#!/usr/bin/env python3
"""
Write preview.html at the top of the kit: a gallery of the whole kit on one page.
The small pictures are built into the page itself, so it works offline, straight from the folder.
Every picture links to the real file.

    python3 code/make_preview.py
"""
import base64
import html
import io
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

KIT = Path(__file__).resolve().parent.parent
CFG = json.loads((KIT / "brand-config.json").read_text())
STYLES = [("red", "02_Style-1-Red"), ("yellow", "03_Style-2-Yellow"), ("wildcard", "04_Style-3-Wildcard")]


def thumb(path, width=520, t=None):
    """A small JPEG of a picture (or of a video frame at time t), as a data: URL."""
    if path.suffix in (".mp4", ".mov"):
        w = 1280
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={w}:-2",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        if len(raw) < w * 3 * 16:
            raise RuntimeError(f"could not read a frame from {path} (is it still being written?)")
        im = Image.fromarray(np.frombuffer(raw, np.uint8).reshape(len(raw) // (w * 3), w, 3))
    else:
        im = Image.open(path)
        if im.mode != "RGB":
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, (214, 210, 204, 255))
            bg.alpha_composite(im)
            im = bg.convert("RGB")
    im.thumbnail((width, int(width * 2.2)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=78, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode(), im.size


def card(path, label, width=520, t=None, link=None):
    src, (w, h) = thumb(path, width, t)
    href = html.escape(str((link or path).relative_to(KIT)))
    return (f'<a class="card" href="{href}"><img src="{src}" width="{w}" height="{h}" alt="{html.escape(label)}" loading="lazy">'
            f'<span>{html.escape(label)}</span></a>')


def section(title, cards, cls="grid"):
    return f'<h3>{html.escape(title)}</h3>\n<div class="{cls}">\n' + "\n".join(cards) + "\n</div>"


def style_block(key, folder):
    b = KIT / folder
    sc = CFG["styles"][key]
    sw = "".join(f'<span class="sw" style="background:{c["hex"]}"></span><code>{c["hex"]}</code> {html.escape(c["name"])} &nbsp; '
                 for c in sc["colours"].values())
    out = [f'<section id="{key}"><h2>Style {sc["number"]}: {html.escape(sc["name"])} <small>&ldquo;{html.escape(sc["tagline"])}&rdquo;</small></h2>',
           f'<p class="sws">{sw}</p>',
           f'<p><a href="{folder}/overview.png">overview.png</a> &middot; <a href="{folder}/01_Brand-Guide/astris-{key}-brand-guide-a4-landscape.pdf">brand guide (PDF)</a> &middot; '
           f'<a href="{folder}/README.md">README</a></p>']
    so = b / "03_YouTube-and-Social"
    out.append(section("YouTube banner and profile picture", [card(so / "banner" / f"astris-{key}-banner-{v}-2560x1440.png", f"banner {v.upper()}") for v in "abcd"]
                       + [card(so / "profile" / f"astris-{key}-profile-800x800.png", "profile picture", 300),
                          card(so / "profile" / f"astris-{key}-profile-preview-in-circle.jpg", "profile, in the circle")]))
    vi = b / "04_Intros-and-Video"
    vids = [("intro-a-pop-2s-4k24.mp4", 1.9, "intro A, pop, 2 s"), ("intro-b-type-4s-4k24.mp4", 3.9, "intro B, type, 4 s"),
            ("intro-c-slow-7s-4k24.mp4", 6.9, "intro C, slow, 7 s"), ("title-logo-5s-4k24.mp4", 4.9, "title logo, 5 s"),
            ("end-card-10s-4k24.mp4", 5.0, "end card, 10 s")]
    out.append(section("Intros and video (click to play)", [card(vi / f"astris-{key}-{n}", lab, t=t) for n, t, lab in vids]))
    out.append(section("Thumbnails, Instagram", [card(p, p.stem.replace(f"astris-{key}-", "")) for p in sorted((so / "thumbnails").glob("*-1280x720.jpg"))]
                       + [card(p, p.stem.replace(f"astris-{key}-", "").replace("-1080x1350", ""), 300) for p in sorted((so / "instagram-posts").glob("*.png"))[:3]]
                       + [card(p, p.stem.replace(f"astris-{key}-", "").replace("-1080x1920", ""), 220) for p in sorted((so / "instagram-stories").glob("*.png"))[:2]]))
    out.append(section("Instagram highlight covers", [card(p, p.stem.split("-", 4)[-1].replace("-1080x1920", ""), 150) for p in sorted((so / "instagram-highlight-covers").glob("*.png"))], "grid small"))
    lg = b / "02_Logos" / "png-512"
    out.append(section("Logos", [card(lg / f"astris-{key}-logo-{lay}-{way}-512.png", f"{lay}, {way}", 260) for lay in ("wide", "stacked", "icon", "wordmark") for way in ("on-colour", "full-colour")]))
    pa = b / "08_Film-and-Paperwork"
    out.append(section("Film and paperwork", [card(p, p.stem.replace(f"astris-{key}-poster-", "poster ").replace("-a3-3508x4961", ""), 300) for p in sorted((pa / "posters").glob("*-a3-*.jpg"))]
                       + [card(pa / "business-card" / f"astris-{key}-business-card-preview.jpg", "business card"),
                          card(pa / "clapperboard" / f"astris-{key}-clapperboard-on-colour-3840x2160.png", "clapperboard (3 s clap in the folder)"),
                          card(pa / "presents-card" / f"astris-{key}-presents-card-3840x2160.png", "the presents card"),
                          card(pa / "letterhead-and-invoice" / f"astris-{key}-invoice-template-a4-2480x3508.png", "invoice template", 300),
                          card(pa / "press-kit" / "previews" / f"astris-{key}-press-kit-full-preview-page-1.jpg", "press kit", 300)]))
    me = b / "07_Merch"
    out.append(section("Merch", [card(me / "stickers" / f"astris-{key}-sticker-sheet-a4-2480x3508.png", "sticker sheet", 300)]
                       + [card(p, p.stem.replace(f"astris-{key}-mockup-", "").replace("-illustration", " (illustration)")) for p in sorted((me / "mock-ups").glob("*.jpg"))]
                       + [card(me / "phone-wallpapers" / f"astris-{key}-wallpaper-{d}-1179x2556.png", f"wallpaper, {d}", 200) for d in ("logo", "name", "dark")]))
    pr = b / "05_Premiere-Assets"
    out.append(section("Premiere, website, textures",
                       [card(p, p.stem.replace(f"astris-{key}-", "").replace("-still-3840x2160-transparent", ""), 420) for p in sorted((pr / "lower-thirds").glob("*-still-*.png"))]
                       + [card(b / "09_Website" / f"astris-{key}-website-hero-desktop-mockup.jpg", "website, desktop (mock-up)"),
                          card(b / "09_Website" / f"astris-{key}-website-hero-mobile-mockup.jpg", "website, phone (mock-up)", 260),
                          card(b / "10_Textures-and-LUTs" / "luts" / f"astris-{key}-looks-preview.jpg", "colour looks: original, natural, strong, print")]))
    gp = sorted((b / "01_Brand-Guide" / "pages").glob("*.png"))
    out.append(section("Brand guide pages", [card(p, p.stem.split("-page-")[1].replace("-", " "), 300) for p in gp]))
    out.append("</section>")
    return "\n".join(out)


def main():
    lp = KIT / "01_Logo-Pack-Bare-Bones"
    blocks = [style_block(k, f) for k, f in STYLES]
    logo = section("Logo pack (bare bones)", [card(p, p.stem.replace("astris-logo-", ""), 420) for p in sorted((lp / "geometric-perfect" / "previews").glob("*.png"))]
                   + [card(p, p.stem.replace("astris-logo-", ""), 420) for p in sorted((lp / "report-images").glob("*.png"))[:2]])
    comp = card(KIT / "compare-styles.png", "the three styles side by side", 1100)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ASTRIS Brand Kit</title>
<style>
  @font-face {{ font-family: "Anton"; src: url("code/fonts/anton-400.ttf"); font-display: swap; }}
  :root {{ --bg: #EDEAE5; --fg: #1A1817; --soft: #6B6560; --card: #FFFFFF; --line: #D9D4CD; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #161514; --fg: #EDEAE5; --soft: #A39C94; --card: #22201E; --line: #33302C; }} }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  header, section, footer {{ max-width: 1240px; margin: 0 auto; padding: 0 16px; }}
  header {{ padding-top: 48px; }}
  h1, h2, h3 {{ font-family: "Anton", Impact, "Arial Narrow", sans-serif; font-weight: 400; letter-spacing: 0.01em; line-height: 1.05; }}
  h1 {{ font-size: clamp(2.4rem, 7vw, 4.6rem); margin: 0 0 8px; }}
  h2 {{ font-size: clamp(1.8rem, 4vw, 2.8rem); margin: 64px 0 4px; border-top: 2px solid var(--fg); padding-top: 18px; }}
  h2 small {{ font-family: system-ui, sans-serif; font-size: 1rem; color: var(--soft); margin-left: 8px; }}
  h3 {{ font-size: 1.3rem; margin: 30px 0 10px; }}
  nav a, p a {{ color: inherit; }}
  nav {{ display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 18px 0 0; font-weight: 600; }}
  .grid {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; }}
  .card {{ display: block; background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 8px; color: inherit; text-decoration: none; max-width: 100%; }}
  .card img {{ display: block; max-width: 100%; height: auto; border-radius: 4px; }}
  .card span {{ display: block; font-size: 12.5px; color: var(--soft); margin-top: 6px; max-width: 520px; }}
  .card:hover {{ border-color: var(--fg); }}
  .small .card span {{ font-size: 11px; }}
  .sws {{ color: var(--soft); }}
  .sw {{ display: inline-block; width: 14px; height: 14px; border-radius: 3px; vertical-align: -2px; margin-right: 6px; border: 1px solid var(--line); }}
  footer {{ color: var(--soft); padding: 60px 16px 80px; }}
</style>
</head>
<body>
<header>
  <h1>astris productions. brand kit</h1>
  <p>Three complete styles, a plain logo pack, and the code that made them. Every picture links to the real file.
  Anything in [square brackets] is a placeholder waiting for your details (see README.md).</p>
  <nav><a href="#compare">compare</a><a href="#red">style 1: red</a><a href="#yellow">style 2: yellow</a><a href="#wildcard">style 3: wildcard</a><a href="#logo-pack">logo pack</a>
  <a href="README.md">README</a><a href="MANIFEST.md">MANIFEST</a><a href="fonts.md">fonts</a><a href="downloads/README.md">downloads</a></nav>
</header>
<section id="compare"><h2>The three styles</h2><div class="grid">{comp}</div></section>
{chr(10).join(blocks)}
<section id="logo-pack"><h2>Logo pack</h2>{logo}
<p><a href="01_Logo-Pack-Bare-Bones/logo-report.md">logo-report.md</a>: what was measured and what each clean version changes.</p></section>
<footer>Made by code/make_preview.py. The mock-ups are illustrations, not photos.</footer>
</body>
</html>
"""
    (KIT / "preview.html").write_text(page)
    print(f"preview.html: {len(page) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
