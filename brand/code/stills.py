"""
ASTRIS PRODUCTIONS - Part 3: still logos (one "badge" per hero intro and ident, no text).
Each is exported twice: stills/2000/<name>.png (2000x2000, transparent) and stills/150/<name>.png (150x150,
transparent, for YouTube's video watermark). Bold silhouettes and strong edge contrast so they read when tiny;
glows always fade out well inside the canvas. Also writes stills/stills-overview.png.
Usage: python3 stills.py [name ...]
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import common as C
import kit as K

cv2 = C.cv2
S = 2000
OUT = C.ROOT.parent / "output" / "stills"
LOGO = C.Logo()
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
CEN = np.array([S / 2, S / 2 + 20])
LH = 1250.0


def logo_polys(h=LH, c=CEN, pieces=None):
    return LOGO.polys_px(c[0], c[1], h, pieces=pieces)


def mask_of(polys):
    return C.poly_mask_ss(polys, shape=(S, S), ss=2)


M = mask_of(logo_polys())
BIN = (M > 0.5).astype(np.uint8)
DI = cv2.distanceTransform(BIN, cv2.DIST_L2, 5)
DO = cv2.distanceTransform(1 - BIN, cv2.DIST_L2, 5)
SDF = (DO - DI).astype(np.float32)
UU, VV = (xx - CEN[0]) / LH, (yy - CEN[1]) / LH
HOLES = mask_of([logo_polys()[j] for pc in LOGO.pieces for j in pc["holes"]]) if any(pc["holes"] for pc in LOGO.pieces) else np.zeros((S, S), np.float32)


def band(at, half, aa=1.2):
    return np.clip((half - np.abs(SDF - at)) / aa + 0.5, 0, 1)


def grown(r):
    return np.clip((r - SDF) / 1.2 + 0.5, 0, 1)


def blur(m, s):
    return cv2.GaussianBlur(m, (0, 0), s)


class Layer:
    """Straight-alpha RGBA canvas with 'over' compositing."""

    def __init__(self):
        self.rgb = np.zeros((S, S, 3), np.float32)
        self.a = np.zeros((S, S), np.float32)

    def over(self, col, alpha):
        alpha = np.clip(alpha, 0, 1)
        col = np.broadcast_to(np.asarray(col, np.float32), (S, S, 3)) if np.ndim(col) == 1 else col
        a0 = self.a
        out_a = alpha + a0 * (1 - alpha)
        self.rgb = (col * alpha[..., None] + self.rgb * (a0 * (1 - alpha))[..., None]) / np.maximum(out_a, 1e-6)[..., None]
        self.a = out_a
        return self

    def glow(self, mask, col, sigmas=(20, 60), weights=(0.6, 0.4), strength=1.0):
        g = sum(blur(mask, s) * w for s, w in zip(sigmas, weights)) * strength
        return self.over(col, np.clip(g, 0, 1) * (1 - mask))


# ================================================================================================
# the badges
# ================================================================================================
def hero1():
    L = Layer()
    r = np.hypot(xx - CEN[0], yy - CEN[1] + 20)
    ang = (np.arctan2(yy - CEN[1], xx - CEN[0]) / (2 * math.pi)) % 1.0
    ring = np.clip((44 - np.abs(r - 880)) / 3, 0, 1)
    L.over(C.hue_wheel(ang * 1.0) * 1.0, ring * 0.95)
    L.over(K.rgb("#7fd0ff"), np.exp(-np.clip(r - 880, 0, None) / 30) * 0.0)
    L.glow(M, K.rgb("#6fc8ff"), (30, 90), (0.55, 0.45), 1.1)
    rim = band(-6, 7)
    body = np.array([0.96, 0.98, 1.0], np.float32) * (1.04 - 0.12 * VV[..., None] - 0.05 * UU[..., None])
    L.over(body, M)
    L.over(K.rgb("#8fe0ff"), rim * M * 0.85)
    return L


def hero3():
    L = Layer()
    L.glow(grown(40), K.rgb("#ff2bd6"), (24, 70), (0.6, 0.4), 1.2)
    L.over(K.rgb("#ff2bd6"), band(30, 9))
    L.over(K.rgb("#ffffff"), band(30, 3.5) * 0.9)
    L.over(K.rgb("#12121a"), grown(16) * (1 - band(30, 12)))
    L.over(K.rgb("#28e7ff"), band(9, 4))
    n = K.bevel_normals(M, 40, 80)
    chrome = K.env_metal(n, [(0.0, "#1b1208"), (0.30, "#4a3420"), (0.44, "#a58a6a"), (0.47, "#f4f1ea"), (0.49, "#1c2330"),
                             (0.58, "#3d5f8a"), (0.75, "#8db8e6"), (0.9, "#e6f2ff"), (1.0, "#ffffff")], UU, VV, 1.1, (-0.3, -0.9, 0.5))
    L.over(np.clip(chrome, 0, 1.2), M)
    return L


def hero4():
    L = Layer()
    L.glow(M, K.rgb("#ffffff"), (16, 50), (0.5, 0.35), 0.9)
    L.over(K.rgb("#f6f7fb"), M)
    d = UU * 0.95 + VV * 0.35
    q = (d + 0.15) / 0.5
    prism = np.clip(np.sin(np.clip(q, 0, 1) * math.pi), 0, 1) * ((q > 0) & (q < 1))
    L.over(C.spectrum(np.clip(q, 0, 1)), M * prism * 0.85)
    L.over(K.rgb("#ffffff"), band(-4, 4) * M * 0.6)
    return L


def mini01():
    L = Layer()
    L.over(K.rgb("#15151c"), grown(20))
    n = K.bevel_normals(M, 34, 60)
    ph = UU * 2.0 - VV * 1.3 + n[..., 0] * 0.9 + n[..., 1] * 0.7
    spec = C.hue_wheel(ph * 1.3)
    silver = 0.62 + 0.25 * np.clip(-n[..., 1] - n[..., 0] * 0.5, -1, 1)
    sparkle = (np.sin(UU * 300) * np.sin(VV * 300) > 0.93).astype(np.float32) * 0.25
    foil = np.clip(silver[..., None] * 0.55 + spec * 0.6 + sparkle[..., None], 0, 1.2)
    L.over(foil, M)
    L.over(K.rgb("#ffffff"), band(-3, 3) * M * 0.5)
    return L


def scribble02():
    L = Layer()
    r = np.hypot(xx - S / 2, yy - S / 2)
    disc = np.clip((900 - r) / 2, 0, 1)
    L.over(K.rgb("#000000"), blur(np.clip((900 - np.hypot(xx - S / 2 - 12, yy - S / 2 - 18)) / 2, 0, 1), 12) * 0.35)
    paper = K.paper(S, S, K.rgb("#f4ead4"), seed=21, fibres=0.03, grain=0.035, mottle=0.06)
    L.over(paper, disc)
    tooth = K.tooth_map(S, S, 22)
    rng = np.random.default_rng(5)
    g = np.zeros((S, S), np.uint8)          # drawn 8-bit so OpenCV anti-aliases it
    # dense diagonal hatching inside the shape, then wobbly overshooting outlines
    ang = math.radians(52)
    dvec = np.array([math.cos(ang), math.sin(ang)])
    pvec = np.array([-dvec[1], dvec[0]])
    for off in np.arange(-1400, 1400, 22):
        a = CEN + pvec * off - dvec * 1500
        b = CEN + pvec * off + dvec * 1500
        cv2.line(g, tuple(np.round(a * 16).astype(int)), tuple(np.round(b * 16).astype(int)), 191, 7, cv2.LINE_AA, 4)
    hatch_g = g.astype(np.float32) / 255
    g = np.zeros((S, S), np.uint8)
    hatch_g *= M * (1 - grown(0) * 0) * (1 - blur(HOLES, 1) * 1.0)
    for p in logo_polys():
        for a, b in zip(p, np.roll(p, -1, 0)):
            dv = b - a
            L_ = np.linalg.norm(dv)
            if L_ < 10:
                continue
            u = dv / L_
            nrm = np.array([-u[1], u[0]])
            o1, o2 = rng.uniform(10, 30, 2) if L_ > 120 else (2, 2)
            n = max(4, int(L_ / 25))
            s = np.linspace(-o1, L_ + o2, n)
            off = rng.uniform(-3, 3) + 3 * np.sin(s / L_ * math.pi * rng.uniform(1, 2))
            pts = a + np.outer(s, u) + np.outer(off, nrm)
            cv2.polylines(g, [np.round(pts * 16).astype(np.int32)], False, 255, 22 if L_ > 120 else 12, cv2.LINE_AA, 4)
    g = np.maximum(hatch_g, g.astype(np.float32) / 255)
    gg = (1 - np.exp(-g * 2.6)) * (0.6 + 0.4 * tooth) * disc
    L.over(K.rgb("#1d1f25"), np.clip(gg * 1.1, 0, 1))
    return L


def graffiti03():
    L = Layer()
    rng = np.random.default_rng(3)
    allp = np.concatenate(logo_polys())
    y0, y1 = allp[:, 1].min(), allp[:, 1].max()
    keys = [(0.0, "#ff2d8a"), (0.28, "#ff7a1a"), (0.5, "#ffd21f"), (0.72, "#38e05a"), (1.0, "#19c8ff")]
    v = np.clip((yy - y0) / (y1 - y0), 0, 1)
    fade = np.stack([np.interp(v, [k for k, _ in keys], [K.rgb(h)[c] for _, h in keys]) for c in range(3)], -1).astype(np.float32)
    block = np.clip(mask_of([p + [42, 36] for p in logo_polys()]) + mask_of([p + [21, 18] for p in logo_polys()]), 0, 1)
    L.over(K.rgb("#3b0f5e"), blur(np.clip(block - 0, 0, 1), 1.2))
    out = np.clip((26 - SDF) / 6, 0, 1)
    L.over(K.rgb("#0c0b10"), out)
    # drips
    dm = np.zeros((S, S), np.uint8)
    for pc in LOGO.pieces:
        p = logo_polys()[pc["outer"]]
        for a, b in zip(p, np.roll(p, -1, 0)):
            if abs(b[1] - a[1]) < 4 and np.linalg.norm(b - a) > 100 and a[1] > CEN[1]:
                for sx in rng.uniform(0.1, 0.9, 3):
                    q = a + (b - a) * sx
                    L_ = rng.uniform(60, 150)
                    cv2.line(dm, (int(q[0] * 16), int((q[1] + 20) * 16)), (int(q[0] * 16), int((q[1] + 20 + L_) * 16)), 255, 14, cv2.LINE_AA, 4)
                    cv2.circle(dm, (int(q[0] * 16), int((q[1] + 20 + L_) * 16)), 16 * 11, 255, -1, cv2.LINE_AA, 4)
    L.over(K.rgb("#0c0b10"), dm.astype(np.float32) / 255)
    L.over(fade, np.clip((2 - SDF) / 2, 0, 1) * M)
    hl = np.clip(M - np.clip(cv2.warpAffine(M, np.float32([[1, 0, 16], [0, 1, 16]]), (S, S)), 0, 1), 0, 1) * (VV < 0.2)
    L.over(K.rgb("#ffffff"), hl * 0.95)
    for c in (np.array([CEN[0] - 520, CEN[1] - 330]), np.array([CEN[0] + 420, CEN[1] - 560])):
        st = np.zeros((S, S), np.uint8)
        for a in (0, math.pi / 2):
            dv = np.array([math.cos(a), math.sin(a)]) * 70
            cv2.line(st, tuple(np.round((c - dv) * 16).astype(int)), tuple(np.round((c + dv) * 16).astype(int)), 255, 12, cv2.LINE_AA, 4)
        cv2.circle(st, tuple(np.round(c * 16).astype(int)), 16 * 14, 255, -1, cv2.LINE_AA, 4)
        L.over(K.rgb("#ffffff"), st.astype(np.float32) / 255)
    return L


def prism05():
    L = Layer()
    r = np.hypot(xx - CEN[0], yy - CEN[1])
    ang = (np.arctan2(yy - CEN[1], xx - CEN[0]) / (2 * math.pi) + 0.15) % 1.0
    fringe = np.clip((36 - np.abs(SDF - 24)) / 18, 0, 1) * (SDF > 0)
    L.over(C.spectrum(ang), fringe * 0.95)
    L.glow(M, K.rgb("#ffffff"), (14, 40), (0.5, 0.3), 0.8)
    n = K.bevel_normals(M, 60, 80)
    fres = np.clip(1 - n[..., 2], 0, 1) ** 1.1
    body = np.array([0.86, 0.9, 1.0], np.float32)[None, None] * (0.55 + 0.3 * np.clip(0.5 - VV - UU * 0.3, 0, 1))[..., None]
    L.over(body, M * 0.55)
    L.over(K.rgb("#ffffff"), M * np.clip(fres * 1.5, 0, 1))
    L.over(K.rgb("#ffffff"), band(-2, 2.5) * M)
    return L


def glitch06():
    L = Layer()
    sh = 30
    cy = cv2.warpAffine(M, np.float32([[1, 0, -sh], [0, 1, 0]]), (S, S))
    mg = cv2.warpAffine(M, np.float32([[1, 0, sh], [0, 1, 0]]), (S, S))
    L.over(K.rgb("#00f0ff"), cy * 0.9)
    L.over(K.rgb("#ff1fd1"), mg * 0.9)
    body = M.copy()
    for y0, h, dx in ((620, 46, 70), (1180, 30, -60), (1390, 38, 44)):
        body[y0:y0 + h] = np.roll(M[y0:y0 + h], dx, axis=1)
    L.over(K.rgb("#f4f6ff"), body)
    L.over(K.rgb("#c6ff00"), np.clip(body[...] * 0, 0, 1))
    return L


def ink07():
    L = Layer()
    rng = np.random.default_rng(7)
    r = np.hypot(xx - S / 2, yy - S / 2)
    wob = cv2.resize(K.fbm(S // 16, S // 16, 72, 5), (S, S))
    disc = np.clip((900 + 40 * (wob - 0.5) - r) / 3, 0, 1)
    L.over(K.rgb("#000000"), blur(disc, 14) * 0.3)
    L.over(K.paper(S, S, K.rgb("#f7f3ea"), seed=74, fibres=0.02, grain=0.03, mottle=0.08), disc)
    n = cv2.resize(K.fbm(S // 8, S // 8, 71, 6), (S, S))
    for (c, col, rad) in (((CEN[0] - 560, CEN[1] + 470), "#ff2d9a", 260), ((CEN[0] + 600, CEN[1] + 380), "#19c8ff", 230),
                          ((CEN[0] - 120, CEN[1] + 560), "#ffc21f", 200), ((CEN[0] + 120, CEN[1] - 520), "#8a4dff", 180)):
        d = np.hypot(xx - c[0], yy - c[1])
        bloom = np.clip(1 - d / (rad * (0.8 + 0.5 * n)), 0, 1) ** 1.4
        L.over(K.rgb(col), blur(bloom, 10) * 0.6 * disc)
    feather = np.clip((-SDF + 10 * (n - 0.5)) / 6 + 0.5, 0, 1)
    L.over(K.rgb("#2a2c8a") * (0.8 + 0.3 * n[..., None]), blur(feather, 2.5))
    L.over(K.rgb("#1f2170"), M * 0.9)
    return L


def cutout08():
    L = Layer()
    paper = K.paper(S, S, (1, 1, 1), seed=83, fibres=0.03, grain=0.03, mottle=0.05)[..., 0]
    bar = mask_of(logo_polys(pieces=[len(LOGO.pieces) - 1]))
    film = mask_of(logo_polys(pieces=list(range(len(LOGO.pieces) - 1))))
    allm = np.maximum(bar, film)
    sh = blur(cv2.warpAffine(allm, np.float32([[1, 0, 20], [0, 1, 28]]), (S, S)), 14)
    L.over(K.rgb("#000000"), sh * 0.45 * (1 - allm))
    for m_, col in ((film, K.rgb("#ff6b6b")), (bar, K.rgb("#ffd23f"))):
        edge = cv2.warpAffine(m_, np.float32([[1, 0, 0], [0, 1, 8]]), (S, S))
        L.over(col * 0.62, edge)
        L.over(col[None, None] * (0.93 + 0.12 * (paper - 1) * 6)[..., None], m_)
    top = (yy < CEN[1] - 80).astype(np.float32) * film
    L.over(K.rgb("#ff8c69")[None, None] * (0.93 + 0.12 * (paper - 1) * 6)[..., None], top)
    return L


def film09():
    L = Layer()
    fr = np.zeros((S, S), np.float32)
    x0, y0, x1, y1, rad = 110, 160, S - 110, S - 160, 150
    cv2.rectangle(fr, (x0 + rad, y0), (x1 - rad, y1), 1.0, -1)
    cv2.rectangle(fr, (x0, y0 + rad), (x1, y1 - rad), 1.0, -1)
    for cx, cy in ((x0 + rad, y0 + rad), (x1 - rad, y0 + rad), (x0 + rad, y1 - rad), (x1 - rad, y1 - rad)):
        cv2.circle(fr, (cx, cy), rad, 1.0, -1, cv2.LINE_AA)
    fr = blur(fr, 1.0)
    base = K.rgb("#1b130d") * (1.15 - 0.45 * np.hypot(UU, VV) * 0.9)[..., None]
    L.over(base, fr)
    halo = blur(M, 26) * 0.8 + blur(M, 70) * 0.5
    L.over(K.rgb("#ff5a1e"), np.clip(halo, 0, 1) * 0.55 * fr * (1 - M))
    L.over(K.rgb("#f2e2bf"), M)
    dark, light = K.dust_layer(7, 909, density=2.0, shape=(S, S))
    grain = cv2.GaussianBlur(np.random.default_rng(9).standard_normal((S, S)).astype(np.float32), (0, 0), 1.4)
    L.rgb = np.clip(L.rgb * (1 + 0.06 * grain[..., None]) * (1 - 0.8 * dark[..., None]) + light[..., None] * 0.5, 0, 1.2)
    return L


def seventies10():
    L = Layer()
    r = np.hypot(xx - S / 2, yy - S / 2)
    ang = np.arctan2(yy - S / 2, xx - S / 2)
    disc = np.clip((950 - r) / 2, 0, 1)
    L.over(K.rgb("#4a2412"), disc)
    inner = np.clip((910 - r) / 2, 0, 1)
    rays = (np.sin(ang * 16) > 0).astype(np.float32)
    L.over(K.rgb("#f6b23c"), inner)
    L.over(K.rgb("#e8641e"), inner * blur(rays, 1.0))
    allp = np.concatenate(logo_polys())
    y0, y1 = allp[:, 1].min(), allp[:, 1].max()
    stripes = [K.rgb(h) for h in ("#e8641e", "#f2a922", "#7a3e1d", "#f6e7c8", "#1f9e98")]
    bandi = np.clip(((yy - y0) / (y1 - y0) * 5).astype(np.int32), 0, 4)
    fill = np.zeros((S, S, 3), np.float32)
    for j, c in enumerate(stripes):
        fill[bandi == j] = c
    L.over(K.rgb("#1f9e98"), grown(40))
    L.over(K.rgb("#f6e7c8"), grown(28))
    L.over(K.rgb("#4a2412"), grown(16))
    L.over(fill, M)
    return L


def synth11():
    L = Layer()
    r = np.hypot(xx - S / 2, yy - S / 2 + 40)
    v = np.clip((yy - (S / 2 - 40 - 900)) / 1800, 0, 1)
    sun = np.stack([np.interp(v, [0, 0.5, 1], [K.rgb(h)[c] for h in ("#fff36b", "#ff9a3d", "#ff2d8f")]) for c in range(3)], -1)
    rel = (yy - (S / 2 - 40)) / 900
    phase = (rel * 7) % 1.0
    gap = np.clip(0.1 + 0.45 * np.clip((rel + 0.3) / 1.2, 0, 1), 0, 0.6)
    bars = np.where(rel > -0.3, (phase > gap).astype(np.float32), 1.0)
    L.over(K.rgb("#ff2bd6"), blur(np.clip((910 - r) / 2, 0, 1), 18) * 0.5)
    L.over(sun, np.clip((900 - r) / 2, 0, 1) * bars)
    L.over(K.rgb("#14052a"), grown(20))
    L.over(K.rgb("#ff9ae6"), band(10, 4))
    n = K.bevel_normals(M, 34, 70)
    chrome = K.env_metal(n, [(0.0, "#12052a"), (0.30, "#3b1a6e"), (0.45, "#9a6ad8"), (0.49, "#ff8ad8"), (0.51, "#ffffff"),
                             (0.54, "#ffb347"), (0.62, "#4ad0ff"), (0.82, "#d4f4ff"), (1.0, "#ffffff")], UU, VV, 1.1, (-0.4, -0.85, 0.5))
    L.over(np.clip(chrome, 0, 1.2), M)
    return L


def from_3d(style, glow_col):
    raw = next(K.frames_3d(f"still3d_scene.html?style={style}", [0], f"still3d_{style}.log", size=(S, S)))[2]
    a = np.frombuffer(raw, np.uint8).reshape(S, S, 4)[::-1].astype(np.float32) / 255
    prem, al = a[..., :3], a[..., 3]
    L = Layer()
    L.glow(al, K.rgb(glow_col), (30, 90), (0.5, 0.4), 0.9)
    L.over(prem / np.maximum(al, 1e-4)[..., None], al)
    return L


# ------------------------------------------------------------------------------------------------
# bonus badges
# ------------------------------------------------------------------------------------------------
RR = np.hypot(xx - S / 2, yy - S / 2)
DISC = np.clip((930 - RR) / 2, 0, 1)


def aa_lines(draw_fn):
    """Run cv2 drawing calls on an 8-bit layer (so OpenCV anti-aliases them) and return it as float 0..1."""
    m = np.zeros((S, S), np.uint8)
    draw_fn(m)
    return m.astype(np.float32) / 255


def neon_b1():
    L = Layer()
    r = np.random.default_rng(31)
    bricks = np.zeros((S, S), np.float32)
    for row in range(-1, S // 110 + 2):
        off = (row % 2) * 120
        for col in range(-1, S // 240 + 2):
            x0, y0 = col * 240 + off, row * 110
            cv2.rectangle(bricks, (x0 + 6, y0 + 6), (x0 + 234, y0 + 104), float(r.uniform(0.6, 1.0)), -1)
    wall = K.rgb("#120a10") + blur(bricks, 1.5)[..., None] * K.rgb("#2a1620")
    lightm = blur(M, 70) * 1.6 + blur(M, 200) * 0.9
    wall = wall * (0.55 + lightm[..., None] * K.rgb("#ff7ac0") * 1.4)
    L.over(K.rgb("#2a2a33"), np.clip((946 - RR) / 2, 0, 1))
    L.over(np.clip(wall, 0, 1), DISC)
    u = np.clip((SDF + 26) / 13, -1, 1)
    tube = band(-26, 13)
    core = (1 - u * u) ** 1.6
    L.over(K.rgb("#ff2f9a") * 0.5 + 0.05, M * 0.35)
    L.over(K.rgb("#ff2f9a"), np.clip(blur(tube, 10) * 1.3, 0, 1) * (1 - tube) * 0.9)
    tube_col = K.rgb("#ff2f9a")[None, None] * (1 - core[..., None]) + K.rgb("#fff0fa")[None, None] * core[..., None]
    L.over(tube_col, tube)
    return L


def stars_b2():
    L = Layer()
    v = np.clip((yy - 70) / 1860, 0, 1)
    sky = K.rgb("#04051a") * (1 - v[..., None]) + K.rgb("#14104a") * v[..., None]
    xn = (xx - 70) / 1860
    edge = 1180 - 120 * np.sin(xn * math.pi * 1.6 + 0.4)
    d = edge - yy
    dp = np.clip(d, 0, None)
    rays = 0.6 + 0.4 * np.sin(xx * 0.09) * np.sin(xx * 0.023 + 1)
    aur = (np.exp(-dp / 260) * (1 - np.exp(-dp / 4)) + np.exp(-((d - 10) / 12) ** 2) * 1.4) * rays
    sky = sky + C.hue_wheel(xn * 0.85 + 0.95)[...] * (aur * 0.55)[..., None]
    rng = np.random.default_rng(32)
    st = aa_lines(lambda m: [cv2.circle(m, (int(rng.uniform(0, S) * 4), int(rng.uniform(0, S) * 4)), int(4 * rng.uniform(1.5, 4)),
                                        int(255 * rng.uniform(0.3, 1.0)), -1, cv2.LINE_AA, 2) for _ in range(700)])
    sky = sky + st[..., None] * 0.9
    L.over(K.rgb("#1d1d3a"), np.clip((946 - RR) / 2, 0, 1))
    L.over(np.clip(sky, 0, 1.2), DISC)
    polys = logo_polys()
    main = [q for q in polys if abs(cv2.contourArea(q.astype(np.float32))) > 30000]
    holes = [q for q in polys if abs(cv2.contourArea(q.astype(np.float32))) <= 30000]
    L.over(K.rgb("#8f9fff"), np.clip(blur(M, 40) * 0.9, 0, 1) * (1 - M) * 0.5)
    L.over(K.rgb("#b8c4ff"), M * 0.30)
    corners = []
    lines = np.zeros((S, S), np.uint8)
    for q in main:
        ap = cv2.approxPolyDP(q.astype(np.float32).reshape(-1, 1, 2), 8.0, True).reshape(-1, 2)
        cv2.polylines(lines, [np.round(ap * 16).astype(np.int32)], True, 255, 16, cv2.LINE_AA, 4)
        corners += list(ap)
    ln = lines.astype(np.float32) / 255
    L.over(K.rgb("#cfd8ff"), np.clip(blur(ln, 8) * 1.2, 0, 1) * 0.6)
    L.over(K.rgb("#eef1ff"), ln)
    sp = np.zeros((S, S), np.uint8)
    for c in corners:
        cv2.circle(sp, (int(c[0] * 16), int(c[1] * 16)), 16 * 30, 255, -1, cv2.LINE_AA, 4)
        for a in (0, math.pi / 2):
            dv = np.array([math.cos(a), math.sin(a)]) * 110
            cv2.line(sp, tuple(np.round((c - dv) * 16).astype(int)), tuple(np.round((c + dv) * 16).astype(int)), 255, 7, cv2.LINE_AA, 4)
    for q in holes:
        c = q.mean(0)
        cv2.circle(sp, (int(c[0] * 16), int(c[1] * 16)), 16 * 11, 255, -1, cv2.LINE_AA, 4)
    spf = sp.astype(np.float32) / 255
    L.over(K.rgb("#dfe6ff"), np.clip(blur(spf, 14) * 1.5, 0, 1) * 0.7)
    L.over(K.rgb("#ffffff"), spf)
    return L


def fireworks_b3():
    L = Layer()
    v = np.clip((yy - 70) / 1860, 0, 1)
    sky = K.rgb("#03030f") * (1 - v[..., None]) + K.rgb("#0e0c2a") * v[..., None]
    rng = np.random.default_rng(33)
    burst = np.zeros((S, S, 3), np.float32)
    for k in range(150):
        a = k / 150 * 2 * math.pi + rng.uniform(-0.01, 0.01)
        r0, r1 = rng.uniform(380, 520), rng.uniform(760, 880)
        col = C.hue_wheel(np.float32(a / (2 * math.pi) + 0.5))
        seg = np.zeros((S, S), np.uint8)
        for j in range(8):
            ra, rb = r0 + (r1 - r0) * j / 8, r0 + (r1 - r0) * (j + 1) / 8
            pa = np.array([S / 2 + math.cos(a) * ra, S / 2 + math.sin(a) * ra])
            pb = np.array([S / 2 + math.cos(a) * rb, S / 2 + math.sin(a) * rb])
            cv2.line(seg, tuple(np.round(pa * 16).astype(int)), tuple(np.round(pb * 16).astype(int)), int(255 * (0.25 + 0.75 * (j + 1) / 8)), 7, cv2.LINE_AA, 4)
        tip = np.array([S / 2 + math.cos(a) * r1, S / 2 + math.sin(a) * r1])
        cv2.circle(seg, (int(tip[0] * 16), int(tip[1] * 16)), 16 * 9, 255, -1, cv2.LINE_AA, 4)
        burst += (seg.astype(np.float32) / 255)[..., None] * col
    burst = burst + blur(burst, 6) * 0.8
    L.over(K.rgb("#22222c"), np.clip((946 - RR) / 2, 0, 1))
    L.over(np.clip(sky + burst, 0, 1.2), DISC)
    ang = np.arctan2(yy - CEN[1], xx - CEN[0])
    halo = C.hue_wheel(((ang / (2 * math.pi)) + 0.5) % 1.0)
    L.over(halo, np.clip(blur(M, 26) * 1.6, 0, 1) * (1 - M) * 0.85)
    L.over(K.rgb("#1a0f06"), grown(10) * (1 - M))
    allp = np.concatenate(logo_polys())
    vv = np.clip((yy - allp[:, 1].min()) / (allp[:, 1].max() - allp[:, 1].min()), 0, 1)
    fill = K.rgb("#fff4dc") * (1 - vv[..., None]) + K.rgb("#ffc04f") * vv[..., None]
    L.over(fill, M)
    return L


def arcade_b4():
    L = Layer()
    blk = 20
    g = S // blk
    small = cv2.resize(M, (g, g), interpolation=cv2.INTER_AREA)
    lm = (small > 0.5).astype(np.uint8)
    k3 = np.ones((3, 3), np.uint8)
    ring1 = cv2.dilate(lm, k3) - lm
    ring2 = cv2.dilate(lm, np.ones((5, 5), np.uint8)) - cv2.dilate(lm, k3)
    ys = np.nonzero(lm.any(1))[0]
    v = np.clip((np.arange(g) - ys.min()) / max(1, ys.max() - ys.min()), 0, 1)
    bandi = np.clip((v * 6).astype(int), 0, 5)
    pal = np.array([K.rgb(h) for h in ("#ff3b5c", "#ff9a2f", "#ffe14d", "#3fe07a", "#3fa0ff", "#a05aff")], np.float32)
    fill = pal[bandi][:, None, :].repeat(g, 1)
    hi = np.zeros((g, g), np.float32)
    hi[1:, :] = lm[1:, :] & (1 - lm[:-1, :])                 # a pixel highlight on top edges
    plate = np.zeros((g, g), np.float32)
    c = g // 2
    for yb in range(g):
        for xb in range(g):
            dx, dy = abs(xb + 0.5 - c), abs(yb + 0.5 - c)
            if max(dx, dy) < 46 and (dx + dy) < 84:
                plate[yb, xb] = 1
    border = plate - cv2.erode(plate, k3)
    shadow = np.roll(np.roll(cv2.dilate(lm, k3), 1, 0), 1, 1)
    up = lambda a: cv2.resize(a.astype(np.float32), (S, S), interpolation=cv2.INTER_NEAREST)
    upc = lambda a: cv2.resize(a.astype(np.float32), (S, S), interpolation=cv2.INTER_NEAREST)
    L.over(K.rgb("#0b0826"), up(plate))
    L.over(K.rgb("#ff3fa4"), up(border))
    rngs = np.random.default_rng(34)
    st = np.zeros((g, g), np.float32)
    for _ in range(40):
        st[rngs.integers(4, g - 4), rngs.integers(4, g - 4)] = 1
    L.over(K.rgb("#ffffff"), up(st * plate * (1 - cv2.dilate(lm, np.ones((7, 7), np.uint8)))))
    L.over(K.rgb("#05020f"), up(shadow * plate))
    L.over(K.rgb("#140726"), up(ring1 + ring2 * 0))
    L.over(upc(fill), up(lm))
    L.over(K.rgb("#ffffff"), up(hi * 0.55))
    return L


LAMBDA = np.array([650, 610, 570, 540, 510, 480, 450], np.float32)
TO_RGB = np.array([[1.00, 0.05, 0.00], [0.95, 0.35, 0.00], [0.55, 0.85, 0.00], [0.15, 1.00, 0.10],
                   [0.00, 0.75, 0.55], [0.00, 0.30, 1.00], [0.35, 0.00, 1.00]], np.float32)
TO_RGB /= TO_RGB.sum(0, keepdims=True)


def film_colour(d, cos_t, n=1.33):
    """Soap-film interference colour for thickness d (nm) - same model as bonus05_bubbles.py."""
    ct = np.sqrt(np.clip(1 - (1 - cos_t ** 2) / (n * n), 0, 1))
    I = np.sin(math.pi * (2 * n * d * ct)[..., None] / LAMBDA) ** 2
    return (I @ TO_RGB) * 1.15


def bubble_b5():
    L = Layer()
    v = np.clip((yy - 70) / 1860, 0, 1)
    bg = K.rgb("#071624") * (1 - v[..., None]) + K.rgb("#1a0f33") * v[..., None]
    L.over(K.rgb("#22222e"), np.clip((946 - RR) / 2, 0, 1))
    L.over(bg, DISC)
    R = 860.0
    u, w = (xx - S / 2) / R, (yy - S / 2) / R
    rr = np.sqrt(u * u + w * w)
    cover = np.clip((1 - rr) * R / 1.3 + 0.5, 0, 1)
    nz = np.sqrt(np.clip(1 - rr * rr, 0, 1))
    sw = cv2.resize(K.fbm(256, 256, 35, 7, aspect=1.0), (S, S), interpolation=cv2.INTER_CUBIC)
    sw = (sw - sw.min()) / (sw.max() - sw.min())
    d = 430 + 520 * sw + 120 * np.clip(w, -1, 1) + 50 * np.sin(u * 4.0)        # 2nd-4th order: vivid bands
    col = film_colour(d.astype(np.float32), nz)
    fres = 0.04 + 0.96 * (1 - nz) ** 5
    refl = col * (0.42 + 0.9 * fres)[..., None] * (0.55 + 0.45 * np.clip(-w, -1, 1))[..., None] * 1.25
    h1 = np.exp(-(((u + 0.38) / 0.15) ** 4 + ((w + 0.42) / 0.10) ** 4)) * 0.85
    rim = np.exp(-((1 - rr) * R / 4.0) ** 2) * 0.4
    film = np.clip(bg * (1 - 0.18 * fres[..., None]) + refl + (h1 + rim)[..., None], 0, 1.2)
    L.over(film, cover * DISC)
    L.over(K.rgb("#c8b8ff"), np.clip(blur(M, 30) * 1.2, 0, 1) * (1 - M) * 0.45)
    L.over(K.rgb("#0d0a20"), grown(8) * (1 - M) * 0.6)
    n = K.bevel_normals(M, 30, 50)
    sheen = film_colour((520 * (0.6 + 0.8 * sw) + 120 * VV).astype(np.float32), np.clip(n[..., 2], 0.2, 1))
    Ld = np.array([-0.4, -0.75, 0.55], np.float32)
    Ld /= np.linalg.norm(Ld)
    body = (0.82 + 0.2 * np.clip((n * Ld).sum(-1), 0, 1))[..., None] * K.rgb("#fbf8ff") + sheen * 0.3
    L.over(np.clip(body, 0, 1.1), M)
    return L


STILLS = {
    "logo-hero-1": hero1, "logo-hero-2": lambda: from_3d("pearl", "#a060ff"), "logo-hero-3": hero3, "logo-hero-4": hero4,
    "logo-01-mini-switcher": mini01, "logo-02-scribble": scribble02, "logo-03-graffiti": graffiti03,
    "logo-04-flythrough": lambda: from_3d("gold", "#ffb85c"), "logo-05-prism": prism05, "logo-06-glitch": glitch06,
    "logo-07-ink": ink07, "logo-08-cutout": cutout08, "logo-09-16mm": film09, "logo-10-sunburst": seventies10,
    "logo-11-synthwave": synth11,
    "logo-bonus-01": neon_b1, "logo-bonus-02": stars_b2, "logo-bonus-03": fireworks_b3, "logo-bonus-04": arcade_b4,
    "logo-bonus-05": bubble_b5,
}


def save(name, L):
    (OUT / "2000").mkdir(parents=True, exist_ok=True)
    (OUT / "150").mkdir(parents=True, exist_ok=True)
    a = np.clip(L.a, 0, 1)
    rgb = np.clip(L.rgb, 0, 1)
    # make sure nothing touches the canvas edge (the glow must fade out inside the badge)
    edge = max(a[:6].max(), a[-6:].max(), a[:, :6].max(), a[:, -6:].max())
    rgba = np.dstack([rgb, a])
    Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").save(OUT / "2000" / f"{name}.png", optimize=True)
    prem = rgb * a[..., None]
    sp = cv2.resize(prem, (150, 150), interpolation=cv2.INTER_AREA)
    sa = cv2.resize(a, (150, 150), interpolation=cv2.INTER_AREA)
    srgb = sp / np.maximum(sa, 1e-4)[..., None]
    blur_ = cv2.GaussianBlur(srgb, (0, 0), 0.8)
    srgb = np.clip(srgb + (srgb - blur_) * 0.35, 0, 1)                  # a touch of sharpening for the tiny size
    Image.fromarray((np.dstack([srgb, sa]) * 255 + 0.5).astype(np.uint8), "RGBA").save(OUT / "150" / f"{name}.png", optimize=True)
    return edge


def overview(names):
    cols = 5
    cell = 420
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell + 40, rows * (cell + 120) + 90), (16, 16, 20))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(str(C.FONT_DIR / "montserrat-500.ttf"), 20)
    ft = ImageFont.truetype(str(C.FONT_DIR / "syncopate-700.ttf"), 30)
    d.text((24, 22), "ASTRIS PRODUCTIONS  -  STILL LOGOS", font=ft, fill=(235, 235, 240))
    for k, n in enumerate(names):
        im = Image.open(OUT / "2000" / f"{n}.png").resize((cell - 140, cell - 140), Image.LANCZOS)
        small = Image.open(OUT / "150" / f"{n}.png")
        x, y = 20 + (k % cols) * cell + 20, 80 + (k // cols) * (cell + 120)
        sheet.paste(im, (x, y), im)
        sheet.paste(small, (x + cell - 190, y + cell - 66), small)          # the real 150 px file, at 1:1
        d.text((x, y + cell - 34), n.replace("logo-", ""), font=f, fill=(170, 170, 185))
    sheet.save(OUT / "stills-overview.png", optimize=True)


if __name__ == "__main__":
    names = [a for a in sys.argv[1:] if a in STILLS] or list(STILLS)
    for n in names:
        L = STILLS[n]()
        edge = save(n, L)
        kb = (OUT / "150" / f"{n}.png").stat().st_size / 1024
        print(f"{n}: saved (150px = {kb:.0f} KB){'  WARNING: touches the edge' if edge > 0.02 else ''}", flush=True)
    overview([n for n in STILLS if (OUT / "2000" / f"{n}.png").exists()])
    print("overview written")
