"""
ASTRIS PRODUCTIONS - Intro 3: STYLE-SWITCHER (10.0 s)

The logo flips through ten complete art directions, fast to slow (2, 3, 4, 5, 6, 8, 10, 13, 17, 22
frames): flat pop yellow, 8-bit, neon, paper-cut, blueprint, leafy, cyan HUD, glass, gold, chrome.
Then a fully rainbow, flowing spectrum (28 frames) - and it LANDS on a clean luminous white logo.
The rainbow paint drains down and drips off the logo, the camera pulls out and ASTRIS PRODUCTIONS
arrives. Each switch has its own punchy tick (each with a little flavour of its style) and the pitch
climbs as the pace slows; the landing is a big hit with a chord, glossy drips and a shimmer.
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import common as C
import sound as S

cv2 = C.cv2
NAME = "astris-3-style-switcher"
DUR = 10.0
N = int(DUR * C.FPS)
W, H = C.W, C.H

SEQ = [("yellow", 2), ("pixel", 3), ("neon", 4), ("paper", 5), ("blueprint", 6), ("leafy", 8),
       ("hud", 10), ("glass", 13), ("gold", 17), ("chrome", 22), ("rainbow", 28)]
STARTS = np.cumsum([0] + [d for _, d in SEQ]).tolist()
LAND_F = STARTS[-1]                       # 118
T_LAND = LAND_F / C.FPS                   # 4.917 s
T_PULL0, T_PULL1 = 5.75, 7.70             # camera pull-out
T_ASTRIS, T_PROD = 7.00, 7.30
DRAIN = 1.90                              # seconds for the rainbow to drain off

LOGO = C.Logo()
LOCK = C.Lockup(LOGO)
POST = C.Post(seed=33, grain=0.022, vignette=0.30)

REF_H = 1450.0
REF_C = (W / 2, H / 2)
POLYS = LOGO.polys_px(REF_C[0], REF_C[1], REF_H)
MASK = C.poly_mask_ss(POLYS, ss=2)
BIN = (MASK > 0.5).astype(np.uint8)
DI = cv2.distanceTransform(BIN, cv2.DIST_L2, 5)
DO = cv2.distanceTransform(1 - BIN, cv2.DIST_L2, 5)
SDF = (DO - DI).astype(np.float32)        # negative inside the logo
_allp = np.concatenate(POLYS)
BX0, BY0 = (_allp.min(0) - 160).astype(int)
BX1, BY1 = (_allp.max(0) + 160).astype(int)
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
U = (XX - REF_C[0]) / REF_H              # logo-space coordinates
V = (YY - REF_C[1]) / REF_H
OUTER_IDX = [pc["outer"] for pc in LOGO.pieces]
HOLE_IDX = [j for pc in LOGO.pieces for j in pc["holes"]]
FONT_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Medium.ttf"


def rgb(h):
    return C.hexrgb(h)


def comp(img, mask, col):
    m = mask[..., None]
    return img * (1 - m) + np.asarray(col, np.float32) * m


def sdf_band(sdf, at, half, aa=1.0):
    """Anti-aliased band where |sdf - at| < half."""
    return np.clip((half - np.abs(sdf - at)) / aa + 0.5, 0, 1)


def grow(r):
    """Logo mask grown (r>0) or shrunk (r<0) by r pixels, with clean anti-aliased edges."""
    return np.clip((r - SDF) / 1.2 + 0.5, 0, 1)


def blur(m, s):
    return cv2.GaussianBlur(m, (0, 0), s)


def shift(m, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(m, M, (m.shape[1], m.shape[0]), flags=cv2.INTER_LINEAR, borderValue=0)


def text_mask(items, shape=(H, W)):
    """items: (x, y, text, size, anchor, font)  -> float mask."""
    im = Image.new("L", (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(im)
    for x, y, txt, size, anchor, font in items:
        f = ImageFont.truetype(font or FONT_MONO, size)
        d.text((x, y), txt, font=f, fill=255, anchor=anchor)
    return np.asarray(im, np.float32) / 255


def bevel(width, height):
    x = np.clip(DI / width, 0, 1)
    h = np.sqrt(np.clip(1 - (1 - x) ** 2, 0, 1)).astype(np.float32)
    h = cv2.GaussianBlur(h, (0, 0), 1.0)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8 * height
    gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8 * height
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def radial_bg(c_in, c_out, power=1.4, cx=W / 2, cy=H / 2):
    r = np.clip(np.hypot((XX - cx) / (W * 0.62), (YY - cy) / (H * 0.62)), 0, 1) ** power
    return (rgb(c_in) * (1 - r[..., None]) + rgb(c_out) * r[..., None]).astype(np.float32)


# ================================================================================================
# the ten styles (static bases at the reference framing; some get per-frame life on top)
# ================================================================================================
def style_yellow():
    img = np.zeros((H, W, 3), np.float32) + rgb("#1b37d6")
    # halftone dots growing toward the corners
    dots = np.zeros((H, W), np.float32)
    step = 54
    for y in range(step // 2, H, step):
        for x in range((y // step % 2) * step // 2, W, step):
            r = math.hypot((x - W / 2) / W, (y - H / 2) / H)
            rad = 3 + 15 * min(1, r * 1.6) ** 1.5
            cv2.circle(dots, (x * 4, y * 4), int(rad * 4), 1.0, -1, cv2.LINE_AA, 2)
    img = comp(img, dots * 0.55, rgb("#2b4cf0"))
    # long hard shadow down-right
    sh = np.zeros((H, W), np.float32)
    for k in range(0, 150, 3):
        np.maximum(sh, shift(MASK, k * 0.8, k), out=sh)
    img = comp(img, sh, rgb("#0b1a7a"))
    img = comp(img, MASK, rgb("#ffd21a"))
    # crisp inner highlight on top-left edges (screen-print feel)
    hl = np.clip(MASK - shift(MASK, 7, 7), 0, 1)
    img = comp(img, hl * 0.9, rgb("#fff1a0"))
    return img


def style_pixel():
    cell = 40
    gw, gh = W // cell, H // cell
    small = cv2.resize(MASK, (gw, gh), interpolation=cv2.INTER_AREA) > 0.45
    sm = small.astype(np.uint8)
    k3 = np.ones((3, 3), np.uint8)
    outline = cv2.dilate(sm, k3) - sm
    shadow = np.roll(np.roll(cv2.dilate(sm, k3), 1, 0), 1, 1) * (1 - sm) * (1 - outline)
    top_edge = sm * (1 - np.roll(sm, 1, 0))           # cells whose upper neighbour is empty
    left_edge = sm * (1 - np.roll(sm, 1, 1))
    low_edge = sm * (1 - np.roll(sm, -1, 0))
    # night sky in four dithered bands + pixel stars
    yy = np.arange(gh)[:, None] / gh
    bands = [rgb("#0d0b2b"), rgb("#1b1450"), rgb("#33206e"), rgb("#5a2a7c")]
    level = yy * 3.999 + ((np.arange(gw)[None, :] + np.arange(gh)[:, None]) % 2) * 0.35
    idx = np.clip(level.astype(int), 0, 3)
    sky = np.stack([np.choose(idx, [b[c] for b in bands]) for c in range(3)], -1).astype(np.float32)
    r = np.random.default_rng(3)
    for _ in range(140):
        x, y = r.integers(0, gw), r.integers(0, int(gh * 0.75))
        sky[y, x] = rgb("#fff6c2") if r.uniform() < 0.3 else rgb("#9fb7ff")
    img = sky.copy()
    img[shadow > 0] = rgb("#140a30")
    img[outline > 0] = rgb("#05030f")
    img[sm > 0] = rgb("#e9ecff")
    img[(top_edge + left_edge) > 0] = rgb("#ffffff")
    img[(low_edge > 0) & (top_edge == 0)] = rgb("#9aa7e6")
    # chunky upscale + CRT scanlines and a soft aperture mask
    big = cv2.resize(img, (gw * cell, gh * cell), interpolation=cv2.INTER_NEAREST)
    big = cv2.copyMakeBorder(big, 0, H - gh * cell, 0, W - gw * cell, cv2.BORDER_REPLICATE)
    scan = (0.84 + 0.16 * (np.arange(H) % 8 < 5))[:, None, None].astype(np.float32)
    return big * scan


def style_neon():
    # dark brick wall
    wall = np.zeros((H, W), np.float32)
    bw, bh = 260, 110
    r = np.random.default_rng(5)
    for row in range(-1, H // bh + 2):
        off = (row % 2) * bw // 2
        for col in range(-1, W // bw + 2):
            x0, y0 = col * bw + off, row * bh
            cv2.rectangle(wall, (x0 + 6, y0 + 6), (x0 + bw - 6, y0 + bh - 6), float(r.uniform(0.75, 1.0)), -1)
    wall = blur(wall, 2.0)
    n = blur(np.random.default_rng(6).standard_normal((H // 4, W // 4)).astype(np.float32), 1.0)
    wall = wall * (0.85 + 0.15 * cv2.resize(n, (W, H)))
    img = wall[..., None] * rgb("#1a0f1c") + rgb("#07040a")
    # tubes: outer outline inset, and small loops around each sprocket hole
    outer = C.poly_mask([POLYS[i] for i in OUTER_IDX])
    ob = (outer > 0.5).astype(np.uint8)
    sdf_o = cv2.distanceTransform(1 - ob, cv2.DIST_L2, 5) - cv2.distanceTransform(ob, cv2.DIST_L2, 5)
    tube = sdf_band(sdf_o, -26, 7.5, 1.5)
    if HOLE_IDX:
        holes = C.poly_mask([POLYS[j] for j in HOLE_IDX])
        hb = (holes > 0.5).astype(np.uint8)
        sdf_h = cv2.distanceTransform(1 - hb, cv2.DIST_L2, 5)
        tube = np.maximum(tube, sdf_band(sdf_h, 9, 5.0, 1.5) * (MASK > 0.5))
    # colour by piece: pink film, cyan bar
    film = C.poly_mask(LOGO.polys_px(REF_C[0], REF_C[1], REF_H, pieces=list(range(len(LOGO.pieces) - 1))))
    filmz = blur(np.clip(film * 3, 0, 1), 30)
    pink, cyan = rgb("#ff2fa0"), rgb("#28e7ff")
    col = pink * filmz[..., None] + cyan * (1 - filmz[..., None])
    wide = cv2.resize(blur(cv2.resize(tube, (W // 4, H // 4), interpolation=cv2.INTER_AREA), 45), (W, H))
    img = img + col * (blur(tube, 12) * 1.4 + blur(tube, 45) * 1.1 + wide * 2.2)[..., None] * 0.55
    core = tube[..., None] * (col * 0.35 + 0.95)
    img = img * (1 - tube[..., None]) + core * 1.25
    # the dark unlit glass of the sign face
    img = comp(img, MASK * 0.18 * (1 - tube), rgb("#000000"))
    return img


def paper_tex(seed, strength=0.05):
    r = np.random.default_rng(seed)
    n = r.standard_normal((H // 2, W // 2)).astype(np.float32)
    fib = cv2.GaussianBlur(n, (0, 0), sigmaX=6, sigmaY=0.8)
    fine = cv2.GaussianBlur(n, (0, 0), 0.7)
    t = cv2.resize(fib * 0.6 + fine * 0.4, (W, H))
    return 1 + strength * t / (np.std(t) + 1e-6)


def style_paper():
    img = np.zeros((H, W, 3), np.float32) + rgb("#e7d9c4")
    img *= paper_tex(1, 0.045)[..., None]
    layers = [(grow(88), rgb("#e4613f"), 2), (grow(44), rgb("#f2b23c"), 3), (MASK, rgb("#fff7ea"), 4)]
    for m, col, seed in layers:
        sh = blur(shift(m, 10, 16), 14)
        img = img * (1 - 0.38 * sh[..., None])
        tint = col * paper_tex(seed, 0.035)[..., None]
        img = comp(img, m, tint)
        # lit top edge of each paper layer
        edge = np.clip(m - shift(m, 0, 4), 0, 1)
        img = img + edge[..., None] * 0.10
    return img


def style_blueprint():
    img = radial_bg("#1452b0", "#0a3277", 1.2)
    grid = np.zeros((H, W), np.float32)
    for x in range(0, W, 40):
        grid[:, x:x + 2] = 0.10 if x % 200 else 0.26
    for y in range(0, H, 40):
        grid[y:y + 2, :] = np.maximum(grid[y:y + 2, :], 0.10 if y % 200 else 0.26)
    ink = rgb("#e6f1ff")
    img = comp(img, grid, ink)
    lines = np.zeros((H, W), np.float32)
    # hatching inside the logo
    hatch = ((XX + YY) % 26 < 2.2).astype(np.float32)
    lines = np.maximum(lines, hatch * MASK * 0.35)
    # outlines
    for p in POLYS:
        cv2.polylines(lines, [np.round(p * 16).astype(np.int32)], True, 1.0, 5, cv2.LINE_AA, 4)
    # construction lines: extend the long edges, dashed
    con = np.zeros((H, W), np.float32)
    for p in [POLYS[i] for i in OUTER_IDX]:
        for a, b in zip(p, np.roll(p, -1, 0)):
            d = b - a
            L = np.linalg.norm(d)
            if L < 400:
                continue
            d /= L
            for s0 in np.arange(-1600, L + 1600, 46):
                if 0 <= s0 <= L:
                    continue
                q0, q1 = a + d * s0, a + d * (s0 + 24)
                cv2.line(con, tuple(np.round(q0 * 16).astype(int)), tuple(np.round(q1 * 16).astype(int)), 0.5, 2,
                         cv2.LINE_AA, 4)
    # dimension lines with arrowheads + numbers
    x0, y0 = _allp.min(0)
    x1, y1 = _allp.max(0)
    dim = np.zeros((H, W), np.float32)

    def arrow_line(p, q):
        cv2.line(dim, tuple(map(int, p)), tuple(map(int, q)), 0.85, 3, cv2.LINE_AA)
        for a, b in ((p, q), (q, p)):
            d = (np.array(b) - np.array(a)) / np.linalg.norm(np.array(b) - np.array(a))
            nrm = np.array([-d[1], d[0]])
            tip = np.array(a)
            tri = np.array([tip, tip + d * 34 + nrm * 11, tip + d * 34 - nrm * 11])
            cv2.fillPoly(dim, [np.round(tri).astype(np.int32)], 0.85, cv2.LINE_AA)

    arrow_line((x0, y1 + 110), (x1, y1 + 110))
    arrow_line((x0 - 130, y0), (x0 - 130, y1))
    for xx in (x0, x1):
        cv2.line(dim, (int(xx), int(y1 + 30)), (int(xx), int(y1 + 140)), 0.6, 2, cv2.LINE_AA)
    for yy in (y0, y1):
        cv2.line(dim, (int(x0 - 160), int(yy)), (int(x0 - 40), int(yy)), 0.6, 2, cv2.LINE_AA)
    cv2.circle(dim, (int(REF_C[0]), int(REF_C[1])), 22, 0.7, 2, cv2.LINE_AA)
    cv2.line(dim, (int(REF_C[0]) - 46, int(REF_C[1])), (int(REF_C[0]) + 46, int(REF_C[1])), 0.7, 2, cv2.LINE_AA)
    cv2.line(dim, (int(REF_C[0]), int(REF_C[1]) - 46), (int(REF_C[0]), int(REF_C[1]) + 46), 0.7, 2, cv2.LINE_AA)
    txt = text_mask([((x0 + x1) / 2, y1 + 92, "1316", 46, "ms", None),
                     (x0 - 150, (y0 + y1) / 2, "1108", 46, "rm", None),
                     (W - 150, H - 120, "A-01   1:1", 40, "rs", None),
                     ((x1 + 80), y0 + 40, "63.4°", 40, "ls", None)])
    # title block frame
    cv2.rectangle(dim, (W - 760, H - 210), (W - 110, H - 80), 0.7, 3, cv2.LINE_AA)
    cv2.rectangle(dim, (110, 110), (W - 110, H - 80), 0.45, 3, cv2.LINE_AA)
    img = comp(img, np.clip(con + dim + txt * 0.95, 0, 1), ink)
    img = comp(img, lines, ink)
    return img


def leaf_shapes(cx, cy, L, Wd, ang, bend, n=14):
    """A gently curved leaf: (outline, lit half, vein) in pixels."""
    s = np.linspace(0, 1, n)
    w = Wd * np.sin(np.pi * s) ** 0.85
    xs = (s - 0.5) * L
    yc = bend * L * ((s - 0.5) ** 2 - 0.25)
    left = np.stack([xs, yc - w / 2], 1)
    right = np.stack([xs[::-1], (yc + w / 2)[::-1]], 1)
    centre = np.stack([xs[::-1], yc[::-1]], 1)
    c, si = math.cos(ang), math.sin(ang)
    R = np.array([[c, -si], [si, c]])
    tr = lambda a: a @ R.T + [cx, cy]
    return tr(np.concatenate([left, right])), tr(np.concatenate([left, centre])), tr(np.stack([xs, yc], 1))


def style_leafy():
    r = np.random.default_rng(8)
    img = radial_bg("#174a2a", "#06180d", 1.2)
    # soft out-of-focus foliage behind
    bok = np.zeros((H // 4, W // 4, 3), np.float32)
    for _ in range(70):
        x, y = r.uniform(0, W // 4), r.uniform(0, H // 4)
        rad = r.uniform(20, 90)
        col = rgb(r.choice(["#2f7d3a", "#4f9d3f", "#1d5e2e", "#9cc95c"])) * r.uniform(0.25, 0.6)
        cv2.circle(bok, (int(x), int(y)), int(rad), tuple(float(c) for c in col), -1, cv2.LINE_AA)
    img = img + cv2.resize(blur(bok, 14), (W, H)) * 0.55
    leaves = np.zeros((H, W, 3), np.float32)
    cover = np.zeros((H, W), np.float32)
    greens = [rgb(h) for h in ("#1f6b2c", "#2e8b3a", "#3fa046", "#5cb85c", "#7cc35a", "#a5d46a", "#16521f")]
    inside = np.argwhere(DI > 6)
    edge = np.argwhere((DI > 0) & (DI <= 8))
    pts = np.concatenate([inside[r.integers(0, len(inside), 1700)], edge[r.integers(0, len(edge), 260)]])
    r.shuffle(pts)
    for (y, x) in pts:
        L = r.uniform(60, 125)
        ang = r.uniform(0, 2 * math.pi)
        # leaves near the edge point outward, like they're growing out of the shape
        if DI[y, x] <= 8:
            gy, gx = SDF[min(H - 1, y + 3), x] - SDF[max(0, y - 3), x], SDF[y, min(W - 1, x + 3)] - SDF[y, max(0, x - 3)]
            ang = math.atan2(gy, gx) + r.normal(0, 0.4)
            x, y = x + math.cos(ang) * L * 0.12, y + math.sin(ang) * L * 0.12
        outline, lit, vein = leaf_shapes(x, y, L, L * r.uniform(0.36, 0.5), ang, r.uniform(-0.25, 0.25))
        base = greens[r.integers(0, len(greens))] * r.uniform(0.85, 1.1)
        pi = np.round(outline * 16).astype(np.int32)
        cv2.fillPoly(leaves, [pi], tuple(float(c) for c in base * 0.72), cv2.LINE_AA, 4)
        cv2.fillPoly(leaves, [np.round(lit * 16).astype(np.int32)], tuple(float(c) for c in base * 1.08), cv2.LINE_AA, 4)
        cv2.polylines(leaves, [np.round(vein * 16).astype(np.int32)], False, tuple(float(c) for c in base * 1.4), 2,
                      cv2.LINE_AA, 4)
        cv2.fillPoly(cover, [pi], 1.0, cv2.LINE_AA, 4)
    # keep the sprocket holes open
    keep = grow(20)                                   # a little organic overhang, real silhouette kept
    if HOLE_IDX:
        holes = C.poly_mask([POLYS[j] for j in HOLE_IDX])
        keep = keep * (1 - holes)
    cover *= keep
    leaves *= keep[..., None]
    shadow = blur(shift(cover, 14, 22), 16)
    img = img * (1 - 0.55 * shadow[..., None])
    img = img * (1 - cover[..., None]) + leaves
    return img


def style_hud_base():
    img = radial_bg("#04202b", "#010509", 1.0)
    cyan = rgb("#3ff3ff")
    lines = np.zeros((H, W), np.float32)
    # perspective floor grid
    hz = int(H * 0.70)
    for k in range(-30, 31):
        x_far = W / 2 + k * 60
        x_near = W / 2 + k * 600
        cv2.line(lines, (int(x_far), hz), (int(x_near), H + 400), 0.18, 2, cv2.LINE_AA)
    for k in range(1, 18):
        y = hz + (H - hz) * (k / 17) ** 2.2
        cv2.line(lines, (0, int(y)), (W, int(y)), 0.18, 2, cv2.LINE_AA)
    # corner brackets
    for (x, y, sx, sy) in ((420, 260, 1, 1), (W - 420, 260, -1, 1), (420, H - 260, 1, -1), (W - 420, H - 260, -1, -1)):
        cv2.line(lines, (x, y), (x + sx * 160, y), 0.9, 4, cv2.LINE_AA)
        cv2.line(lines, (x, y), (x, y + sy * 160), 0.9, 4, cv2.LINE_AA)
    # logo: translucent fill + scanlines + edges
    scan = ((YY % 12) < 3).astype(np.float32)
    fill = MASK * (0.10 + 0.32 * scan)
    edge = np.zeros((H, W), np.float32)
    for p in POLYS:
        cv2.polylines(edge, [np.round(p * 16).astype(np.int32)], True, 1.0, 4, cv2.LINE_AA, 4)
    txt = text_mask([(470, 330, "ASTRIS // 7.4", 44, "la", None), (470, 390, "0x7F3A  0x11C0", 34, "la", None),
                     (W - 470, 330, "51.5072 N", 34, "ra", None), (W - 470, 380, "0.1276 W", 34, "ra", None),
                     (470, H - 330, "0024 / 0240", 34, "ls", None), (W - 470, H - 330, "▸ 100%", 34, "rs", None)])
    img = img + cyan * (lines * 0.6 + fill * 0.55 + edge * 1.25 + txt * 0.9)[..., None]
    glow = blur(edge, 8) * 0.8 + blur(edge, 30) * 0.5
    img = img + cyan * glow[..., None] * 0.6
    return img


def hud_live(img, tl):
    """Rotating segmented rings, sweeping scan bar, ticking numbers."""
    cyan = rgb("#3ff3ff")
    ov = np.zeros((H, W), np.float32)
    cx, cy = int(REF_C[0]), int(REF_C[1])
    for k, (R, segs, spd, thick, a) in enumerate(((930, 6, 40, 6, 0.8), (990, 36, -25, 3, 0.5), (1050, 3, 15, 10, 0.35))):
        for s in range(segs):
            a0 = s * 360 / segs + spd * tl * 6
            cv2.ellipse(ov, (cx, cy), (R, int(R * 0.98)), 0, a0, a0 + 360 / segs * 0.6, a, thick, cv2.LINE_AA)
    for k in range(120):
        a = math.radians(k * 3 + 10 * tl)
        r0, r1 = 1100, 1100 + (30 if k % 10 == 0 else 14)
        cv2.line(ov, (int(cx + r0 * math.cos(a)), int(cy + r0 * math.sin(a))),
                 (int(cx + r1 * math.cos(a)), int(cy + r1 * math.sin(a))), 0.5, 2, cv2.LINE_AA)
    sweep = (BY0 + (BY1 - BY0) * ((tl * 2.2) % 1.0))
    bar = np.exp(-((YY - sweep) / 18) ** 2) * (MASK * 0.9 + 0.08)
    num = text_mask([(W - 470, H - 400, f"{(tl * 997.3) % 1000:07.2f}", 40, "rs", None)])
    img = img + cyan * (ov + bar + num * 0.8)[..., None] * 0.9
    return img


def glass_bg():
    r = np.random.default_rng(12)
    bg = radial_bg("#2a1747", "#0b0616", 1.1)
    bok = np.zeros((H // 4, W // 4, 3), np.float32)
    cols = ["#ff4f9a", "#ff9b3d", "#3dc6ff", "#7a5cff", "#36e0b0", "#ffd84d"]
    for _ in range(46):
        x, y = r.uniform(0, W // 4), r.uniform(0, H // 4)
        rad = r.uniform(18, 75)
        col = rgb(cols[r.integers(0, len(cols))]) * r.uniform(0.35, 0.9)
        cv2.circle(bok, (int(x), int(y)), int(rad), tuple(float(c) for c in col), -1, cv2.LINE_AA)
    return bg + cv2.resize(blur(bok, 6), (W, H)) * 0.9


GLASS_N = None


def style_glass_base():
    global GLASS_N
    bg = glass_bg()
    n = bevel(64, 70)
    GLASS_N = n
    k = 150.0
    mx = XX - n[..., 0] * k - (XX - REF_C[0]) * 0.13 * MASK
    my = YY - n[..., 1] * k - (YY - REF_C[1]) * 0.13 * MASK
    refr = cv2.remap(blur(bg, 7.0), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    fres = np.clip(1 - n[..., 2], 0, 1) ** 1.1
    sheen = np.clip(0.5 - V * 0.9 - U * 0.3, 0, 1) ** 2 * 0.16
    glass = refr * np.array([0.95, 1.0, 1.08], np.float32) * 1.05 + 0.075 + (fres * 1.25 + sheen)[..., None]
    shadow = blur(shift(MASK, 18, 30), 24)
    img = bg * (1 - 0.35 * shadow[..., None])
    img = img * (1 - MASK[..., None]) + glass * MASK[..., None]
    rim = sdf_band(SDF, -1.5, 1.6, 1.0)
    img = img + rim[..., None] * 0.55
    return img


def glass_live(img, tl, dur):
    pos = -0.7 + 1.9 * tl / dur
    band = np.exp(-(((U * 0.9 + V * 0.45) - pos) / 0.05) ** 2) * MASK * 0.75
    band2 = np.exp(-(((U * 0.9 + V * 0.45) - pos - 0.14) / 0.015) ** 2) * MASK * 0.5
    return img + (band + band2)[..., None]


def metal(n, ramp, face_bend, light_pos):
    """Environment-mapped metal from a normal map: ramp is a list of (pos, hex) on the reflected y."""
    ry = 2 * n[..., 2] * n[..., 1] + V * face_bend
    rx = 2 * n[..., 2] * n[..., 0] + U * face_bend * 0.4
    u = np.clip(0.5 + 0.5 * (ry * 0.85 + rx * 0.25), 0, 1)
    keys = np.array([p for p, _ in ramp], np.float32)
    cols = np.array([rgb(h) for _, h in ramp], np.float32)
    env = np.stack([np.interp(u, keys, cols[:, c]) for c in range(3)], -1).astype(np.float32)
    L = np.array(light_pos, np.float32)
    L = L / np.linalg.norm(L)
    hv = L + np.array([0, 0, 1], np.float32)
    hv /= np.linalg.norm(hv)
    spec = np.clip((n * hv).sum(-1), 0, 1) ** 60
    return env + spec[..., None] * 1.2


def style_gold_base():
    bg = radial_bg("#2a1a08", "#050302", 1.1, cy=H * 0.45)
    n = bevel(46, 70)
    gold = metal(n, [(0.0, "#2a1703"), (0.28, "#7a4b0e"), (0.45, "#c9922c"), (0.56, "#ffe39a"),
                     (0.62, "#d9a23a"), (0.8, "#6b3f0b"), (1.0, "#f7d27a")], 0.9, (-0.4, -0.8, 0.6))
    brushed = 1 + 0.035 * cv2.resize(cv2.GaussianBlur(np.random.default_rng(4).standard_normal((H // 2, W // 2)).astype(np.float32), (0, 0), sigmaX=12, sigmaY=0.6), (W, H))
    gold *= brushed[..., None]
    shadow = blur(shift(MASK, 0, 34), 30)
    img = bg * (1 - 0.6 * shadow[..., None])
    return img * (1 - MASK[..., None]) + gold * MASK[..., None]


def metal_sweep(img, tl, dur, tint, width=0.06, strength=0.9):
    pos = -0.8 + 2.1 * C.expo_in_out(tl / dur, 3)
    band = np.exp(-(((U * 0.8 - V * 0.5) - pos) / width) ** 2) * MASK * strength
    return img + band[..., None] * np.asarray(tint, np.float32)


def glints(img, tl, seed, col, n=5):
    r = np.random.default_rng(seed)
    pts = np.argwhere((DI > 1) & (DI < 6))
    sel = pts[r.integers(0, len(pts), n)]
    ov = np.zeros((H // 2, W // 2), np.float32)
    for k, (y, x) in enumerate(sel):
        f = max(0.0, math.sin(tl * 7 + k * 1.9)) ** 3
        if f < 0.02:
            continue
        L = 70 * f + 10
        for a in (0, math.pi / 2, math.pi / 4, 3 * math.pi / 4):
            ll = L if a in (0, math.pi / 2) else L * 0.45
            dx, dy = math.cos(a) * ll / 2, math.sin(a) * ll / 2
            cv2.line(ov, (int((x - dx) / 2), int((y - dy) / 2)), (int((x + dx) / 2), int((y + dy) / 2)), f, 1, cv2.LINE_AA)
    ov = cv2.resize(blur(ov, 1.0), (W, H))
    return img + ov[..., None] * np.asarray(col, np.float32) * 2.0


def style_chrome_base():
    bg = radial_bg("#2a3341", "#07090c", 1.1, cy=H * 0.42)
    n = bevel(44, 80)
    chrome = metal(n, [(0.0, "#1b1208"), (0.30, "#4a3420"), (0.44, "#a58a6a"), (0.47, "#f4f1ea"),
                       (0.49, "#1c2330"), (0.58, "#3d5f8a"), (0.75, "#8db8e6"), (0.9, "#e6f2ff"), (1.0, "#ffffff")],
                   1.1, (-0.3, -0.9, 0.5))
    floor = np.clip((YY - (REF_C[1] + REF_H / 2 + 30)) / 500, 0, 1)
    mirror = cv2.flip(MASK, 0)
    dy = int(2 * (REF_C[1] + REF_H / 2) - H + 40)
    mirror = shift(mirror, 0, dy)
    img = bg + (mirror * (1 - floor) * 0.12 * (YY > REF_C[1] + REF_H / 2))[..., None] * rgb("#9fc0e6")
    return img * (1 - MASK[..., None]) + chrome * MASK[..., None]


def rainbow(img, tl):
    x0, y0, x1, y1 = max(0, BX0), max(0, BY0), min(W, BX1), min(H, BY1)
    u, v = U[y0:y1, x0:x1], V[y0:y1, x0:x1]
    m = MASK[y0:y1, x0:x1]
    ph = u * 0.75 + v * 0.35 - tl * 0.55 + 0.05 * np.sin(v * 9 + tl * 2.4) + 0.04 * np.sin(u * 13 - tl * 1.7)
    col = C.hue_wheel(ph) * 0.93
    sheen = 0.92 + 0.08 * np.sin((u - v) * 24 - tl * 6)
    roi = img[y0:y1, x0:x1]
    layer = col * sheen[..., None] * m[..., None]
    roi[:] = roi * (1 - m[..., None]) + layer
    # coloured halo: the spectrum lights the darkness around it (full frame, so it never shows a box)
    full = np.zeros((H // 4, W // 4, 3), np.float32)
    full[y0 // 4:y0 // 4 + (y1 - y0) // 4, x0 // 4:x0 // 4 + (x1 - x0) // 4] = cv2.resize(
        layer, ((x1 - x0) // 4, (y1 - y0) // 4), interpolation=cv2.INTER_AREA)
    halo = cv2.GaussianBlur(full, (0, 0), 14) * 0.9 + cv2.GaussianBlur(full, (0, 0), 40) * 0.6
    img += C.up(halo) * (1 - MASK[..., None] * 0.85)
    return img


STYLE_FUNCS = {"yellow": style_yellow, "pixel": style_pixel, "neon": style_neon, "paper": style_paper,
               "blueprint": style_blueprint, "leafy": style_leafy, "hud": style_hud_base, "glass": style_glass_base,
               "gold": style_gold_base, "chrome": style_chrome_base}
BLOOM = {"yellow": (0.18, 0.9), "pixel": (0.2, 0.9), "neon": (0.9, 0.55), "paper": (0.12, 0.95), "blueprint": (0.25, 0.85),
         "leafy": (0.2, 0.85), "hud": (0.7, 0.55), "glass": (0.45, 0.7), "gold": (0.55, 0.7), "chrome": (0.5, 0.75),
         "rainbow": (0.35, 0.8)}
BASES = {}


def build_bases(names=None):
    for nm in (names or STYLE_FUNCS):
        if nm not in BASES:
            BASES[nm] = STYLE_FUNCS[nm]().astype(np.float16)


# ================================================================================================
# the landing: white logo, rainbow paint draining and dripping, camera pull-out
# ================================================================================================
def camera(t):
    """Maps lockup space to the screen: returns (Z, off) usable with LOCK.logo_xy / word_mask."""
    P0 = np.array(LOCK.logo_xy(1.0)[:2])
    Z0, Q0 = REF_H / LOCK.LOGO_H, np.array(REF_C)
    Z1, Q1 = 1.0, P0
    e = C.expo_in_out((t - T_PULL0) / (T_PULL1 - T_PULL0), 6)
    Z = math.exp(math.log(Z0) + (math.log(Z1) - math.log(Z0)) * e)
    Q = Q0 + (Q1 - Q0) * e
    Z *= 1.0 + 0.025 * C.smoothstep(T_PULL1, DUR, t)
    off = Q - LOCK.anchor - Z * (P0 - LOCK.anchor)
    return Z, off


def drain_front(uu, tau):
    """Paint is present below this line (logo-space v, -0.5 = top, +0.5 = bottom)."""
    d = (tau / DRAIN) ** 1.5 * 1.15 + 0.30 * C.expo_out(tau / 0.14, 4)
    return -0.56 + d + 0.035 * np.sin(uu * 17 + 1.3) + 0.022 * np.sin(uu * 43 + tau * 2.0) + 0.012 * np.sin(uu * 91)


_dr = np.random.default_rng(21)


def _drip_sources():
    src = []
    for pc in LOGO.pieces:
        p = LOGO.polys[pc["outer"]]
        for a, b in zip(p, np.roll(p, -1, 0)):
            d = b - a
            L = np.linalg.norm(d)
            if L < 0.05:
                continue
            nrm = np.array([d[1], -d[0]]) / L
            if cv2.pointPolygonTest(p.astype(np.float32), tuple(map(float, (a + b) / 2 + nrm * 0.01)), False) > 0:
                nrm = -nrm
            if nrm[1] > 0.8:                   # downward-facing edge: paint drips from here
                k = max(2, int(L / 0.05))
                for s in np.sort(_dr.uniform(0.06, 0.94, k)):
                    src.append(a + d * s)
    return np.array(src)


DRIPS = _drip_sources()
ND = len(DRIPS)
DRIP_T0 = _dr.uniform(0.15, 1.1, ND)
DRIP_G = _dr.uniform(0.25, 0.65, ND)          # logo heights per s^2
DRIP_W = _dr.uniform(0.016, 0.032, ND)


def paint_colour(uu, vv, t):
    # continues the exact flow of the rainbow style so the hand-off is seamless
    return C.hue_wheel(uu * 0.75 + vv * 0.35 - (t - STARTS[-2] / C.FPS) * 0.55)


def landing(t, i):
    tau = t - T_LAND
    Z, off = camera(t)
    cx, cy, h = LOCK.logo_xy(Z, off)
    img = np.zeros((H, W, 3), np.float32) + rgb("#020203")
    polys = LOCK.logo_polys(Z, off)
    m = C.poly_mask_ss(polys, ss=2)
    allp = np.concatenate(polys)
    x0, y0 = np.maximum((allp.min(0) - 40).astype(int), 0)
    x1, y1 = np.minimum((allp.max(0) + 40).astype(int), [W, H])
    uu = (XX[y0:y1, x0:x1] - cx) / h
    vv = (YY[y0:y1, x0:x1] - cy) / h
    mm = m[y0:y1, x0:x1]
    white = np.array([0.97, 0.975, 1.0], np.float32) * (1.0 + 0.6 * math.exp(-max(tau, 0) / 0.18))
    roi = img[y0:y1, x0:x1]
    roi[:] = roi * (1 - mm[..., None]) + white * mm[..., None]
    # rainbow paint still on the logo, below the draining front
    paint = np.zeros((H, W), np.float32)
    pcol = np.zeros((H, W, 3), np.float32)
    if tau < DRAIN + 0.3:
        f = drain_front(uu, tau)
        cover = np.clip((vv - f) * h / 2.0 + 0.5, 0, 1) * mm
        col = paint_colour(uu, vv, t) * 1.05
        meniscus = np.exp(-(((vv - f) * h) / 5.0) ** 2) * mm * 0.65
        paint[y0:y1, x0:x1] = cover
        pcol[y0:y1, x0:x1] = col * 0.9 * cover[..., None] + meniscus[..., None]
    # drips: grow from the bottom edges, then let go and fall
    supply_end = DRAIN * 0.72
    for k in range(ND):
        tk = tau - DRIP_T0[k]
        if tk <= 0:
            continue
        sx, sy = cx + DRIPS[k][0] * h, cy + DRIPS[k][1] * h
        g = DRIP_G[k] * h
        if tau < supply_end:
            top, bot = sy, sy + 0.5 * g * tk ** 2 + 6
        else:
            tr = tau - supply_end                  # let go: the drop falls freely
            gf = 5.0 * h
            top = sy + 0.5 * gf * tr ** 2
            bot = sy + 0.5 * g * (supply_end - DRIP_T0[k]) ** 2 + 6 + 0.5 * gf * tr ** 2 + 0.4 * g * tr
        if top > H + 200:
            continue
        wd = DRIP_W[k] * h * (1.0 if tau < supply_end else max(0.35, 1 - (tau - supply_end) * 0.6))
        hue = C.hue_wheel(np.array([DRIPS[k][0] * 0.75 + DRIPS[k][1] * 0.35 - (tau + 1.17) * 0.55]))[0]
        L = bot - top
        ys = np.linspace(0, 1, 18)
        # thick where it leaves the edge (with a little fillet), thinning, then a round drop
        ww = wd * (0.62 + 0.38 * (1 - ys) ** 2 + 0.9 * np.exp(-ys * L / (wd * 0.9)) * (tau < supply_end))
        left = np.stack([sx - ww / 2, top + ys * L], 1)
        right = np.stack([sx + ww[::-1] / 2, top + ys[::-1] * L], 1)
        poly = np.round(np.concatenate([left, right]) * 16).astype(np.int32)
        cv2.fillPoly(paint, [poly], 1.0, cv2.LINE_AA, 4)
        cv2.fillPoly(pcol, [poly], tuple(float(c) for c in hue * 1.05), cv2.LINE_AA, 4)
        rad = wd * 0.85
        cv2.circle(paint, (int(sx * 16), int(bot * 16)), int(rad * 16), 1.0, -1, cv2.LINE_AA, 4)
        cv2.circle(pcol, (int(sx * 16), int(bot * 16)), int(rad * 16), tuple(float(c) for c in hue * 1.05), -1, cv2.LINE_AA, 4)
        # glossy highlight on each drip
        cv2.line(pcol, (int((sx - wd * 0.2) * 16), int((top + L * 0.3) * 16)), (int((sx - wd * 0.2) * 16), int((bot - rad * 0.3) * 16)),
                 (0.9, 0.9, 0.9), max(1, int(wd * 0.12)), cv2.LINE_AA, 4)
    img = img * (1 - paint[..., None]) + pcol
    # landing flash ring
    if 0 <= tau < 0.6:
        rr = np.hypot(XX[::4, ::4] - cx, YY[::4, ::4] - cy)
        R = h * 0.6 + 2600 * (1 - math.exp(-tau / 0.25))
        ring = np.exp(-((rr - R) / (20 + 300 * tau)) ** 2) * 0.5 * math.exp(-tau / 0.25)
        img += C.up(ring)[..., None] * np.array([0.9, 0.95, 1.0], np.float32)
    # type
    if t >= T_ASTRIS:
        a = [C.expo_out((t - T_ASTRIS - k * 0.05) / 0.5, 5) for k in range(6)]
        ma = LOCK.word_mask("astris", Z, off, alpha=a, track_mul=1 + 0.25 * (1 - C.expo_out((t - T_ASTRIS) / 1.0, 5)),
                            letter_dy=[30 * (1 - v) for v in a])
        img = comp(img, ma, [0.95, 0.96, 1.0])
    if t >= T_PROD:
        p = [C.expo_out((t - T_PROD - k * 0.03) / 0.5, 5) for k in range(11)]
        mp = LOCK.word_mask("prod", Z, off, alpha=p, track_mul=1 + 0.15 * (1 - C.expo_out((t - T_PROD) / 0.9, 5)))
        img = comp(img, mp, [0.80, 0.83, 0.9])
    # a slow shimmer glint across the lockup once it holds
    if 8.0 <= t <= 8.9:
        g = (t - 8.0) / 0.9
        band = np.exp(-(((((XX - cx) / h) * 0.9 - (YY - cy) / h * 0.4) - (-0.9 + 2.2 * g)) / 0.04) ** 2)
        lock_m = np.clip(m + (LOCK.word_mask("astris", Z, off) if t > 7.5 else 0), 0, 1)
        img += (band * lock_m * 0.35)[..., None]
    bloom = 0.55 + 0.9 * math.exp(-max(tau, 0) / 0.25)
    return img, bloom


def style_at(i):
    for k, (nm, d) in enumerate(SEQ):
        if STARTS[k] <= i < STARTS[k + 1]:
            return k, nm, STARTS[k], d
    return None


def frame(i):
    t = i / C.FPS
    if i < LAND_F:
        k, nm, k0, d = style_at(i)
        tl = (i - k0) / C.FPS
        if nm == "rainbow":
            img = np.zeros((H, W, 3), np.float32) + rgb("#030304")
            img = rainbow(img, (i - k0) / C.FPS)
        else:
            if nm not in BASES:
                build_bases([nm])
            img = BASES[nm].astype(np.float32)
            if nm == "hud":
                img = hud_live(img, tl)
            elif nm == "glass":
                img = glass_live(img, tl, d / C.FPS)
            elif nm == "gold":
                img = metal_sweep(img, tl, d / C.FPS, [1.0, 0.85, 0.5])
                img = glints(img, tl, 3, [1.0, 0.9, 0.6])
            elif nm == "chrome":
                img = metal_sweep(img, tl, d / C.FPS, [0.9, 0.95, 1.0], 0.05, 0.8)
                img = glints(img, tl, 4, [0.9, 0.95, 1.0])
            elif nm == "neon" and (i - k0) == 2:
                img = img * 0.82                     # one flicker
        # gentle continuous push + a pop on every switch
        zoom = 1.0 + 0.03 * (i / LAND_F) + 0.035 * math.exp(-(i - k0) / 1.3)
        img = C.warp(img, zoom=zoom, center=REF_C, border=cv2.BORDER_REPLICATE)
        bl, th = BLOOM[nm]
        return POST.finish(img, i, bloom=bl, threshold=th)
    img, bloom = landing(t, i)
    return POST.finish(img, i, bloom=bloom, threshold=0.75)


# ================================================================================================
# sound
# ================================================================================================
FLAVOUR = {
    "pixel": lambda f: S.signal.square(2 * np.pi * f * 2 * S.tt(0.12)) * np.exp(-S.tt(0.12) / 0.04) * 0.25,
    "neon": lambda f: S.sos(np.sign(np.sin(2 * np.pi * 120 * S.tt(0.18))) * 0.2, "lowpass", 1800) * np.exp(-S.tt(0.18) / 0.08),
    "paper": lambda f: S.sos(S.noise(0.12, "white", 3), "bandpass", [1500, 6000]) * np.exp(-S.tt(0.12) / 0.03) * 0.5,
    "blueprint": lambda f: S.sos(S.noise(0.08, "white", 4), "highpass", 4000) * np.exp(-S.tt(0.08) / 0.015) * 0.5,
    "leafy": lambda f: S.sos(S.noise(0.25, "pink", 5), "bandpass", [800, 5000]) * np.exp(-S.tt(0.25) / 0.07) * 0.5,
    "hud": lambda f: np.sin(2 * np.pi * f * 4 * S.tt(0.15)) * np.exp(-S.tt(0.15) / 0.05) * 0.25,
    "glass": lambda f: S.chime(f * 4, 0.9, 1.0, 0.35),
    "gold": lambda f: S.chime(f * 2, 1.2, 1.0, 0.6),
    "chrome": lambda f: S.chime(f * 3, 1.2, 1.0, 0.5) * 0.8,
    "rainbow": lambda f: S.chime(f * 2, 1.5, 1.0, 0.8),
}


def audio():
    m = S.Mix(DUR)
    # rising sub + air under the whole switch sequence
    m.add(S.sub_build(T_LAND, 34, 62, curve=1.6), 0.0, gain=0.35, send=0.0)
    m.add(S.riser(T_LAND, 300, 5000, seed=301), 0.0, gain=0.18, send=0.2)
    # one tick per style; pitch climbs as the switches slow down
    names = [nm for nm, _ in SEQ]
    for k, nm in enumerate(names):
        tk = STARTS[k] / C.FPS
        f = 196.0 * 2 ** (k * 2.2 / len(names))
        m.add(S.tick(f, 0.3, level=1.0, seed=310 + k), tk, gain=0.42, pan=(-1) ** k * 0.15, send=0.18)
        if nm in FLAVOUR:
            m.add(FLAVOUR[nm](f), tk, gain=0.35, pan=(-1) ** k * 0.3, send=0.35)
    # the landing: big hit, resolved chord, then the glossy drips and a shimmer
    m.add(S.whoosh(0.35, peak=0.9, f_lo=500, f_hi=7000, q=1.0, pan_from=0, pan_to=0, seed=330), T_LAND - 0.32,
          gain=0.45, send=0.15)
    m.add(S.impact(3.5, weight=1.4, bright=1.0, metal=0.8, seed=331, sub_f=(90, 32)), T_LAND, gain=0.95, send=0.3)
    chord = [S.midi(45), S.midi(52), S.midi(57), S.midi(61), S.midi(64), S.midi(69)]
    m.add(S.sting(chord, 4.5, bright=0.8, seed=333), T_LAND, gain=0.45, send=0.45)
    m.add(S.shimmer(3.0, root=S.midi(85), density=34, seed=335, rise=0.4), T_LAND + 0.05, gain=0.30, send=0.6)
    for k in range(ND):
        tk = T_LAND + DRIP_T0[k] + 0.35 + 0.25 * DRIP_G[k]
        if tk < DUR - 1.0:
            f0 = 900 + 900 * DRIP_W[k] / 0.018
            x = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 0.8 * np.exp(-S.tt(0.12) / 0.02))) / S.SR) * np.exp(-S.tt(0.12) / 0.03)
            m.add(x, tk, gain=0.05, pan=float(np.clip(DRIPS[k][0] * 1.4, -0.8, 0.8)), send=0.5)
    # pull-out swell + type + final glint
    m.add(S.pad([S.midi(45), S.midi(52), S.midi(57), S.midi(64), S.midi(68)], DUR - T_PULL0, attack=1.4,
                release=1.6, cutoff=(500, 2600), level=1.0, seed=341), T_PULL0, gain=0.20, send=0.5)
    m.add(S.whoosh(0.5, peak=0.8, f_lo=300, f_hi=4500, q=1.0, pan_from=-0.5, pan_to=0.2, seed=343), T_ASTRIS - 0.4,
          gain=0.22, send=0.3)
    m.add(S.shimmer(2.4, root=S.midi(88), density=22, seed=345, rise=0.3), 8.0, gain=0.15, send=0.6)
    mix = m.master(ir_seconds=2.6, wet=0.9, peak_db=-1.5, tail_fade=0.12)
    S.report(mix, NAME)
    return mix


def main():
    C.OUT_DIR.mkdir(exist_ok=True)
    if "--test" in sys.argv:
        fr = [int(a) for a in sys.argv[2].split(",")] if len(sys.argv) > 2 else \
            [0, 2, 5, 9, 14, 20, 28, 38, 51, 68, 90, 104, 118, 124, 134, 150, 170, 190, 239]
        names = sorted({style_at(k)[1] for k in fr if k < LAND_F and style_at(k)[1] != "rainbow"})
        build_bases(names)
        print(C.save_test_frames("intro3", frame, fr, sheet_cols=5))
        return
    build_bases()
    wav = C.OUT_DIR / f"{NAME}.wav"
    S.write_wav24(wav, audio())
    C.render_video(NAME, N, frame, wav, workers=3)


if __name__ == "__main__":
    main()
