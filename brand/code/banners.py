"""
ASTRIS PRODUCTIONS - Part 4: YouTube banners (2560x1440, all logo/type inside the 1546x423 safe area) and
matching profile pictures (1600x1600 + 800x800, everything important inside the central circle).
Sets: 1 retro grainy (16mm), 2 retro VHS (synthwave), 3 retro 70s, 4 surprise ("of the stars": the logo as a
constellation under a rainbow aurora), bonus 5 rainbow paper collage, 6 neon sign, 7 blueprint.
Usage: python3 banners.py [set numbers]
"""
import io
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import common as C
import kit as K

cv2 = C.cv2
BW, BH = 2560, 1440
SAFE = (BW // 2 - 773, BH // 2 - 211, BW // 2 + 773, BH // 2 + 212)
PS = 1600
OUT = C.ROOT.parent / "output"
LOGO = C.Logo()


def grid(h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx, yy


BX, BY = grid(BH, BW)
PX, PY = grid(PS, PS)


def rgb(h):
    return K.rgb(h)


def comp(img, m, col):
    return img * (1 - m[..., None]) + np.asarray(col, np.float32) * m[..., None]


def blur(m, s):
    return cv2.GaussianBlur(m, (0, 0), s)


def mask(polys, shape):
    return C.poly_mask_ss(polys, shape=shape, ss=2)


EXTENTS = []          # every lockup drawn records its exact ink bounds here (checked against SAFE in run())


def hlockup(logo_h, fa, fp, cap_a, cap_p, track_a, gap=70, centre=(BW / 2, BH / 2), p_track=None, script=False):
    """Horizontal lockup that fits the safe area: logo on the left, ASTRIS over PRODUCTIONS on the right."""
    _, aw = C.layout_word(K.font(fa), "ASTRIS", cap_a, track_a)
    text_w = aw
    total = logo_h * LOGO.aspect + gap + text_w
    x0 = centre[0] - total / 2
    lc = (x0 + logo_h * LOGO.aspect / 2, centre[1])
    tcx = x0 + logo_h * LOGO.aspect + gap + text_w / 2
    block = cap_a + 0.42 * cap_a + cap_p
    a_base = centre[1] - block / 2 + cap_a
    p_base = a_base + 0.42 * cap_a + cap_p
    a, _ = K.line_letters(fa, "ASTRIS", cap_a, tcx, a_base, track_a)
    if script:
        p, _ = K.line_letters(fp, "Productions", cap_p, tcx + aw * 0.12, p_base + cap_p * 0.15, 0.0)
    else:
        p, _ = K.line_letters(fp, "PRODUCTIONS", cap_p, tcx, p_base, 0.0 if p_track is None else p_track,
                              width_px=aw * 0.99 if p_track is None else None)
    polys = LOGO.polys_px(lc[0], lc[1], logo_h)
    pts = np.concatenate(list(polys) + [q for L in (a, p) for d in L for q in d["polys"]])
    EXTENTS.append((float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max())))
    return polys, a, p, (x0, centre[1] - max(logo_h, block) / 2, x0 + total, centre[1] + max(logo_h, block) / 2)


def letters_mask(L, shape):
    return K.letters_mask(L, shape=shape)


def grain(img, amt, size, seed):
    h, w = img.shape[:2]
    g = cv2.GaussianBlur(np.random.default_rng(seed).standard_normal((h, w)).astype(np.float32), (0, 0), size)
    g /= g.std() + 1e-6
    lum = img.mean(axis=2)
    return img + (g * amt * (0.25 + 2.4 * lum * np.clip(1 - lum, 0, 1)))[..., None]


def vignette(img, k=0.35):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    return img * (1 - k * np.clip(r - 0.35, 0, 1) ** 1.5)[..., None]


def glow(img, m, col, sig=(12, 40), w=(0.6, 0.4), k=1.0):
    g = sum(blur(m, s) * ww for s, ww in zip(sig, w))
    return img + g[..., None] * np.asarray(col, np.float32) * k


def bevel(m, width, height):
    return K.bevel_normals(m, width, height)


def env_metal(n, ramp, uu, vv, bend=1.0, light=(-0.4, -0.8, 0.6)):
    return K.env_metal(n, ramp, uu, vv, bend, light)


def save_png(img, path, max_mb=6.0):
    """8-bit PNG; if it's over the limit, gently quantise (dithered) until it fits."""
    im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    im.save(path, optimize=True)
    if path.stat().st_size > max_mb * 1e6:
        q = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).convert("RGB")
        q.save(path, optimize=True)
    return path.stat().st_size / 1e6


# ================================================================================================
# 1 - RETRO GRAINY (16mm)
# ================================================================================================
CREAM, ORANGE, SEPIA = rgb("#f2e2bf"), rgb("#d9692a"), rgb("#1b130d")


def film_strip_band(h, w, y0, height, seed):
    """A strip of film running across the image: dark base, sprocket holes along both edges."""
    m = np.zeros((h, w), np.float32)
    holes = np.zeros((h, w), np.float32)
    cv2.rectangle(m, (0, int(y0)), (w, int(y0 + height)), 1.0, -1)
    pitch = height * 0.36
    hs = height * 0.13
    for x in np.arange(-pitch, w + pitch, pitch):
        for yy_ in (y0 + height * 0.08, y0 + height * 0.92 - hs):
            cv2.rectangle(holes, (int(x), int(yy_)), (int(x + hs * 1.35), int(yy_ + hs)), 1.0, -1, cv2.LINE_AA)
    return m, holes


def retro_grainy_bg(h, w, xx, yy, seed=1):
    img = np.zeros((h, w, 3), np.float32) + SEPIA
    img *= (1.25 - 0.55 * np.hypot((xx - w * 0.45) / w, (yy - h * 0.5) / h))[..., None]
    # a dusty projector beam sweeping in from the upper left
    ang = np.arctan2(yy - (-0.1 * h), xx - (-0.15 * w))
    beam = np.exp(-((ang - 0.42) / 0.11) ** 2) * np.clip(np.hypot(xx + 0.15 * w, yy + 0.1 * h) / w, 0, 1)
    dust = (np.random.default_rng(seed).random((h // 2, w // 2)) > 0.9985).astype(np.float32)
    dust = cv2.resize(cv2.GaussianBlur(dust, (0, 0), 0.8), (w, h))
    img += (beam * 0.32)[..., None] * rgb("#ffd9a0") + (dust * beam * 2.0)[..., None]
    return img


def retro_finish(img, seed, strength=1.0):
    h, w = img.shape[:2]
    lum = img.mean(axis=2, keepdims=True)
    img = img * 0.88 + lum * 0.12
    img = img + np.clip(1 - lum * 2.2, 0, 1) * np.array([-0.01, 0.022, 0.03], np.float32)
    img = 0.06 + img * np.array([1.04, 0.98, 0.88], np.float32) * 0.9
    hi = np.clip((img.max(axis=2) - 0.62) / 0.38, 0, 1)
    img += (blur(hi, 14) * 0.6 + blur(hi, 40) * 0.4)[..., None] * np.array([1.0, 0.32, 0.12], np.float32) * 0.5
    dark, light = K.dust_layer(seed, 909, density=2.5 * strength, shape=(h, w))
    img = img * (1 - 0.8 * dark[..., None]) + light[..., None] * 0.6
    img = grain(img, 0.05 * strength, 1.2, seed)
    return vignette(img, 0.45)


def set1_banner():
    img = retro_grainy_bg(BH, BW, BX, BY, 11)
    for y0 in (40, BH - 230):
        band, holes = film_strip_band(BH, BW, y0, 190, 12)
        img = comp(img, band * 0.92, rgb("#0d0906"))
        img = comp(img, holes, rgb("#3a2a1c"))
    polys, a, p, _ = hlockup(330, "abril-fatface-400", "rokkitt-700", 118, 40, 0.14, gap=80)
    m = mask(polys, (BH, BW))
    img = comp(img, m, CREAM)
    img = comp(img, letters_mask(a, (BH, BW)), CREAM)
    img = comp(img, letters_mask(p, (BH, BW)), ORANGE * 1.1)
    deco = np.zeros((BH, BW), np.float32)
    x0, y0, x1, y1 = SAFE
    for inset, th in ((10, 4), (28, 2)):
        cv2.rectangle(deco, (x0 + inset, y0 + inset), (x1 - inset, y1 - inset), 1.0, th, cv2.LINE_AA)
    img = comp(img, deco * 0.7, ORANGE * 0.85)
    return retro_finish(img, 101)


def set1_profile():
    img = retro_grainy_bg(PS, PS, PX, PY, 13)
    r = np.hypot(PX - PS / 2, PY - PS / 2)
    ring = np.clip((14 - np.abs(r - 640)) / 1.5, 0, 1) + np.clip((5 - np.abs(r - 604)) / 1.5, 0, 1)
    img = comp(img, ring * 0.8, ORANGE)
    m = mask(LOGO.polys_px(PS / 2, PS / 2 + 10, 760), (PS, PS))
    img = comp(img, m, CREAM)
    return retro_finish(img, 102)


# ================================================================================================
# 2 - RETRO VHS (synthwave)
# ================================================================================================
CHROME = [(0.0, "#12052a"), (0.30, "#3b1a6e"), (0.45, "#9a6ad8"), (0.49, "#ff8ad8"), (0.51, "#ffffff"), (0.54, "#ffb347"),
          (0.62, "#4ad0ff"), (0.82, "#d4f4ff"), (1.0, "#ffffff")]


def synth_world(h, w, xx, yy, hz, sun_c, sun_r, seed=2):
    keys = [(0.0, "#0b0326"), (0.35, "#2a0b4d"), (0.62, "#7a1a7a"), (0.82, "#ff3d8b"), (1.0, "#ff9a3d")]
    v = np.clip(yy / hz, 0, 1)
    img = np.stack([np.interp(v, [k for k, _ in keys], [rgb(c)[i] for _, c in keys]) for i in range(3)], -1).astype(np.float32)
    r = np.random.default_rng(seed)
    st = np.zeros((h, w), np.uint8)          # 8-bit layers: OpenCV only anti-aliases 8-bit images
    for _ in range(int(w * h / 9000)):
        x, y = r.uniform(0, w), r.uniform(0, hz * 0.8)
        cv2.circle(st, (int(x * 4), int(y * 4)), int(4 * r.uniform(0.8, 2.2)), int(255 * r.uniform(0.3, 1.0)), -1, cv2.LINE_AA, 2)
    img += (st.astype(np.float32) / 255)[..., None] * 0.9
    d = np.hypot(xx - sun_c[0], yy - sun_c[1])
    sv = np.clip((yy - (sun_c[1] - sun_r)) / (2 * sun_r), 0, 1)
    scol = np.stack([np.interp(sv, [0, 0.45, 1], [rgb(c)[i] for c in ("#fff36b", "#ff9a3d", "#ff2d8f")]) for i in range(3)], -1)
    rel = (yy - sun_c[1]) / sun_r
    gap = np.clip(0.10 + 0.45 * np.clip((rel + 0.45) / 1.0, 0, 1), 0, 0.6)
    bars = np.where(rel > -0.45, (((rel * 7) % 1.0) > gap).astype(np.float32), 1.0)
    sun = np.clip((sun_r - d) / 2, 0, 1) * bars * (yy < hz)
    img = img * (1 - sun[..., None]) + scol * 0.9 * sun[..., None]
    img += (np.exp(-np.clip(d - sun_r, 0, None) / (sun_r * 0.4)) * 0.3 * (d > sun_r))[..., None] * rgb("#ff4a8a")
    floor = (yy > hz).astype(np.float32)
    img = img * (1 - floor[..., None]) + rgb("#14052a") * floor[..., None]
    g = np.zeros((h, w), np.uint8)
    for k in range(-40, 41):
        cv2.line(g, (int((w / 2 + k * w * 0.016) * 16), int(hz * 16)), (int((w / 2 + k * w * 0.22) * 16), int((h + 400) * 16)), 255, 2, cv2.LINE_AA, 4)
    for j in range(1, 30):
        y = hz + (h - hz) * 0.9 / (j * 0.55)
        if y < h + 5:
            cv2.line(g, (0, int(y * 16)), (w * 16, int(y * 16)), 255, 2, cv2.LINE_AA, 4)
    g = g.astype(np.float32) / 255 * floor
    img += g[..., None] * rgb("#ff2bd6") * 1.1
    img += (np.exp(-np.abs(yy - hz) / 12) * 0.6)[..., None] * rgb("#ff7ad9")
    return img


def vhs_finish(img, seed):
    h, w = img.shape[:2]
    r = np.random.default_rng(seed)
    Y = img @ np.array([0.299, 0.587, 0.114], np.float32)
    ch = np.roll(cv2.blur(img - Y[..., None], (25, 1)), 6, axis=1)
    img = Y[..., None] + ch * 1.15
    for y0 in (int(h * 0.18), int(h * 0.83)):
        for y in range(y0, y0 + 60, 2):
            img[y:y + 2] = np.roll(img[y:y + 2], int(r.normal(0, 18)), axis=1)
        img[y0:y0 + 60] += r.random((60, 1, 1)).astype(np.float32) * 0.12
    for y in range(h - 30, h, 2):
        img[y:y + 2] = np.roll(img[y:y + 2], int(r.normal(20, 6)), axis=1)
    s = 1 - 0.18 * (0.5 + 0.5 * np.cos(2 * math.pi * np.arange(h, dtype=np.float32) / 4))
    img = img * s[:, None, None]
    hi = np.clip((img.max(axis=2) - 0.6) / 0.4, 0, 1)
    img += (blur(hi, 10) * 0.5 + blur(hi, 30) * 0.4)[..., None] * rgb("#ff7ad9") * 0.5
    return vignette(img, 0.4)


def chrome_mask_fill(img, m, xx, yy, cx, cy, h, key=16):
    k = np.clip((key - cv2.distanceTransform((m < 0.5).astype(np.uint8), cv2.DIST_L2, 5)) / 1.5, 0, 1)
    img = comp(img, k, rgb("#14052a"))
    n = bevel(m, max(6, h * 0.05), 70)
    ch = env_metal(n, CHROME, (xx - cx) / h, (yy - cy) / h, 1.1, (-0.4, -0.85, 0.5))
    return img * (1 - m[..., None]) + ch * m[..., None]


def set2_banner():
    hz = 1000
    img = synth_world(BH, BW, BX, BY, hz, (BW / 2, hz - 120), 420)
    polys, a, p, box = hlockup(330, "orbitron-900", "mr-dafoe-400", 112, 92, 0.16, gap=80, script=True,
                               centre=(BW / 2, BH / 2 - 10))
    m = mask(polys, (BH, BW))
    lc = np.concatenate(polys).mean(0)
    img = glow(img, m, rgb("#ff2bd6"), (10, 30), (0.5, 0.4), 0.8)
    img = chrome_mask_fill(img, m, BX, BY, lc[0], lc[1], 330)
    am = letters_mask(a, (BH, BW))
    img = glow(img, am, rgb("#4ad0ff"), (6, 20), (0.4, 0.3), 0.8)
    img = chrome_mask_fill(img, am, BX, BY, BW / 2, BH / 2 - 60, 120, key=10)
    pm = letters_mask(p, (BH, BW))
    # neon script with a dark keyline, so it reads over the sun
    key = np.clip(blur(cv2.dilate(pm, np.ones((15, 15), np.uint8)), 1.5), 0, 1)
    img = img * (1 - 0.55 * blur(key, 14))[..., None]
    img = comp(img, key, rgb("#1a0530"))
    img = glow(img, pm, rgb("#ff2bd6"), (5, 18), (0.9, 0.6), 1.5)
    tv = np.clip((BY - (BH / 2 + 20)) / 90, 0, 1)
    pcol = rgb("#fff4fd") * (1 - tv[..., None]) + rgb("#ff5fd8") * tv[..., None]
    img = img * (1 - pm[..., None]) + pcol * pm[..., None]
    osd = Image.new("L", (BW, BH), 0)
    dr = ImageDraw.Draw(osd)
    f = ImageFont.truetype(str(C.FONT_DIR / "vt323-400.ttf"), 64)
    dr.polygon([(120, 112), (120, 160), (160, 136)], fill=255)
    dr.text((180, 100), "PLAY", font=f, fill=255)
    dr.text((BW - 380, BH - 150), "SP  0:00:07", font=f, fill=255)
    img = comp(img, np.asarray(osd, np.float32) / 255 * 0.85, [0.85, 1.0, 0.85])
    return vhs_finish(img, 202)


def set2_profile():
    hz = 1150
    img = synth_world(PS, PS, PX, PY, hz, (PS / 2, hz - 330), 560, seed=3)
    polys = LOGO.polys_px(PS / 2, 760, 700)
    m = mask(polys, (PS, PS))
    img = glow(img, m, rgb("#ff2bd6"), (12, 36), (0.5, 0.4), 0.8)
    img = chrome_mask_fill(img, m, PX, PY, PS / 2, 760, 700, key=20)
    return vhs_finish(img, 203)


# ================================================================================================
# 3 - RETRO 70s
# ================================================================================================
STRIPES = [rgb(h) for h in ("#e8641e", "#f2a922", "#7a3e1d", "#f6e7c8", "#1f9e98")]
BROWN = rgb("#4a2412")


def print_finish(img, seed, xx, yy):
    h, w = img.shape[:2]
    wear = np.clip((cv2.resize(K.fbm(h // 4, w // 4, seed, 6), (w, h)) - 0.66) * 7, 0, 1)
    paper = K.paper(h, w, rgb("#f3e3c4"), seed=seed + 1, fibres=0.02, grain=0.03, mottle=0.08)
    img = img * (1 - 0.35 * wear[..., None]) + paper * 0.35 * wear[..., None]
    lum = img.mean(axis=2)
    yy_, xx_ = np.mgrid[0:h, 0:w].astype(np.float32)
    c, s = math.cos(0.26), math.sin(0.26)
    u, v = (xx_ * c + yy_ * s) / 16, (-xx_ * s + yy_ * c) / 16
    d = np.hypot(u - np.floor(u) - 0.5, v - np.floor(v) - 0.5)
    dots = np.clip((np.sqrt(np.clip(0.55 - lum, 0, 1) * 0.6 / math.pi) * 1.05 - d) * 16 / 1.2 + 0.5, 0, 1)
    img = img * (1 - 0.25 * dots[..., None])
    img = img * (0.95 + 0.05 * paper.mean(axis=2, keepdims=True) / paper.mean())
    return grain(img, 0.02, 1.0, seed)


def seventies_art(h, w, xx, yy, cx, cy, stripes_y):
    img = K.paper(h, w, rgb("#f3e3c4"), seed=31, fibres=0.02, grain=0.03, mottle=0.08)
    ang = np.arctan2(yy - cy, xx - cx)
    rad = np.hypot(xx - cx, yy - cy)
    rays = blur((np.sin(ang * 18) > 0).astype(np.float32), 1.0)
    rc = rgb("#f6b23c")[None, None] * (1 - np.clip(rad / (w * 0.7), 0, 1))[..., None] + rgb("#e8641e")[None, None] * np.clip(rad / (w * 0.7), 0, 1)[..., None]
    img = img * (1 - (rays * 0.8)[..., None]) + rc * (rays * 0.8)[..., None]
    # full-width stacked supergraphic stripes with a groovy curve
    for (y0, amp) in stripes_y:
        for j, col in enumerate(STRIPES):
            yc = y0 + j * 46 + amp * np.sin(xx / w * math.pi * 2 + 0.6)
            band = np.clip((23 - np.abs(yy - yc)) / 1.2, 0, 1)
            img = comp(img, cv2.warpAffine(band, np.float32([[1, 0, 3 * (j % 2)], [0, 1, -2 * (j % 2)]]), (w, h)), col)
    return img


def stripe_logo(img, polys, shape, outline=(30, 22, 14)):
    m = mask(polys, shape)
    allp = np.concatenate(polys)
    y0, y1 = allp[:, 1].min(), allp[:, 1].max()
    yy = np.mgrid[0:shape[0], 0:shape[1]][0].astype(np.float32)
    bandi = np.clip(((yy - y0) / (y1 - y0) * 5).astype(np.int32), 0, 4)
    fill = np.zeros(shape + (3,), np.float32)
    for j, c in enumerate(STRIPES):
        fill[bandi == j] = c
    b = (m > 0.5).astype(np.uint8)
    for rad, col in zip(outline, (STRIPES[4], STRIPES[3], BROWN)):
        ring = cv2.dilate(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (rad * 2 + 1, rad * 2 + 1))).astype(np.float32)
        img = comp(img, blur(ring, 1.0), col)
    return img * (1 - m[..., None]) + fill * m[..., None]


def set3_banner():
    img = seventies_art(BH, BW, BX, BY, BW / 2, BH / 2, [(170, 40), (BH - 400, -40)])
    disc = np.clip((560 - np.hypot((BX - BW / 2) / 1.6, BY - BH / 2)) / 2, 0, 1)
    img = comp(img, np.clip((574 - np.hypot((BX - BW / 2) / 1.6, BY - BH / 2)) / 2, 0, 1), BROWN)
    img = comp(img, disc, rgb("#fbe6bd"))
    polys, a, p, _ = hlockup(320, "shrikhand-400", "righteous-400", 120, 40, 0.06, gap=90)
    img = stripe_logo(img, polys, (BH, BW), (22, 16, 10))
    am = letters_mask(a, (BH, BW))
    b = (am > 0.5).astype(np.uint8)
    for rad, col in ((20, STRIPES[4]), (14, STRIPES[0]), (8, STRIPES[1])):
        ring = cv2.dilate(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (rad * 2 + 1, rad * 2 + 1))).astype(np.float32)
        img = comp(img, blur(ring, 1.0), col)
    img = comp(img, am, rgb("#fbf1dc"))
    img = comp(img, letters_mask(p, (BH, BW)), BROWN)
    return print_finish(img, 301, BX, BY)


def set3_profile():
    img = seventies_art(PS, PS, PX, PY, PS / 2, PS / 2, [(150, 30), (PS - 380, -30)])
    r = np.hypot(PX - PS / 2, PY - PS / 2)
    img = comp(img, np.clip((612 - r) / 2, 0, 1), BROWN)
    img = comp(img, np.clip((596 - r) / 2, 0, 1), rgb("#fbe6bd"))
    img = stripe_logo(img, LOGO.polys_px(PS / 2, PS / 2 + 10, 700), (PS, PS))
    return print_finish(img, 302, PX, PY)


# ================================================================================================
# 4 - SURPRISE: "of the stars" - the logo as a constellation under a rainbow aurora
# ================================================================================================
def aurora(h, w, xx, yy, seed, ribbons):
    """Rainbow aurora curtains: each ribbon has a bright, wavy lower edge and fine vertical rays that fade upward;
    the hue sweeps through the spectrum along the ribbon."""
    r = np.random.default_rng(seed)
    out = np.zeros((h, w, 3), np.float32)
    x1 = np.arange(w, dtype=np.float32)
    for (y_l, y_r, amp, waves, height, k, hue0, hue_span) in ribbons:
        ph = r.uniform(0, 2 * math.pi, 3)
        edge = (y_l + (y_r - y_l) * x1 / w + amp * np.sin(x1 / w * math.pi * waves + ph[0])
                + amp * 0.35 * np.sin(x1 / w * math.pi * waves * 2.7 + ph[1]))
        # rays: 1-D noise across x at a few scales, so the curtain has fine striations and broader folds
        rays = np.zeros(w, np.float32)
        for scale, wt in ((3, 0.45), (9, 0.35), (40, 0.35), (160, 0.4)):
            n = r.standard_normal(w // scale + 3).astype(np.float32)
            rays += np.interp(x1 / scale, np.arange(len(n)), n) * wt
        rays = np.clip(0.55 + 0.35 * rays, 0.05, 1.3)
        ray_mod = np.clip(0.35 + 0.75 * np.interp(x1 / 300, np.arange(w // 300 + 3),
                                                   r.uniform(0, 1, w // 300 + 3)), 0, 1)
        d = edge[None, :] - yy                      # height above the lower edge (px)
        dp = np.clip(d, 0, None)
        above = np.exp(-dp / height) * (1 - np.exp(-dp / 5))
        lip = np.exp(-((d - 14) / 16) ** 2) * 1.6          # the bright lower lip of the curtain
        below = np.exp(-np.clip(-d, 0, None) / 6) * (d <= 0)
        prof = above + lip + below * 0.5
        sl = np.clip(xx + d * 0.06, 0, w - 1).astype(np.int32)   # rays lean a touch
        a = prof * (rays * ray_mod)[sl] * k
        hue = C.hue_wheel(hue0 + xx / w * hue_span + np.clip(d, 0, None) / height * 0.10)
        out += hue * a[..., None]
    # soft bloom so the curtains glow rather than look painted
    return out + blur(out, 14) * 0.5 + blur(out, 50) * 0.22


def night(h, w, xx, yy, seed, ribbons=None):
    img = np.zeros((h, w, 3), np.float32)
    v = yy / h
    img += (rgb("#04051a") * (1 - v[..., None]) + rgb("#0c0a2c") * v[..., None])
    neb = cv2.resize(K.fbm(h // 8, w // 8, seed, 6), (w, h))
    img += (np.clip(neb - 0.45, 0, 1) ** 1.5)[..., None] * rgb("#3a2a8a") * 0.7
    if ribbons is None:
        ribbons = [(h * 0.52, h * 0.30, h * 0.05, 2.2, h * 0.16, 0.42, 0.95, 0.85),
                   (h * 0.70, h * 0.58, h * 0.04, 3.1, h * 0.10, 0.22, 0.25, 0.75)]
    img += aurora(h, w, xx, yy, seed + 7, ribbons)
    r = np.random.default_rng(seed)
    st = np.zeros((h, w), np.uint8)
    for _ in range(int(w * h / 2200)):
        x, y = r.uniform(0, w), r.uniform(0, h)
        b = r.uniform(0.15, 1.0) ** 2
        cv2.circle(st, (int(x * 4), int(y * 4)), int(4 * (0.6 + 1.6 * b)), int(255 * b), -1, cv2.LINE_AA, 2)
    st = st.astype(np.float32) / 255
    img += (st + blur(st, 3) * 0.6)[..., None] * rgb("#e8eeff")
    return img


def constellation(img, polys, shape, star_r=10, line_w=3, glow_k=1.0):
    """The logo as a star chart (same style as the constellation ident): sparkling stars on the true corners
    (plus one on each long edge), fine lines joining them, the sprocket holes as a row of small quiet stars."""
    m = mask(polys, shape)
    img = img + (m * 0.10)[..., None] * rgb("#c8d4ff")
    img = glow(img, m, rgb("#8fa8ff"), (20, 60), (0.25, 0.2), 0.6 * glow_k)
    areas = [abs(cv2.contourArea(q.astype(np.float32))) for q in polys]
    allp = np.concatenate(polys)
    h = allp[:, 1].max() - allp[:, 1].min()
    ln = np.zeros(shape, np.uint8)
    corners, holes = [], []
    for q, a in zip(polys, areas):
        if a > 0.05 * max(areas):
            ap = cv2.approxPolyDP(q.astype(np.float32).reshape(-1, 1, 2), max(2.0, 0.0105 * h), True).reshape(-1, 2)
            cv2.polylines(ln, [np.round(ap * 16).astype(np.int32)], True, 255, line_w, cv2.LINE_AA, 4)
            for j in range(len(ap)):
                a_, b_ = ap[j], ap[(j + 1) % len(ap)]
                corners.append(a_)
                if np.linalg.norm(b_ - a_) > 0.68 * h:
                    corners.append((a_ + b_) / 2)
        else:
            holes.append(q.mean(0))
    ln = ln.astype(np.float32) / 255
    img = img + (ln * 0.85)[..., None] * rgb("#dfe6ff") + blur(ln, 4)[..., None] * rgb("#8fa8ff") * 0.6
    sp = np.zeros(shape, np.uint8)
    spikes = np.zeros(shape, np.uint8)
    for p in corners:
        cv2.circle(sp, (int(p[0] * 16), int(p[1] * 16)), int(16 * star_r), 255, -1, cv2.LINE_AA, 4)
        for a in (0, math.pi / 2):
            dv = np.array([math.cos(a), math.sin(a)]) * star_r * 4.5
            cv2.line(spikes, tuple(np.round((p - dv) * 16).astype(int)), tuple(np.round((p + dv) * 16).astype(int)), 178, 2, cv2.LINE_AA, 4)
    for p in holes:
        cv2.circle(sp, (int(p[0] * 16), int(p[1] * 16)), int(16 * star_r * 0.42), 230, -1, cv2.LINE_AA, 4)
    sp = sp.astype(np.float32) / 255
    spikes = spikes.astype(np.float32) / 255
    img = img + (sp * 1.4)[..., None] + (blur(sp, star_r) * 1.2 + blur(spikes, 1.0) * 0.8)[..., None] * rgb("#e8eeff")
    return img


def set4_banner():
    img = night(BH, BW, BX, BY, 41)
    polys, a, p, _ = hlockup(340, "syncopate-700", "montserrat-500", 104, 34, 0.30, gap=90)
    am = letters_mask(a, (BH, BW))
    pm = letters_mask(p, (BH, BW))
    # a soft pool of night sky behind the type so it reads cleanly over the aurora
    sh = np.clip(blur(cv2.dilate(np.maximum(am, pm), np.ones((41, 41), np.uint8)), 45) * 1.6, 0, 1)
    img = img * (1 - 0.6 * sh)[..., None]
    img = constellation(img, polys, (BH, BW), 9, 3)
    img = glow(img, am, rgb("#9fb4ff"), (8, 24), (0.4, 0.3), 0.8)
    img = comp(img, am, rgb("#f4f6ff"))
    img = comp(img, pm, rgb("#c9d2ff"))
    img = grain(img, 0.015, 1.0, 401)
    return vignette(img, 0.35)


def set4_profile():
    img = night(PS, PS, PX, PY, 42, ribbons=[(PS * 0.70, PS * 0.50, PS * 0.05, 2.0, PS * 0.20, 0.45, 0.92, 0.9),
                                             (PS * 0.86, PS * 0.80, PS * 0.03, 3.0, PS * 0.10, 0.22, 0.3, 0.7)])
    img = constellation(img, LOGO.polys_px(PS / 2, PS / 2 + 10, 760), (PS, PS), 16, 5, 1.2)
    img = grain(img, 0.015, 1.0, 402)
    return vignette(img, 0.3)


# ================================================================================================
# bonus 5 - RAINBOW PAPER COLLAGE, 6 - NEON SIGN, 7 - BLUEPRINT
# ================================================================================================
def torn_strip(h, w, y0, height, seed, angle=0.0):
    r = np.random.default_rng(seed)
    xs = np.linspace(-100, w + 100, 160)
    top = y0 + np.cumsum(r.normal(0, 2.2, len(xs))) * 0.6 + r.normal(0, 1.5, len(xs))
    bot = y0 + height + np.cumsum(r.normal(0, 2.2, len(xs))) * 0.6 + r.normal(0, 1.5, len(xs))
    pts = np.concatenate([np.stack([xs, top], 1), np.stack([xs[::-1], bot[::-1]], 1)])
    M = cv2.getRotationMatrix2D((w / 2, y0 + height / 2), angle, 1.0)
    pts = (np.c_[pts, np.ones(len(pts))] @ M.T)
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.round(pts * 16).astype(np.int32)], 255, cv2.LINE_AA, 4)
    m = m.astype(np.float32) / 255
    edge = np.clip(m - cv2.erode(m, np.ones((7, 7), np.uint8)), 0, 1)
    return m, edge


def collage(h, w, xx, yy, seed):
    img = K.paper(h, w, rgb("#f6f1e7"), seed=seed, fibres=0.03, grain=0.03, mottle=0.05)
    cols = ["#ff3b5c", "#ff8a1f", "#ffd21f", "#2fd36b", "#1fa8ff", "#7a4dff", "#ff4fc4"]
    paper = K.paper(h, w, (1, 1, 1), seed=seed + 1, fibres=0.04, grain=0.04, mottle=0.06)[..., 0]
    n = len(cols)
    for k, c in enumerate(cols):
        y0 = -h * 0.1 + k * h * 1.2 / n
        m, edge = torn_strip(h, w, y0, h * 1.2 / n + 70, seed + k, angle=-8 + k * 0.6)
        sh = blur(cv2.warpAffine(m, np.float32([[1, 0, 8], [0, 1, 14]]), (w, h)), 10)
        img = img * (1 - 0.3 * sh[..., None])
        img = comp(img, m, rgb(c)[None, None] * (0.93 + 0.1 * (paper - 1) * 5)[..., None])
        img = comp(img, edge * 0.85, rgb("#fffaf0"))
    return img


def paper_piece(img, polys, shape, col, lift=14):
    m = mask(polys, shape)
    sh = blur(cv2.warpAffine(m, np.float32([[1, 0, lift * 0.6], [0, 1, lift]]), (shape[1], shape[0])), lift * 0.8)
    img = img * (1 - 0.4 * sh[..., None])
    edge = np.clip(cv2.dilate(m, np.ones((9, 9), np.uint8)) - m, 0, 1)
    img = comp(img, edge, rgb("#fffaf0"))
    return comp(img, m, col)


def set5_banner():
    img = collage(BH, BW, BX, BY, 51)
    x0, y0, x1, y1 = SAFE
    card = np.zeros((BH, BW), np.float32)
    cv2.rectangle(card, (x0 + 20, y0 + 10), (x1 - 20, y1 - 10), 1.0, -1)
    img = paper_piece(img, [np.array([[x0 + 20, y0 + 10], [x1 - 20, y0 + 10], [x1 - 20, y1 - 10], [x0 + 20, y1 - 10]], float)],
                      (BH, BW), rgb("#fbf7ee"), 18)
    polys, a, p, _ = hlockup(310, "luckiest-guy-400", "lilita-one-400", 120, 42, 0.12, gap=80)
    img = paper_piece(img, polys, (BH, BW), rgb("#1b1b24"), 10)
    for k, L in enumerate(a):
        img = paper_piece(img, L["polys"], (BH, BW), rgb(["#ff3b5c", "#ff8a1f", "#ffd21f", "#2fd36b", "#1fa8ff", "#7a4dff"][k]), 8)
    img = comp(img, letters_mask(p, (BH, BW)), rgb("#1b1b24"))
    return vignette(grain(img, 0.012, 1.0, 501), 0.25)


def set5_profile():
    img = collage(PS, PS, PX, PY, 52)
    r = np.hypot(PX - PS / 2, PY - PS / 2)
    img = paper_piece(img, [np.stack([PS / 2 + 600 * np.cos(np.linspace(0, 2 * math.pi, 120)),
                                      PS / 2 + 600 * np.sin(np.linspace(0, 2 * math.pi, 120))], 1)], (PS, PS), rgb("#fbf7ee"), 20)
    img = paper_piece(img, LOGO.polys_px(PS / 2, PS / 2 + 10, 700), (PS, PS), rgb("#1b1b24"), 12)
    return vignette(grain(img, 0.012, 1.0, 502), 0.2)


def brick(h, w, seed):
    img = np.zeros((h, w, 3), np.float32) + rgb("#120a10")
    r = np.random.default_rng(seed)
    bw, bh = 200, 80
    m = np.zeros((h, w), np.float32)
    for row in range(-1, h // bh + 2):
        off = (row % 2) * bw // 2
        for col in range(-1, w // bw + 2):
            x0, y0 = col * bw + off, row * bh
            cv2.rectangle(m, (x0 + 5, y0 + 5), (x0 + bw - 5, y0 + bh - 5), float(r.uniform(0.6, 1.0)), -1)
    m = blur(m, 1.5)
    return img + m[..., None] * rgb("#2a1620")


def neon(img, m, col, inset, half, glow_k=1.0):
    b = (m > 0.5).astype(np.uint8)
    sdf = cv2.distanceTransform(1 - b, cv2.DIST_L2, 5) - cv2.distanceTransform(b, cv2.DIST_L2, 5)
    tube = np.clip((half - np.abs(sdf + inset)) / 1.2 + 0.5, 0, 1)
    img = img + (blur(tube, 6) * 1.2 + blur(tube, 24) * 0.9 + blur(tube, 70) * 0.6)[..., None] * np.asarray(col) * 0.8 * glow_k
    core = tube[..., None] * (np.asarray(col) * 0.35 + 0.95)
    return img * (1 - tube[..., None]) + core * 1.2


def set6_banner():
    img = brick(BH, BW, 61)
    polys, a, p, _ = hlockup(320, "syncopate-700", "montserrat-500", 104, 34, 0.30, gap=90)
    img = neon(img, mask(polys, (BH, BW)), rgb("#ff2fa0"), 10, 5)
    img = neon(img, letters_mask(a, (BH, BW)), rgb("#28e7ff"), 4, 3.5)
    img = neon(img, letters_mask(p, (BH, BW)), rgb("#28e7ff"), 0, 1.8, 0.8)
    return vignette(grain(img, 0.02, 1.0, 601), 0.5)


def set6_profile():
    img = brick(PS, PS, 62)
    img = neon(img, mask(LOGO.polys_px(PS / 2, PS / 2 + 10, 720), (PS, PS)), rgb("#ff2fa0"), 14, 7, 1.2)
    return vignette(grain(img, 0.02, 1.0, 602), 0.5)


def blueprint_bg(h, w, xx, yy):
    img = np.zeros((h, w, 3), np.float32) + rgb("#0e3f8f")
    img *= (1.1 - 0.3 * np.hypot((xx - w / 2) / w, (yy - h / 2) / h))[..., None]
    g = np.zeros((h, w), np.float32)
    for x in range(0, w, 32):
        g[:, x:x + 1] = 0.12 if x % 160 else 0.28
    for y in range(0, h, 32):
        g[y:y + 1, :] = np.maximum(g[y:y + 1, :], 0.12 if y % 160 else 0.28)
    return comp(img, g, rgb("#d9e8ff"))


def blueprint_draw(img, polys, shape, lw=4, hatch=True):
    m = mask(polys, shape)
    ln = np.zeros(shape, np.uint8)
    for p in polys:
        cv2.polylines(ln, [np.round(p * 16).astype(np.int32)], True, 255, lw, cv2.LINE_AA, 4)
    ln = ln.astype(np.float32) / 255
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    if hatch:
        ln = np.maximum(ln, ((xx + yy) % 18 < 1.6).astype(np.float32) * m * 0.4)
    return comp(img, ln, rgb("#eef5ff"))


def set7_banner():
    img = blueprint_bg(BH, BW, BX, BY)
    polys, a, p, box = hlockup(320, "space-mono-700", "space-mono-400", 96, 34, 0.12, gap=90)
    img = blueprint_draw(img, polys, (BH, BW), 3)
    ln = np.zeros((BH, BW), np.float32)
    x0, y0, x1, y1 = box
    for (pa, pb) in (((x0, y1 + 50), (x1, y1 + 50)), ((x0 - 50, y0), (x0 - 50, y1))):
        cv2.line(ln, tuple(map(int, pa)), tuple(map(int, pb)), 0.8, 2, cv2.LINE_AA)
    img = comp(img, ln, rgb("#eef5ff"))
    img = comp(img, letters_mask(a, (BH, BW)), rgb("#ffffff"))
    img = comp(img, letters_mask(p, (BH, BW)), rgb("#cfe3ff"))
    return vignette(grain(img, 0.012, 1.0, 701), 0.3)


def set7_profile():
    img = blueprint_bg(PS, PS, PX, PY)
    img = blueprint_draw(img, LOGO.polys_px(PS / 2, PS / 2 + 10, 720), (PS, PS), 6)
    r = np.hypot(PX - PS / 2, PY - PS / 2)
    ring = np.clip((2.5 - np.abs(r - 640)) / 1.2, 0, 1)
    return vignette(comp(img, ring * 0.7, rgb("#eef5ff")), 0.25)


SETS = {1: ("retro-grainy", set1_banner, set1_profile), 2: ("retro-vhs", set2_banner, set2_profile),
        3: ("retro-70s", set3_banner, set3_profile), 4: ("surprise-constellation", set4_banner, set4_profile),
        5: ("bonus-rainbow-collage", set5_banner, set5_profile), 6: ("bonus-neon", set6_banner, set6_profile),
        7: ("bonus-blueprint", set7_banner, set7_profile)}


def run(which):
    import json
    (OUT / "banners").mkdir(parents=True, exist_ok=True)
    (OUT / "profiles").mkdir(parents=True, exist_ok=True)
    log = C.ROOT / "logs" / "safe_area.json"
    log.parent.mkdir(exist_ok=True)
    report = json.loads(log.read_text()) if log.exists() else {}
    for k in which:
        name, fb, fp = SETS[k]
        tag = f"{k}-{name}" if k <= 4 else f"{name}"
        EXTENTS.clear()
        b = fb()
        x0, y0 = min(e[0] for e in EXTENTS), min(e[1] for e in EXTENTS)
        x1, y1 = max(e[2] for e in EXTENTS), max(e[3] for e in EXTENTS)
        inside = x0 >= SAFE[0] and y0 >= SAFE[1] and x1 <= SAFE[2] and y1 <= SAFE[3]
        report[f"banner-{tag}"] = {"ink_box": [round(v, 1) for v in (x0, y0, x1, y1)], "safe": SAFE, "inside": inside,
                                   "margins_lrtb": [round(x0 - SAFE[0]), round(SAFE[2] - x1), round(y0 - SAFE[1]), round(SAFE[3] - y1)]}
        assert inside, f"banner {tag}: lockup {x0:.0f},{y0:.0f}-{x1:.0f},{y1:.0f} leaves the safe area {SAFE}"
        mb = save_png(b, OUT / "banners" / f"banner-{tag}.png")
        rec = []
        orig = LOGO.polys_px
        LOGO.polys_px = lambda *a, **kw: rec.append(orig(*a, **kw)) or rec[-1]
        try:
            p = fp()
        finally:
            del LOGO.polys_px
        pts = np.concatenate([q for polys in rec for q in polys])
        rmax = float(np.hypot(pts[:, 0] - PS / 2, pts[:, 1] - PS / 2).max())
        report[f"profile-{tag}"] = {"logo_max_radius_px": round(rmax, 1), "circle_radius_px": PS / 2,
                                    "inside_circle": rmax < PS / 2 * 0.92}
        assert rmax < PS / 2 * 0.92, f"profile {tag}: logo reaches r={rmax:.0f}, too close to the circle edge"
        log.write_text(json.dumps(report, indent=1))
        save_png(p, OUT / "profiles" / f"profile-{tag}-1600.png", 10)
        small = cv2.resize(np.clip(p, 0, 1), (800, 800), interpolation=cv2.INTER_AREA)
        save_png(small, OUT / "profiles" / f"profile-{tag}-800.png", 10)
        print(f"set {k} {name}: banner {mb:.2f} MB", flush=True)


if __name__ == "__main__":
    which = [int(a) for a in sys.argv[1:]] or list(SETS)
    run(which)
