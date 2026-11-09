"""
ASTRIS PRODUCTIONS - previews of how each banner and profile picture will look on YouTube.

Banner previews (previews/preview-banner-<name>.png):
  1. the full 2560x1440 image, as a TV shows it, with the desktop / tablet / phone crops outlined,
  2. each crop on its own (desktop 2560x423, tablet 1855x423, phone = safe area 1546x423),
  3. small mock-ups of a channel header on a desktop and on a phone, with the matching profile picture.
Profile previews (previews/preview-profile-<name>.png):
  the picture inside YouTube's circle, large and at small sizes, on dark and light backgrounds.
Usage: python3 previews.py
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import common as C

OUT = C.ROOT.parent / "output"
PREV = OUT / "previews"
BW, BH = 2560, 1440
CROPS = [("DESKTOP", 2560, (74, 208, 255)), ("TABLET", 1855, (255, 210, 63)), ("PHONE  +  SAFE AREA", 1546, (255, 79, 154))]
STRIP_H = 423
BG, PANEL, TXT, DIM = (14, 14, 18), (24, 24, 30), (236, 236, 242), (150, 150, 162)


def font(name, size):
    return ImageFont.truetype(str(C.FONT_DIR / f"{name}.ttf"), size)


F_HEAD, F_LAB, F_SMALL = font("montserrat-500", 40), font("montserrat-500", 28), font("montserrat-500", 22)
F_NAME = font("syncopate-700", 30)


def crop(img, w):
    x0 = (BW - w) // 2
    y0 = (BH - STRIP_H) // 2
    return img.crop((x0, y0, x0 + w, y0 + STRIP_H))


def rounded(im, r):
    m = Image.new("L", (im.width * 4, im.height * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, m.width - 1, m.height - 1), r * 4, fill=255)
    out = im.convert("RGBA")
    out.putalpha(m.resize(im.size, Image.LANCZOS))
    return out


def circle(im, d):
    """The picture scaled to d px and cut to a circle (anti-aliased), as YouTube shows it."""
    a = np.asarray(im.convert("RGB"), np.float32) / 255
    a = C.cv2.resize(a, (d, d), interpolation=C.cv2.INTER_AREA)
    ss = 4
    m = Image.new("L", (d * ss, d * ss), 0)
    ImageDraw.Draw(m).ellipse((0, 0, d * ss - 1, d * ss - 1), fill=255)
    out = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).convert("RGBA")
    out.putalpha(m.resize((d, d), Image.LANCZOS))
    return out


def dashed_rect(dr, box, col, w=4, dash=18, gap=10):
    x0, y0, x1, y1 = box
    for (a, b, horiz, fixed) in ((x0, x1, True, y0), (x0, x1, True, y1), (y0, y1, False, x0), (y0, y1, False, x1)):
        p = a
        while p < b:
            q = min(p + dash, b)
            dr.line(((p, fixed), (q, fixed)) if horiz else ((fixed, p), (fixed, q)), fill=col, width=w)
            p = q + gap


def banner_preview(name, profile_name):
    ban = Image.open(OUT / "banners" / f"{name}.png").convert("RGB")
    prof = Image.open(OUT / "profiles" / f"{profile_name}-800.png").convert("RGB")
    CW = 2200
    S = 2000 / BW
    sections = []

    # ---- 1. full image with the crop boxes ----
    tv_w, tv_h = 2000, int(BH * S)
    canvas_h = 150 + tv_h + 120
    sec = Image.new("RGB", (CW, canvas_h), BG)
    dr = ImageDraw.Draw(sec)
    dr.text((100, 40), f"{name}.png   ·   2560 × 1440", font=F_HEAD, fill=TXT)
    dr.text((100, 96), "Full image (what a TV shows).  The boxes are what desktop, tablet and phone show.",
            font=F_SMALL, fill=DIM)
    sec.paste(ban.resize((tv_w, tv_h), Image.LANCZOS), (100, 150))
    ov = Image.new("RGBA", (CW, canvas_h), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    y0 = 150 + (BH - STRIP_H) / 2 * S
    y1 = y0 + STRIP_H * S
    # dim what only the TV sees, so the strip stands out
    od.rectangle((100, 150, 100 + tv_w, y0), fill=(0, 0, 0, 90))
    od.rectangle((100, y1, 100 + tv_w, 150 + tv_h), fill=(0, 0, 0, 90))
    sec = Image.alpha_composite(sec.convert("RGBA"), ov).convert("RGB")
    dr = ImageDraw.Draw(sec)
    for k, (lab, w, col) in enumerate(CROPS):
        x0 = 100 + (BW - w) / 2 * S
        inset = 3 + k * 6
        dashed_rect(dr, (x0 + inset, y0 + inset, x0 + w * S - inset, y1 - inset), col, 4)
    lx = 100
    for lab, w, col in CROPS:
        dr.rectangle((lx, 150 + tv_h + 40, lx + 26, 150 + tv_h + 66), fill=col)
        t = f"{lab}  {w}×{STRIP_H}"
        dr.text((lx + 40, 150 + tv_h + 36), t, font=F_LAB, fill=TXT)
        lx += 60 + dr.textlength(t, font=F_LAB) + 60
    sections.append(sec)

    # ---- 2. the three crops on their own, same scale ----
    for lab, w, col in CROPS:
        cw, ch = int(w * S), int(STRIP_H * S)
        sec = Image.new("RGB", (CW, ch + 110), BG)
        dr = ImageDraw.Draw(sec)
        dr.rectangle((100, 30, 120, 50), fill=col)
        dr.text((135, 22), f"{lab}  ·  {w} × {STRIP_H}", font=F_LAB, fill=TXT)
        sec.paste(crop(ban, w).resize((cw, ch), Image.LANCZOS), (100 + (2000 - cw) // 2, 80))
        sections.append(sec)

    # ---- 3. mock-ups: a channel header on desktop and on a phone (generic layout, no platform branding) ----
    sec = Image.new("RGB", (CW, 960), BG)
    dr = ImageDraw.Draw(sec)
    dr.text((100, 30), "How it sits on a channel page (generic mock-up)", font=F_LAB, fill=TXT)
    # desktop
    dx, dy, dw = 100, 90, 1300
    dr.rounded_rectangle((dx, dy, dx + dw, dy + 760), 22, fill=PANEL)
    strip = crop(ban, 2560).resize((dw - 60, int((dw - 60) * STRIP_H / 2560)), Image.LANCZOS)
    sec.paste(rounded(strip, 18), (dx + 30, dy + 40), rounded(strip, 18))
    av = circle(prof, 150)
    sec.paste(av, (dx + 30, dy + 80 + strip.height), av)
    dr.text((dx + 210, dy + 105 + strip.height), "ASTRIS PRODUCTIONS", font=F_NAME, fill=TXT)
    for i, wfrac in enumerate((0.42, 0.30)):
        dr.rounded_rectangle((dx + 210, dy + 165 + strip.height + i * 40, dx + 210 + int(800 * wfrac),
                              dy + 185 + strip.height + i * 40), 10, fill=(52, 52, 62))
    for i in range(4):
        tx = dx + 30 + i * 312
        dr.rounded_rectangle((tx, dy + 330 + strip.height, tx + 290, dy + 330 + strip.height + 163), 14, fill=(40, 40, 48))
    dr.text((dx + 30, dy + 715), "DESKTOP", font=F_SMALL, fill=DIM)
    # phone
    px, py, pw, ph = 1520, 90, 400, 760
    dr.rounded_rectangle((px - 14, py - 14, px + pw + 14, py + ph + 14), 56, fill=(46, 46, 54))
    dr.rounded_rectangle((px, py, px + pw, py + ph), 44, fill=PANEL)
    strip = crop(ban, 1546).resize((pw - 32, int((pw - 32) * STRIP_H / 1546)), Image.LANCZOS)
    sec.paste(rounded(strip, 12), (px + 16, py + 70), rounded(strip, 12))
    av = circle(prof, 92)
    sec.paste(av, (px + 16, py + 90 + strip.height), av)
    dr.text((px + 124, py + 110 + strip.height), "ASTRIS PRODUCTIONS", font=font("syncopate-700", 17), fill=TXT)
    dr.rounded_rectangle((px + 124, py + 150 + strip.height, px + 300, py + 164 + strip.height), 7, fill=(52, 52, 62))
    for i in range(2):
        ty = py + 230 + strip.height + i * 230
        dr.rounded_rectangle((px + 16, ty, px + pw - 16, ty + 200), 14, fill=(40, 40, 48))
    dr.text((px + 16, py + ph + 30), "PHONE", font=F_SMALL, fill=DIM)
    sections.append(sec)

    H = sum(s.height for s in sections) + 40
    out = Image.new("RGB", (CW, H), BG)
    y = 0
    for s in sections:
        out.paste(s, (0, y))
        y += s.height
    path = PREV / f"preview-{name}.png"
    out.save(path, optimize=True)
    return path


def profile_preview(name):
    src = Image.open(OUT / "profiles" / f"{name}-1600.png").convert("RGB")
    W, H = 2200, 1180
    out = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(out)
    dr.text((100, 40), f"{name}.png   ·   1600 × 1600  (+ 800 × 800)", font=F_HEAD, fill=TXT)
    dr.text((100, 96), "YouTube crops the square to a circle.  Left: what gets cut away.  Right: real sizes, dark and light.",
            font=F_SMALL, fill=DIM)
    # large: the square faintly, the circle at full strength
    D = 920
    sq = src.resize((D, D), Image.LANCZOS)
    faint = Image.blend(Image.new("RGB", (D, D), BG), sq, 0.22)
    out.paste(faint, (100, 180))
    c = circle(src, D)
    out.paste(c, (100, 180), c)
    dr.ellipse((100, 180, 100 + D, 180 + D), outline=(255, 255, 255), width=2)
    # small sizes on dark and on light
    sizes = [176, 120, 88, 48, 36, 24]
    for row, (bg, fg) in enumerate(((PANEL, TXT), ((246, 246, 248), (30, 30, 36)))):
        x0, y0 = 1120, 200 + row * 480
        dr.rounded_rectangle((x0, y0, x0 + 980, y0 + 420), 24, fill=bg)
        dr.text((x0 + 30, y0 + 20), "dark mode" if row == 0 else "light mode", font=F_SMALL, fill=fg)
        x = x0 + 40
        for d in sizes:
            c = circle(src, d)
            out.paste(c, (x, int(y0 + 230 - d / 2)), c)
            dr.text((x + d / 2 - 22, y0 + 340), f"{d}px", font=F_SMALL, fill=fg)
            x += d + 60
    path = PREV / f"preview-{name}.png"
    out.save(path, optimize=True)
    return path


if __name__ == "__main__":
    PREV.mkdir(parents=True, exist_ok=True)
    for f in sorted((OUT / "banners").glob("banner-*.png")):
        name = f.stem
        pname = "profile-" + name[len("banner-"):]
        p = banner_preview(name, pname)
        print(f"{p.name}  {Image.open(p).size}  {p.stat().st_size / 1e6:.2f} MB", flush=True)
    for f in sorted((OUT / "profiles").glob("profile-*-1600.png")):
        name = f.stem[: -len("-1600")]
        p = profile_preview(name)
        print(f"{p.name}  {Image.open(p).size}  {p.stat().st_size / 1e6:.2f} MB", flush=True)
