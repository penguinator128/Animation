"""YouTube banner (variants A-D) and profile pictures, in any style."""
import math

import numpy as np

from engine import lockup as L
from engine.core import Art

BW, BH = 2560, 1440
SAFE_W, SAFE_H = 1546, 423                      # YouTube's "safe for all devices" centre
CROPS = [("tv", 2560, 1440), ("desktop", 2560, 423), ("tablet", 1855, 423), ("phone", 1546, 423)]
DARK_LOGO_ROLE = {"red": "second", "yellow": "ink", "wildcard": "ink"}


def safe_box(k=1):
    return ((BW - SAFE_W) / 2 * k, (BH - SAFE_H) / 2 * k, (BW + SAFE_W) / 2 * k, (BH + SAFE_H) / 2 * k)


def banner(style, variant="a", k=1):
    """variant: a = name + supporting line, b = logo only, c = wordmark only, d = dark alternate (logo + name).
    k = 1 gives 2560x1440; k = 2 the 5120x2880 master. Returns (image, box of everything important)."""
    W, H = BW * k, BH * k
    cx, cy = W / 2, H / 2
    art = Art(style, W, H, scheme="dark" if variant == "d" else "main", scale=k, seed=f"{style.key}-banner-{variant}")
    if variant == "a":
        box, _ = L.name_line(art, cx, cy - 34 * k, 1310 * k)
    elif variant == "b":
        h = 336 * k
        art.logo(cx, cy, h)
        box = (cx - h * style.logo.aspect / 2, cy - h / 2, cx + h * style.logo.aspect / 2, cy + h / 2)
    elif variant == "c":
        box, _ = L.stacked(art, cx, cy, 800 * k)
    else:
        box = L.horizontal(art, cx, cy, 250 * k, lowercase=True, tagline=True, logo_role=DARK_LOGO_ROLE[style.key])
    sb = safe_box(k)
    assert box[0] >= sb[0] and box[1] >= sb[1] and box[2] <= sb[2] and box[3] <= sb[3], f"banner {variant}: {box} outside safe {sb}"
    return art.render(), box


def logo_fit(style, size, fill=0.71):
    """Where to put the logo so it sits as big as a circle allows: (cx, cy, height).
    The A shape is centred on its smallest enclosing circle, nudged a little towards its visual centre of weight."""
    lg = style.logo
    pts = np.concatenate([np.asarray(p["outer"]) for p in lg.parts])
    ccx, ccy, R = enclosing_circle(pts)
    u = fill * (size / 2) / R
    height = lg.h * u
    weight_y = ccy - 0.35                                  # between the enclosing-circle centre and the centroid
    cx = size / 2 + (lg.w / 2 - ccx) * u
    cy = size / 2 + (lg.h / 2 - weight_y) * u
    return cx, cy, height


def enclosing_circle(pts):
    """Smallest enclosing circle of a few points (brute force over pairs/triples: the logo has 8 corners)."""
    best = None
    n = len(pts)
    cands = []
    for i in range(n):
        for j in range(i + 1, n):
            c = (pts[i] + pts[j]) / 2
            cands.append((c[0], c[1], float(np.linalg.norm(pts[i] - c))))
            for k in range(j + 1, n):
                ax, ay, bx, by, qx, qy = *pts[i], *pts[j], *pts[k]
                d = 2 * (ax * (by - qy) + bx * (qy - ay) + qx * (ay - by))
                if abs(d) < 1e-9:
                    continue
                ux = ((ax * ax + ay * ay) * (by - qy) + (bx * bx + by * by) * (qy - ay) + (qx * qx + qy * qy) * (ay - by)) / d
                uy = ((ax * ax + ay * ay) * (qx - bx) + (bx * bx + by * by) * (ax - qx) + (qx * qx + qy * qy) * (bx - ax)) / d
                cands.append((ux, uy, float(math.hypot(ax - ux, ay - uy))))
    for c in cands:
        if all(math.hypot(p[0] - c[0], p[1] - c[1]) <= c[2] + 1e-6 for p in pts):
            if best is None or c[2] < best[2]:
                best = c
    return best


def profile(style, size=800, scheme="main", logo_role=None):
    """The logo, centred on the style's field, as big as the circle allows with breathing room."""
    art = Art(style, size, size, scheme=scheme, scale=size / 800.0, seed=f"{style.key}-profile-{scheme}")
    cx, cy, h = logo_fit(style, size)
    art.logo(cx, cy, h, role=logo_role or (DARK_LOGO_ROLE[style.key] if scheme == "dark" else "ink"))
    return art.render()


# ====================================================================================================
# building the files
# ====================================================================================================
import cv2                                                    # noqa: E402
from PIL import Image, ImageDraw, ImageFont                   # noqa: E402

from engine.core import save_jpg, save_png, save_png_alpha, to_u8        # noqa: E402
from engine.paths import FONTS, out                           # noqa: E402

VARIANTS = [("a", "name + supporting line"), ("b", "logo only"), ("c", "wordmark only"), ("d", "dark alternate")]
UI_BG, UI_PANEL, UI_TXT, UI_DIM = (14, 14, 18), (24, 24, 30), (236, 236, 242), (150, 150, 162)
GUIDE_COLS = [("TV", 2560, 1440, (255, 255, 255)), ("DESKTOP", 2560, 423, (74, 208, 255)), ("TABLET", 1855, 423, (255, 210, 63)),
              ("PHONE + SAFE AREA", 1546, 423, (255, 79, 154))]


def ui_font(size, weight=500):
    return ImageFont.truetype(str(FONTS / f"dm-sans-{weight}.ttf"), size)


def dashed(d, box, col, w=4, dash=20, gap=12):
    x0, y0, x1, y1 = box
    for (a, b, horiz, fixed) in ((x0, x1, True, y0), (x0, x1, True, y1), (y0, y1, False, x0), (y0, y1, False, x1)):
        p = a
        while p < b:
            q = min(p + dash, b)
            d.line(((p, fixed), (q, fixed)) if horiz else ((fixed, p), (fixed, q)), fill=col, width=w)
            p = q + gap


def circle_crop(u8, d):
    """The picture scaled to d px and cut to an anti-aliased circle (RGBA), as profile pictures are shown."""
    im = cv2.resize(u8, (d, d), interpolation=cv2.INTER_AREA)
    yy, xx = np.mgrid[0:d, 0:d].astype(np.float32)
    a = np.clip(d / 2 - np.hypot(xx - (d - 1) / 2, yy - (d - 1) / 2) + 0.5, 0, 1)
    return Image.fromarray(np.dstack([im, (a * 255 + 0.5).astype(np.uint8)]), "RGBA")


def safe_guide(u8, style, path):
    im = Image.fromarray(u8).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    f = ui_font(30, 700)
    # dim everything outside the safe area a little, outline each device's view
    sx0, sy0, sx1, sy1 = safe_box()
    for box in ((0, 0, BW, sy0), (0, sy1, BW, BH), (0, sy0, sx0, sy1), (sx1, sy0, BW, sy1)):
        d.rectangle(box, fill=(0, 0, 0, 70))
    for k, (name, w, h, col) in enumerate(GUIDE_COLS):
        box = ((BW - w) / 2 + 4 + 5 * k, (BH - h) / 2 + 4 + 5 * k, (BW + w) / 2 - 5 - 5 * k, (BH + h) / 2 - 5 - 5 * k)
        dashed(d, box, col + (255,), 4)
    labels = [("TV: the whole image, 2560 x 1440", 60, 44, GUIDE_COLS[0][3]), ("DESKTOP (widest): 2560 x 423", 60, sy0 - 54, GUIDE_COLS[1][3]),
              ("TABLET: 1855 x 423", (BW - 1855) / 2 + 20, sy1 + 22, GUIDE_COLS[2][3]),
              ("PHONE and SAFE AREA: 1546 x 423. Keep the logo and all text inside this box.", sx0 + 20, sy1 + 64, GUIDE_COLS[3][3])]
    for t, x, y, col in labels:
        w = d.textlength(t, font=f)
        d.rounded_rectangle((x - 12, y - 8, x + w + 12, y + 40), 8, fill=(10, 10, 14, 215))
        d.text((x, y - 2), t, font=f, fill=col)
    save_jpg(np.asarray(im, np.float32) / 255, path, 90)


def device_preview(u8, prof_u8, name, path):
    """How one banner crops on TV, desktop, tablet and phone, plus a generic channel-page mock-up."""
    ban = Image.fromarray(u8)
    CW, S = 2200, 2000 / BW
    secs = []
    tv_h = int(BH * S)
    sec = Image.new("RGB", (CW, 150 + tv_h + 110), UI_BG)
    d = ImageDraw.Draw(sec)
    d.text((100, 38), name, font=ui_font(40, 700), fill=UI_TXT)
    d.text((100, 96), "TV shows the whole image. The boxes are what desktop, tablet and phone show.", font=ui_font(22), fill=UI_DIM)
    sec.paste(ban.resize((2000, tv_h), Image.LANCZOS), (100, 150))
    y0 = 150 + (BH - 423) / 2 * S
    for k, (nm, w, h, col) in enumerate(GUIDE_COLS[1:]):
        x0 = 100 + (BW - w) / 2 * S
        dashed(d, (x0 + 3 + 6 * k, y0 + 3 + 6 * k, x0 + w * S - 3 - 6 * k, y0 + 423 * S - 3 - 6 * k), col, 4)
    lx = 100
    for nm, w, h, col in GUIDE_COLS[1:]:
        d.rectangle((lx, 150 + tv_h + 40, lx + 26, 150 + tv_h + 66), fill=col)
        t = f"{nm}  {w} x {h}"
        d.text((lx + 40, 150 + tv_h + 36), t, font=ui_font(26), fill=UI_TXT)
        lx += 100 + d.textlength(t, font=ui_font(26))
    secs.append(sec)
    for nm, w, h, col in GUIDE_COLS[1:]:
        cw, ch = int(w * S), int(423 * S)
        sec = Image.new("RGB", (CW, ch + 100), UI_BG)
        d = ImageDraw.Draw(sec)
        d.rectangle((100, 26, 120, 46), fill=col)
        d.text((135, 18), f"{nm}  ·  {w} x 423", font=ui_font(26), fill=UI_TXT)
        crop = ban.crop(((BW - w) // 2, (BH - 423) // 2, (BW + w) // 2, (BH - 423) // 2 + 423))
        sec.paste(crop.resize((cw, ch), Image.LANCZOS), (100 + (2000 - cw) // 2, 70))
        secs.append(sec)
    sec = Image.new("RGB", (CW, 940), UI_BG)
    d = ImageDraw.Draw(sec)
    d.text((100, 26), "How it sits on a channel page (a generic mock-up, not a screenshot)", font=ui_font(26), fill=UI_TXT)
    dx, dy, dw = 100, 86, 1300
    d.rounded_rectangle((dx, dy, dx + dw, dy + 760), 22, fill=UI_PANEL)
    strip = ban.crop((0, (BH - 423) // 2, BW, (BH - 423) // 2 + 423)).resize((dw - 60, int((dw - 60) * 423 / BW)), Image.LANCZOS)
    sec.paste(strip, (dx + 30, dy + 40))
    av = circle_crop(prof_u8, 150)
    sec.paste(av, (dx + 30, dy + 80 + strip.height), av)
    d.text((dx + 210, dy + 102 + strip.height), "ASTRIS PRODUCTIONS", font=ui_font(34, 700), fill=UI_TXT)
    for i, wf in enumerate((0.42, 0.30)):
        d.rounded_rectangle((dx + 210, dy + 165 + strip.height + i * 40, dx + 210 + int(800 * wf), dy + 185 + strip.height + i * 40), 10, fill=(52, 52, 62))
    for i in range(4):
        tx = dx + 30 + i * 312
        d.rounded_rectangle((tx, dy + 330 + strip.height, tx + 290, dy + 330 + strip.height + 163), 14, fill=(40, 40, 48))
    d.text((dx + 30, dy + 712), "DESKTOP", font=ui_font(22), fill=UI_DIM)
    px, py, pw, ph = 1520, 86, 400, 760
    d.rounded_rectangle((px - 14, py - 14, px + pw + 14, py + ph + 14), 56, fill=(46, 46, 54))
    d.rounded_rectangle((px, py, px + pw, py + ph), 44, fill=UI_PANEL)
    strip = ban.crop(((BW - 1546) // 2, (BH - 423) // 2, (BW + 1546) // 2, (BH - 423) // 2 + 423)).resize((pw - 32, int((pw - 32) * 423 / 1546)), Image.LANCZOS)
    sec.paste(strip, (px + 16, py + 70))
    av = circle_crop(prof_u8, 92)
    sec.paste(av, (px + 16, py + 90 + strip.height), av)
    d.text((px + 124, py + 108 + strip.height), "ASTRIS PRODUCTIONS", font=ui_font(20, 700), fill=UI_TXT)
    d.rounded_rectangle((px + 124, py + 150 + strip.height, px + 300, py + 164 + strip.height), 7, fill=(52, 52, 62))
    for i in range(2):
        ty = py + 230 + strip.height + i * 230
        d.rounded_rectangle((px + 16, ty, px + pw - 16, ty + 200), 14, fill=(40, 40, 48))
    d.text((px + 16, py + ph + 26), "PHONE", font=ui_font(22), fill=UI_DIM)
    secs.append(sec)
    full = Image.new("RGB", (CW, sum(s.height for s in secs)), UI_BG)
    y = 0
    for s_ in secs:
        full.paste(s_, (0, y))
        y += s_.height
    save_jpg(np.asarray(full, np.float32) / 255, path, 88)


def profile_preview(u8_1600, name, path):
    W, H = 2200, 1180
    im = Image.new("RGB", (W, H), UI_BG)
    d = ImageDraw.Draw(im)
    d.text((100, 40), name, font=ui_font(40, 700), fill=UI_TXT)
    d.text((100, 96), "Profile pictures are shown as a circle. Left: what gets cut away. Right: the real sizes, on dark and on light.", font=ui_font(22), fill=UI_DIM)
    D = 920
    sq = Image.fromarray(cv2.resize(u8_1600, (D, D), interpolation=cv2.INTER_AREA))
    im.paste(Image.blend(Image.new("RGB", (D, D), UI_BG), sq, 0.25), (100, 180))
    c = circle_crop(u8_1600, D)
    im.paste(c, (100, 180), c)
    d.ellipse((100, 180, 100 + D, 180 + D), outline=(255, 255, 255), width=2)
    for row, (bg, fg) in enumerate(((UI_PANEL, UI_TXT), ((246, 246, 248), (30, 30, 36)))):
        x0, y0 = 1120, 200 + row * 480
        d.rounded_rectangle((x0, y0, x0 + 980, y0 + 420), 24, fill=bg)
        d.text((x0 + 30, y0 + 20), "on dark" if row == 0 else "on light", font=ui_font(22), fill=fg)
        x = x0 + 40
        for dd in (176, 120, 88, 48, 36, 24):
            c = circle_crop(u8_1600, dd)
            im.paste(c, (x, int(y0 + 230 - dd / 2)), c)
            d.text((x + dd / 2, y0 + 340), f"{dd}px", font=ui_font(22), fill=fg, anchor="ma")
            x += dd + 60
    save_jpg(np.asarray(im, np.float32) / 255, path, 90)


def build(style):
    k = style.key
    bdir, pdir = out(k, "social", "banner"), out(k, "social", "profile")
    prof800 = profile(style, 800)
    prof1600 = profile(style, 1600)
    save_png(prof800, pdir / f"astris-{k}-profile-800x800.png")
    save_png(prof1600, pdir / f"astris-{k}-profile-master-1600x1600.png")
    alt800, alt1600 = profile(style, 800, "dark"), profile(style, 1600, "dark")
    save_png(alt800, pdir / f"astris-{k}-profile-alt-800x800.png")
    save_png(alt1600, pdir / f"astris-{k}-profile-alt-master-1600x1600.png")
    gen = profile(style, 1000)
    save_png(gen, pdir / f"astris-{k}-profile-general-square-1000x1000.png")
    circle_crop(to_u8(gen), 1000).save(pdir / f"astris-{k}-profile-general-circle-1000x1000.png", optimize=True)
    profile_preview(to_u8(prof1600), f"astris-{k}-profile  ·  800 x 800 (master 1600 x 1600)", pdir / f"astris-{k}-profile-preview-in-circle.jpg")
    profile_preview(to_u8(alt1600), f"astris-{k}-profile-alt  ·  800 x 800 (master 1600 x 1600)", pdir / f"astris-{k}-profile-alt-preview-in-circle.jpg")
    report = []
    for v, label in VARIANTS:
        img, box = banner(style, v, 1)
        p = save_png(img, bdir / f"astris-{k}-banner-{v}-2560x1440.png")
        mb = p.stat().st_size / 1e6
        assert mb < 6.0, f"{p.name} is {mb:.2f} MB (YouTube's limit is 6 MB)"
        u8 = to_u8(img)
        prof_for = to_u8(alt800 if v == "d" else prof800)
        device_preview(u8, prof_for, f"astris-{k}-banner-{v}  ·  {label}  ·  2560 x 1440", bdir / f"astris-{k}-banner-{v}-device-preview.jpg")
        if v == "a":
            safe_guide(u8, style, bdir / f"astris-{k}-banner-safe-area-guide-2560x1440.jpg")
        master, _ = banner(style, v, 2)
        pm = save_png(master, bdir / f"astris-{k}-banner-{v}-master-5120x2880.png")
        sb = safe_box()
        report.append(f"banner {v}: {mb:.2f} MB, master {pm.stat().st_size / 1e6:.1f} MB, margins inside the safe area (l, t, r, b) = "
                      f"{box[0] - sb[0]:.0f}, {box[1] - sb[1]:.0f}, {sb[2] - box[2]:.0f}, {sb[3] - box[3]:.0f} px")
    return report
