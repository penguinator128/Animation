"""
Website starter in a style:
  favicons     favicon.ico (16 / 32 / 48), PNG 32 / 180 / 192 / 512, favicon.svg, site.webmanifest
  og image     1200 x 630 sharing image (PNG + JPG)
  hero         desktop and mobile hero mock-ups (pictures of how the top of a site could look)
  tokens       tokens.css and tokens.json: the colours, fonts and spacing as variables
  preview      preview.html, a static page that uses the tokens (open it in a browser)

Usage: python3 code/build.py web [--style red]
"""
import json
import struct
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

from assets.youtube import logo_fit
from engine import lockup as L
from engine import type as T
from engine.core import Art, apply_grain, grain_field, hex_rgb, rounded_mask, save_jpg, save_png
from engine.extras import placeholder
from engine.logo import path_d
from engine.paths import STYLE_DIRS, SUB, out
from engine.style import config, films

TEXT_NAMES = {"dm-sans": "DM Sans", "inter": "Inter", "space-grotesk": "Space Grotesk"}


def icon_colours(style):
    h, k = style.hex, style.key
    if k == "red":
        return h["signature"], h["light"], None
    if k == "yellow":
        return h["signature"], h["dark"], None
    return h["signature"], h["light"], h["second"]


# ====================================================================================================
# favicons
# ====================================================================================================
def icon(style, size, rounded=True, fill=None):
    """Square icon: the logo on a tile of the style's colour. Small sizes use the logo without its sprocket holes,
    which would only be blur at 16 px (the full logo is used from 96 px up)."""
    bg, fg, sh = icon_colours(style)
    ss = 8 if size <= 64 else (4 if size <= 256 else 2)
    S = size * ss
    lg = style.logo
    cx, cy, lh = logo_fit(style, S, fill or (0.66 if rounded else 0.56))
    x0, y0 = cx - lh * lg.aspect / 2, cy - lh / 2
    holes = size >= 96
    m = lg.mask((S, S), x0, y0, lh, ss=1, holes=holes)
    img = np.empty((S, S, 3), np.float32)
    img[:] = hex_rgb(bg)
    if sh and size >= 96:
        off = 0.03 * lh * 0.55
        solid = lg.mask((S, S), x0, y0, lh, ss=1, holes=False)
        shm = lg.mask((S, S), x0 + off, y0 + off * 0.9, lh, ss=1, holes=holes) * (1 - solid)
        img = img * (1 - shm[..., None]) + hex_rgb(sh) * shm[..., None]
    img = img * (1 - m[..., None]) + hex_rgb(fg) * m[..., None]
    al = rounded_mask(S, S, 0.22 * S, ss=1) if rounded else np.ones((S, S), np.float32)
    rgb = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    a = cv2.resize(al, (size, size), interpolation=cv2.INTER_AREA)
    return Image.fromarray(np.dstack([np.clip(rgb * 255 + 0.5, 0, 255), np.clip(a * 255 + 0.5, 0, 255)]).astype(np.uint8), "RGBA")


def write_ico(path, images):
    """A .ico that holds each size exactly as drawn (PNG inside, which every current browser reads)."""
    blobs = []
    for im in images:
        b = BytesIO()
        im.save(b, format="PNG", optimize=True)
        blobs.append(b.getvalue())
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for im, blob in zip(images, blobs):
        w = im.width if im.width < 256 else 0
        entries += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    path.write_bytes(head + entries + b"".join(blobs))


def favicon_svg(style):
    bg, fg, sh = icon_colours(style)
    lg = style.logo
    cx, cy, lh = logo_fit(style, 64, 0.66)
    polys = lg.polys(cx - lh * lg.aspect / 2, cy - lh / 2, lh)
    d = " ".join(" ".join([path_d(o, 3)] + [path_d(h, 3) for h in hs]) for _, o, hs in polys)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">\n  <title>ASTRIS PRODUCTIONS</title>\n'
            f'  <rect width="64" height="64" rx="14" fill="{bg}"/>\n  <path fill="{fg}" fill-rule="evenodd" d="{d}"/>\n</svg>\n')


def favicons(style):
    k = style.key
    d = out(k, "web", "favicons")
    write_ico(d / "favicon.ico", [icon(style, s) for s in (16, 32, 48)])
    icon(style, 32).save(d / "favicon-32.png", optimize=True)
    icon(style, 180, rounded=False).convert("RGB").save(d / "apple-touch-icon-180.png", optimize=True)
    icon(style, 192, rounded=False).convert("RGB").save(d / "icon-192.png", optimize=True)
    icon(style, 512, rounded=False).convert("RGB").save(d / "icon-512.png", optimize=True)
    (d / "favicon.svg").write_text(favicon_svg(style))
    bg = icon_colours(style)[0]
    (d / "site.webmanifest").write_text(json.dumps({
        "name": config()["brand"]["name"], "short_name": config()["brand"]["first_word"],
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}],
        "theme_color": bg, "background_color": bg, "display": "standalone"}, indent=2) + "\n")
    # one picture of every size, to check them by eye
    sheet = Image.new("RGB", (1130, 300), (238, 236, 232))
    x = 30
    for s in (16, 32, 48, 180, 192):
        im = icon(style, s, rounded=s < 96)
        sheet.paste(im, (x, 150 - s // 2), im)
        x += s + 40
    big = icon(style, 512, rounded=False).resize((240, 240), Image.LANCZOS)
    sheet.paste(big, (x, 30))
    sheet.save(d / "favicon-check-sheet.png", optimize=True)
    return 8


# ====================================================================================================
# sharing image
# ====================================================================================================
def og_image(style):
    k = style.key
    d = out(k, "web")
    art = Art(style, 1200, 630, scale=1.0, seed=f"{k}-og")
    art.logo(600, 205, 178)
    L.name_line(art, 600, 415, 640, tag_scale=0.22)
    img = art.render()
    save_png(img, d / f"astris-{k}-og-image-1200x630.png")
    save_jpg(img, d / f"astris-{k}-og-image-1200x630.jpg", 90)
    return 2


# ====================================================================================================
# hero mock-ups
# ====================================================================================================
BUTTON = "watch the films"


def button(art, cx, cy, w, h, text, size):
    art.rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, radius=h / 2, size=h, wear=0.4)
    art.text(text, cx, cy, size, face=art.style.text_face(700), tracking=0.10, anchor="mm", role="field", shadow=False, wear=0)


def hero_desktop(style):
    W, H = 2560, 1440
    art = Art(style, W, H, scale=1.0, seed=f"{style.key}-hero-d")
    tf = style.text_face(500)
    art.logo(160, 112, 86)
    x = W - 120
    for word in ("contact", "about", "films"):
        _, _, w = art.text(word, x, 112, 30, face=tf, tracking=0.14, anchor="rm", shadow=False, wear=0)
        x -= w + 84
    L.name_line(art, W / 2, 520, 1500)
    art.tag = "main"
    button(art, W / 2, 800, 440, 104, BUTTON, 31)
    fl = films()[:4]
    cw, gap = 500, 60
    x0 = (W - (len(fl) * cw + (len(fl) - 1) * gap)) / 2
    for i, (title, note) in enumerate(fl):
        x = x0 + i * (cw + gap)
        placeholder(art, x, 1000, x + cw, 1281, "[A STILL FROM THE FILM]", fill=0.10)
        art.text(title.lower() + ".", x + 4, 1342, 52, anchor="lm", shadow=False)
    return art.render()


def hero_mobile(style):
    W, H = 1170, 2532
    art = Art(style, W, H, scale=1.0, seed=f"{style.key}-hero-m")
    tf = style.text_face(500)
    art.logo(130, 230, 92)
    art.text("menu", W - 84, 230, 34, face=tf, tracking=0.14, anchor="rm", shadow=False, wear=0)
    L.name_line(art, W / 2, 900, 930, tag_scale=0.22)
    art.tag = "main"
    button(art, W / 2, 1230, 560, 124, BUTTON, 37)
    fl = films()
    if fl:
        placeholder(art, 100, 1540, W - 100, 1540 + 546, "[A STILL FROM THE FILM]", fill=0.10)
        art.text(fl[0][0].lower() + ".", 104, 2180, 78, anchor="lm", shadow=False)
        art.text("[one line about it]", 106, 2270, 34, face=tf, tracking=0.10, anchor="lm", shadow=False, wear=0)
    return art.render()


def paste(canvas, img, x, y, mask=None):
    h, w = img.shape[:2]
    reg = canvas[y:y + h, x:x + w]
    if mask is None:
        reg[:] = img
    else:
        reg[:] = reg * (1 - mask[..., None]) + img * mask[..., None]


def soft_shadow(canvas, x, y, w, h, radius, blur=46, dy=34, amount=0.30):
    H, W = canvas.shape[:2]
    m = np.zeros((H, W), np.float32)
    m[y + dy:y + dy + h, x:x + w] = rounded_mask(h, w, radius)[: H - (y + dy), : W - x]
    canvas *= 1 - amount * cv2.GaussianBlur(m, (0, 0), blur)[..., None]


def small_text(canvas, s, x, y, size, colour, face, tracking=0.08, anchor="l"):
    m, (ox, oy) = T.text_mask(s, face, size, tracking)
    w = T.text_width(s, face, size, tracking)
    x0 = int(round(x - {"l": 0, "m": w / 2, "r": w}[anchor] + ox))
    y0 = int(round(y + oy))
    col = np.empty(m.shape + (3,), np.float32)
    col[:] = hex_rgb(colour)
    paste(canvas, col, x0, y0, m)


def hero_mockups(style):
    k = style.key
    d = out(k, "web")
    tf = style.text_face(500)
    back = hex_rgb(style.hex["light"]) * 0.88
    site = config()["person"]["website"]
    # ---- desktop: a browser window
    hero = hero_desktop(style)
    cw, ch = 2760, 1552
    hero_s = cv2.resize(hero, (cw, ch), interpolation=cv2.INTER_AREA)
    W, H, bar = 3200, 2100, 96
    canvas = np.empty((H, W, 3), np.float32)
    canvas[:] = back
    x, y = (W - cw) // 2, 190
    soft_shadow(canvas, x, y, cw, bar + ch, 30)
    win = np.empty((bar + ch, cw, 3), np.float32)
    win[:bar] = (0.955, 0.950, 0.940)
    win[bar:] = hero_s
    paste(canvas, win, x, y, rounded_mask(bar + ch, cw, 30))
    for i, c in enumerate(((0.80, 0.78, 0.76), (0.86, 0.84, 0.82), (0.90, 0.89, 0.87))):
        dot = np.empty((30, 30, 3), np.float32)
        dot[:] = c
        paste(canvas, dot, x + 44 + i * 50, y + 33, rounded_mask(30, 30, 15))
    pill = np.ones((52, 980, 3), np.float32)
    paste(canvas, pill, x + (cw - 980) // 2, y + 22, rounded_mask(52, 980, 26))
    small_text(canvas, site, x + cw / 2, y + 22 + 35, 26, "#6B6762", tf, anchor="m")
    small_text(canvas, "MOCK-UP  ·  NOT A LIVE WEBSITE", 220, H - 96, 28, style.hex["dark"], tf, tracking=0.24)
    save_jpg(canvas, d / f"astris-{k}-website-hero-desktop-mockup.jpg", 90)
    # ---- mobile: a phone
    hero = hero_mobile(style)
    sw, sh = 1132, 2450
    hero_s = cv2.resize(hero, (sw, sh), interpolation=cv2.INTER_AREA)
    W, H = 1800, 3000
    canvas = np.empty((H, W, 3), np.float32)
    canvas[:] = back
    bw, bh = sw + 68, sh + 68
    x, y = (W - bw) // 2, 200
    soft_shadow(canvas, x, y, bw, bh, 150)
    body = np.empty((bh, bw, 3), np.float32)
    body[:] = (0.075, 0.072, 0.070)
    paste(canvas, body, x, y, rounded_mask(bh, bw, 150))
    paste(canvas, hero_s, x + 34, y + 34, rounded_mask(sh, sw, 118))
    isl = np.zeros((66, 250, 3), np.float32) + 0.05
    paste(canvas, isl, x + (bw - 250) // 2, y + 34 + 36, rounded_mask(66, 250, 33))
    small_text(canvas, "MOCK-UP  ·  NOT A LIVE WEBSITE", W / 2, H - 78, 26, style.hex["dark"], tf, tracking=0.24, anchor="m")
    save_jpg(canvas, d / f"astris-{k}-website-hero-mobile-mockup.jpg", 90)
    return 2


# ====================================================================================================
# tokens + preview page
# ====================================================================================================
def tokens(style):
    h, k = style.hex, style.key
    text_name = TEXT_NAMES[style.text_family]
    if k == "red":
        role = dict(bg=h["signature"], fg=h["light"], muted=h["dark"], surface=h["light"], on_surface=h["dark"], accent=h["signature"], on_accent=h["light"], dark=h["dark"], on_dark=h["light"])
    elif k == "yellow":
        role = dict(bg=h["signature"], fg=h["dark"], muted=h["dark"], surface=h["light"], on_surface=h["dark"], accent=h["dark"], on_accent=h["signature"], dark=h["dark"], on_dark=h["signature"])
    else:
        role = dict(bg=h["light"], fg=h["signature"], muted=h["dark"], surface=h["light"], on_surface=h["dark"], accent=h["signature"], on_accent=h["light"], dark=h["signature"], on_dark=h["light"])
    tok = {
        "name": f"ASTRIS PRODUCTIONS, {style.name}",
        "color": {**{key: {"value": val, "name": style.colour_names[key]} for key, val in h.items()}},
        "role": role,
        "font": {"display": {"family": "Anton", "weight": 400, "fallback": '"League Gothic", Impact, "Arial Narrow", sans-serif'},
                 "text": {"family": text_name, "weights": [400, 500, 700], "fallback": "system-ui, -apple-system, 'Segoe UI', Arial, sans-serif"}},
        "type": {"hero": "clamp(3rem, 10vw, 9.5rem)", "h1": "clamp(2.4rem, 6vw, 5rem)", "h2": "clamp(1.6rem, 3.4vw, 2.6rem)", "body": "1.0625rem", "small": "0.8125rem",
                 "tracking-display": "0.012em", "tracking-small": "0.16em", "leading-display": 0.95, "leading-body": 1.55},
        "space": {"1": "0.25rem", "2": "0.5rem", "3": "1rem", "4": "1.5rem", "5": "2.5rem", "6": "4rem", "7": "6.5rem"},
        "radius": {"small": "0.5rem", "medium": "1rem", "pill": "999px"},
        "grain": {"amount": style.grain_amount, "note": "Lay astris-grain-512.png over the page with mix-blend-mode: overlay."},
        "motion": {"quick": "120ms", "normal": "240ms", "ease": "cubic-bezier(0.2, 0.8, 0.2, 1)"},
    }
    css = [f"/* ASTRIS PRODUCTIONS design tokens, {style.name} style. Generated from brand-config.json by code/build.py web. */", ":root {"]
    for key, val in h.items():
        css.append(f"  --astris-{key}: {val};   /* {style.colour_names[key]} */")
    css.append("")
    for key, val in role.items():
        css.append(f"  --astris-{key.replace('_', '-')}: {val};")
    css += ["", f"  --astris-font-display: \"Anton\", {tok['font']['display']['fallback']};", f"  --astris-font-text: \"{text_name}\", {tok['font']['text']['fallback']};", ""]
    for key, val in tok["type"].items():
        css.append(f"  --astris-{key}: {val};")
    css.append("")
    for grp in ("space", "radius", "motion"):
        for key, val in tok[grp].items():
            css.append(f"  --astris-{grp}-{key}: {val};")
    css += ["", f"  --astris-grain: {style.grain_amount};", "}", ""]
    return tok, "\n".join(css)


def logo_svg_inline(style, colour, height):
    lg = style.logo
    polys = lg.polys(0, 0, 100)
    d = " ".join(" ".join([path_d(o, 2)] + [path_d(h, 2) for h in hs]) for _, o, hs in polys)
    return f'<svg class="logo" viewBox="0 0 {100 * lg.aspect:.2f} 100" height="{height}" role="img" aria-label="ASTRIS PRODUCTIONS"><path fill="{colour}" fill-rule="evenodd" d="{d}"/></svg>'


def preview_html(style, tok):
    cfg = config()
    k, b, p, so = style.key, cfg["brand"], cfg["person"], cfg["social"]
    text_name = TEXT_NAMES[style.text_family]
    r = tok["role"]
    cards = "\n".join(f'      <article class="card"><div class="still">[a still from the film]</div><h3>{t.lower()}.</h3><p>{("(" + n + ") ") if n else ""}[one line about it]</p></article>'
                      for t, n in films())
    sw = "\n".join(f'      <div class="swatch" style="background:{v}; color:{"#fff" if sum(hex_rgb(v)) < 1.4 else "#111"}"><b>{style.colour_names[key]}</b><span>{v}</span></div>'
                   for key, v in style.hex.items())
    shadow = f"text-shadow: 0.03em 0.027em 0 {style.hex['second']};" if k == "wildcard" else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{b['name']} ({style.name} style preview)</title>
<link rel="icon" href="favicons/favicon.ico" sizes="48x48">
<link rel="icon" href="favicons/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="favicons/apple-touch-icon-180.png">
<link rel="stylesheet" href="tokens.css">
<style>
  /* The brand fonts ship with the kit (code/fonts). On a real site, host them yourself or load them from Google Fonts. */
  @font-face {{ font-family: "Anton"; src: url("../../code/fonts/anton-400.ttf"); font-weight: 400; font-display: swap; }}
  @font-face {{ font-family: "{text_name}"; src: url("../../code/fonts/{style.text_family}-400.ttf"); font-weight: 400; font-display: swap; }}
  @font-face {{ font-family: "{text_name}"; src: url("../../code/fonts/{style.text_family}-500.ttf"); font-weight: 500; font-display: swap; }}
  @font-face {{ font-family: "{text_name}"; src: url("../../code/fonts/{style.text_family}-700.ttf"); font-weight: 700; font-display: swap; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--astris-bg); color: var(--astris-fg); font-family: var(--astris-font-text); font-size: var(--astris-body); line-height: var(--astris-leading-body); }}
  body::after {{ content: ""; position: fixed; inset: 0; background: url("astris-grain-512.png"); mix-blend-mode: overlay; opacity: 0.75; pointer-events: none; z-index: 10; }}
  nav {{ display: flex; align-items: center; justify-content: space-between; padding: var(--astris-space-4) var(--astris-space-5); }}
  nav ul {{ display: flex; gap: var(--astris-space-5); list-style: none; margin: 0; padding: 0; font-weight: 500; letter-spacing: 0.14em; font-size: var(--astris-small); }}
  a {{ color: inherit; text-decoration: none; }}
  .hero {{ text-align: center; padding: var(--astris-space-7) var(--astris-space-4) var(--astris-space-6); }}
  .hero h1 {{ font-family: var(--astris-font-display); font-weight: 400; font-size: var(--astris-hero); line-height: var(--astris-leading-display); letter-spacing: var(--astris-tracking-display); margin: 0; {shadow} }}
  .hero p {{ font-family: var(--astris-font-display); letter-spacing: var(--astris-tracking-small); font-size: clamp(0.8rem, 1.6vw, 1.3rem); margin: var(--astris-space-3) 0 var(--astris-space-5); }}
  .button {{ display: inline-block; background: var(--astris-fg); color: var(--astris-bg); font-weight: 700; letter-spacing: 0.1em; padding: 0.95em 2.2em; border-radius: var(--astris-radius-pill); transition: transform var(--astris-motion-quick) var(--astris-motion-ease); }}
  .button:hover {{ transform: translateY(-2px); }}
  section {{ padding: var(--astris-space-6) var(--astris-space-5); }}
  h2 {{ font-family: var(--astris-font-display); font-weight: 400; font-size: var(--astris-h2); letter-spacing: var(--astris-tracking-display); margin: 0 0 var(--astris-space-4); }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: var(--astris-space-4); }}
  .still {{ aspect-ratio: 16 / 9; border: 2px dashed currentColor; border-radius: var(--astris-radius-medium); display: grid; place-items: center; font-size: var(--astris-small); letter-spacing: 0.08em; opacity: 0.85; }}
  .card h3 {{ font-family: var(--astris-font-display); font-weight: 400; font-size: 1.9rem; margin: var(--astris-space-3) 0 0; line-height: 1; }}
  .card p {{ margin: var(--astris-space-2) 0 0; font-size: var(--astris-small); }}
  .panel {{ background: var(--astris-surface); color: var(--astris-on-surface); }}
  .swatches {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: var(--astris-space-3); }}
  .swatch {{ border-radius: var(--astris-radius-medium); padding: var(--astris-space-4) var(--astris-space-3); min-height: 130px; display: flex; flex-direction: column; justify-content: flex-end; border: 1px solid rgba(0,0,0,0.08); }}
  .swatch span {{ font-size: var(--astris-small); letter-spacing: 0.08em; }}
  .type-row {{ display: grid; grid-template-columns: 9rem 1fr; gap: var(--astris-space-3); align-items: baseline; border-top: 1px solid rgba(0,0,0,0.12); padding: var(--astris-space-3) 0; }}
  .type-row small {{ letter-spacing: 0.14em; text-transform: uppercase; font-size: 0.7rem; }}
  footer {{ background: var(--astris-dark); color: var(--astris-on-dark); padding: var(--astris-space-5); display: flex; flex-wrap: wrap; gap: var(--astris-space-4); justify-content: space-between; align-items: center; font-size: var(--astris-small); }}
  footer .name {{ font-family: var(--astris-font-display); font-size: 1.6rem; }}
</style>
</head>
<body>
  <nav>
    <a href="#">{logo_svg_inline(style, r['fg'], 44)}</a>
    <ul><li><a href="#films">films</a></li><li><a href="#about">about</a></li><li><a href="#contact">contact</a></li></ul>
  </nav>
  <header class="hero">
    <h1>{b['name_lowercase']}</h1>
    <p>{style.tagline}</p>
    <a class="button" href="#films">{BUTTON}</a>
  </header>
  <section id="films">
    <h2>films.</h2>
    <div class="cards">
{cards}
    </div>
  </section>
  <section id="about" class="panel">
    <h2>about.</h2>
    <p style="max-width: 46rem">{b['about_long']}</p>
    <h2 style="margin-top: var(--astris-space-6)">colours.</h2>
    <div class="swatches">
{sw}
    </div>
    <h2 style="margin-top: var(--astris-space-6)">type.</h2>
    <div class="type-row"><small>Display</small><div style="font-family: var(--astris-font-display); font-size: var(--astris-h1); line-height: 1">Anton, for the big friendly lines.</div></div>
    <div class="type-row"><small>Text 700</small><div style="font-weight: 700">{text_name} Bold, for labels and buttons.</div></div>
    <div class="type-row"><small>Text 400</small><div>{text_name} Regular, for everything you read for more than a second.</div></div>
    <div class="type-row"><small>Small</small><div style="font-size: var(--astris-small); letter-spacing: var(--astris-tracking-small); text-transform: uppercase">The very small supporting line</div></div>
  </section>
  <footer id="contact">
    <span class="name">{b['name_lowercase']}</span>
    <span>{p['email']} &nbsp;&middot;&nbsp; {so['youtube']} &nbsp;&middot;&nbsp; {so['instagram']}</span>
  </footer>
</body>
</html>
"""


def readme(style):
    k = style.key
    (STYLE_DIRS[k] / SUB["web"] / "README.md").write_text(f"""# Website starter ({style.name})

| File | What it is |
|---|---|
| `favicons/` | `favicon.ico` (16, 32 and 48 px inside), `favicon-32.png`, `apple-touch-icon-180.png`, `icon-192.png`, `icon-512.png`, `favicon.svg`, `site.webmanifest`, and a check sheet |
| `astris-{k}-og-image-1200x630.png` / `.jpg` | The picture that shows when a link to your site is shared |
| `astris-{k}-website-hero-desktop-mockup.jpg` | A picture of how the top of the site could look on a computer |
| `astris-{k}-website-hero-mobile-mockup.jpg` | The same on a phone |
| `tokens.css` / `tokens.json` | The style's colours, fonts, sizes and spacing as variables |
| `astris-grain-512.png` | A small seamless grain tile for the page background |
| `preview.html` | A static page built from the tokens. Open it in a browser (keep it inside the kit folder so it can find the fonts) |

The hero mock-ups are pictures, not a working site. `preview.html` is a real, static page you can start from.

## Favicons: paste this into your page's `<head>`

```html
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon-180.png">
<link rel="manifest" href="/site.webmanifest">
```

Put the files from `favicons/` at the top level of your site.
The 16, 32 and 48 px icons use the logo without its sprocket holes, because at that size the holes turn to blur.
The larger icons and the SVG use the full logo.

## Sharing image

```html
<meta property="og:title" content="ASTRIS PRODUCTIONS">
<meta property="og:image" content="https://[WEBSITE]/astris-{k}-og-image-1200x630.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
```

## Tokens

Link `tokens.css`, then use the variables: `background: var(--astris-bg); color: var(--astris-fg); font-family: var(--astris-font-display);`
`tokens.json` holds the same values for design tools and build scripts.

Fonts: Anton and {TEXT_NAMES[style.text_family]} are free (SIL Open Font License). The files are in `code/fonts/`, and both are on Google Fonts. See `fonts.md` at the top of the kit.
""")


def build(style):
    k = style.key
    n = favicons(style) + og_image(style) + hero_mockups(style)
    d = out(k, "web")
    tok, css = tokens(style)
    (d / "tokens.json").write_text(json.dumps(tok, indent=2) + "\n")
    (d / "tokens.css").write_text(css)
    # seamless grain tile for the page
    from assets.textures import tile_grain
    g = tile_grain(512, "web", 0.6)
    Image.fromarray(np.clip((0.5 + 0.055 * g) * 255 + 0.5, 0, 255).astype(np.uint8), "L").save(d / "astris-grain-512.png", optimize=True)
    (d / "preview.html").write_text(preview_html(style, tok))
    readme(style)
    return [f"{n + 5} website files"]
