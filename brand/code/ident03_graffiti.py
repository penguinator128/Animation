"""
ASTRIS PRODUCTIONS - Ident 03: GRAFFITI (5.0 s, fast and punchy)

A brick wall at night under one sodium street lamp. A can rattles, then the logo is tagged as a proper
graffiti piece: deep-purple 3D block, a rainbow-fade fill sprayed in zigzag passes with overspray, a black
outline, white highlights and sparkles. On the landing a phone flash snaps it - splatter, camera shake, an
808 thump - and the paint starts to drip down the bricks. ASTRIS PRODUCTIONS is stencilled underneath.
Sound: can rattle, hiss for every pass, outline bursts, a deep thump + bass drop, flash click, stencil psshts.
"""
import math

import numpy as np

import common as C
import kit as K
import sfx as X
import sound as S

cv2 = C.cv2
NAME = "astris-ident-03"
DUR = 5.0
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=303, grain=0.03, vignette=0.42)
R = np.random.default_rng(3)

T_FILL0, T_FILL1 = 0.45, 1.35
T_LINE0, T_LINE1 = 1.35, 2.02
T_HI0, T_HI1 = 2.02, 2.28
T_LAND = 2.30
T_ST1, T_ST2 = 2.55, 3.02

# ---------------------------------------------------------------- the wall (static, design space)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def build_wall():
    bw, bh, mortar = 300, 108, 12
    height = np.zeros((H, W), np.float32)
    tint = np.zeros((H, W, 3), np.float32)
    rng = np.random.default_rng(31)
    base_cols = [K.rgb(h) for h in ("#5b2a1f", "#6d3324", "#4a231b", "#7a3b29", "#563028", "#62301f")]
    for row in range(-1, H // bh + 2):
        off = (row % 2) * bw // 2 + rng.integers(-8, 8)
        for col in range(-1, W // bw + 2):
            x0, y0 = col * bw + off + mortar // 2, row * bh + mortar // 2
            x1, y1 = x0 + bw - mortar, y0 + bh - mortar
            c = base_cols[rng.integers(0, len(base_cols))] * rng.uniform(0.8, 1.15)
            pts = np.array([[x0 + rng.normal(0, 2), y0 + rng.normal(0, 2)], [x1 + rng.normal(0, 2), y0 + rng.normal(0, 2)],
                            [x1 + rng.normal(0, 2), y1 + rng.normal(0, 2)], [x0 + rng.normal(0, 2), y1 + rng.normal(0, 2)]])
            cv2.fillPoly(height, [np.round(pts).astype(np.int32)], 1.0, cv2.LINE_AA)
            cv2.fillPoly(tint, [np.round(pts).astype(np.int32)], tuple(float(v) for v in c), cv2.LINE_AA)
    height = cv2.GaussianBlur(height, (0, 0), 2.2)
    rough = cv2.resize(K.fbm(H // 3, W // 3, 32, 6, base=6), (W, H))
    pits = (np.random.default_rng(33).random((H // 2, W // 2)) > 0.985).astype(np.float32)
    pits = cv2.resize(cv2.GaussianBlur(pits, (0, 0), 1.2), (W, H))
    height = height * (0.82 + 0.25 * rough) - pits * 0.4
    mortar_col = K.rgb("#3b3532") * (0.8 + 0.4 * rough[..., None])
    alb = tint * np.clip(height, 0, 1)[..., None] + mortar_col * (1 - np.clip(height, 0, 1))[..., None]
    alb *= (0.75 + 0.5 * rough[..., None])
    # old, faded ghosts of earlier tags and a torn poster corner
    ghost = np.zeros((H, W), np.float32)
    for _ in range(14):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        pts = np.cumsum(rng.normal(0, 60, (12, 2)), 0) + [x, y]
        cv2.polylines(ghost, [np.round(pts).astype(np.int32)], False, 1.0, int(rng.integers(10, 26)), cv2.LINE_AA)
    ghost = cv2.GaussianBlur(ghost, (0, 0), 4)
    alb = alb * (1 - 0.25 * ghost[..., None]) + ghost[..., None] * K.rgb("#4a6c7a") * 0.18
    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3)
    n = np.stack([-gx * 3, -gy * 3, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return alb.astype(np.float32), n.astype(np.float32), rough


ALB, NRM, ROUGH = build_wall()
LAMP = np.array([1450.0, -820.0])         # warm street lamp, above the frame, aimed at the piece


def lighting(flash=0.0):
    """Warm street lamp (from above, pooling on the piece) + cool moonlight + a phone flash from the front."""
    d = np.stack([LAMP[0] - xx, LAMP[1] - yy, np.full_like(xx, 900.0)], -1)
    dist = np.linalg.norm(d, axis=-1, keepdims=True)
    L = d / dist
    lam = np.clip((NRM * L).sum(-1), 0, 1)
    fall = (1 / (1 + (dist[..., 0] / 2300) ** 2)) * 4.0
    sodium = (lam * fall)[..., None] * K.rgb("#ffc890")
    moon = np.clip(NRM[..., 0] * -0.6 + NRM[..., 2] * 0.5, 0, 1)[..., None] * K.rgb("#5b7fc0") * 0.30
    fl = (NRM[..., 2:3] * 0.9 + 0.1) * flash * K.rgb("#ffffff") * 1.6
    return sodium + moon + fl + 0.02


LIGHT0 = lighting(0.0).astype(np.float32)

# ---------------------------------------------------------------- the piece
LOGO_H, LOGO_C = 820.0, np.array([W / 2, 800.0])
POLYS = LOGO.polys_px(LOGO_C[0], LOGO_C[1], LOGO_H)
MASK = C.poly_mask_ss(POLYS, ss=2)
BIN = (MASK > 0.5).astype(np.uint8)
SDF = (cv2.distanceTransform(1 - BIN, cv2.DIST_L2, 5) - cv2.distanceTransform(BIN, cv2.DIST_L2, 5)).astype(np.float32)
OUTER = C.poly_mask([POLYS[pc["outer"]] for pc in LOGO.pieces])
x0, y0 = np.concatenate(POLYS).min(0)
x1, y1 = np.concatenate(POLYS).max(0)
# rainbow fade top -> bottom (hot pink, orange, yellow, green, cyan)
fade_keys = [(0.0, "#ff2d8a"), (0.28, "#ff7a1a"), (0.5, "#ffd21f"), (0.72, "#38e05a"), (1.0, "#19c8ff")]
v = np.clip((yy - y0) / (y1 - y0), 0, 1)
FADE = np.stack([np.interp(v, [k for k, _ in fade_keys], [K.rgb(h)[c] for _, h in fade_keys]) for c in range(3)], -1).astype(np.float32)
BLOCK = np.clip(C.poly_mask([p + [34, 30] for p in POLYS]) + C.poly_mask([p + [17, 15] for p in POLYS]), 0, 1)

# fill passes: horizontal zigzag covering the logo, top to bottom
PASSES = []
ys = np.arange(y0 + 30, y1, 58)
for k, py in enumerate(ys):
    a, b = (x0 - 40, x1 + 40) if k % 2 == 0 else (x1 + 40, x0 - 40)
    PASSES.append(np.array([[a, py + R.normal(0, 6)], [b, py + 30 + R.normal(0, 6)]]))
CONTOURS = POLYS


def spray_lines(paths, prog, width, soft):
    """Coverage of soft spray lines drawn up to `prog` (0..1 over the concatenated paths)."""
    m = np.zeros((H // 2, W // 2), np.float32)
    total = sum(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)) for p in paths)
    left = prog * total
    for p in paths:
        seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
        for j, L in enumerate(seg):
            if left <= 0:
                break
            f = min(1.0, left / max(L, 1e-6))
            a, b = p[j], p[j] + (p[j + 1] - p[j]) * f
            cv2.line(m, tuple(np.round(a * 8).astype(int)), tuple(np.round(b * 8).astype(int)), 1.0,
                     max(1, int(width / 2)), cv2.LINE_AA, 4)
            left -= L
        if left <= 0:
            break
    m = cv2.GaussianBlur(m, (0, 0), soft / 2)
    return cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)


def tip_of(paths, prog):
    total = sum(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)) for p in paths)
    left = prog * total
    for p in paths:
        seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
        for j, L in enumerate(seg):
            if left <= L:
                return p[j] + (p[j + 1] - p[j]) * (left / max(L, 1e-6))
            left -= L
    return paths[-1][-1]


def overspray(centre, n, spread, seed, shape=(H, W)):
    r = np.random.default_rng(seed)
    m = np.zeros((shape[0] // 2, shape[1] // 2), np.float32)
    pts = centre + r.normal(0, spread, (n, 2))
    for p in pts:
        cv2.circle(m, (int(p[0] * 8), int(p[1] * 8)), int(r.uniform(2, 9)), float(r.uniform(0.4, 1)), -1, cv2.LINE_AA, 4)
    return cv2.resize(m, (shape[1], shape[0]))


SPECKS = np.clip(sum(overspray(np.array([R.uniform(x0, x1), R.uniform(y0, y1)]), 120, 120, 400 + k) for k in range(40)), 0, 1)
SPECKS *= (1 - np.clip(MASK * 4, 0, 1)) * 0.85

# drips: from the bottom edges of the piece, in the colour of the fade there (and some black)
DR = []
for pc in LOGO.pieces:
    p = POLYS[pc["outer"]]
    for a, b in zip(p, np.roll(p, -1, 0)):
        d = b - a
        if abs(d[1]) < 4 and np.linalg.norm(d) > 60 and a[1] > LOGO_C[1]:
            for s in np.sort(R.uniform(0.05, 0.95, int(np.linalg.norm(d) / 70))):
                q = a + d * s
                DR.append({"x": q[0], "y": q[1] + 4, "t0": T_LAND - 0.25 + R.uniform(0, 0.6), "v": R.uniform(120, 330),
                           "w": R.uniform(9, 17), "black": R.uniform() < 0.3})

# highlights: white strokes on the upper-left edges + sparkles
HL = []
for pc in LOGO.pieces:
    p = POLYS[pc["outer"]]
    for a, b in zip(p, np.roll(p, -1, 0)):
        d = b - a
        L = np.linalg.norm(d)
        nrm = np.array([d[1], -d[0]]) / (L + 1e-9)
        if L > 200 and (nrm[0] + nrm[1]) < -0.3:
            q0, q1 = a + d * 0.12 + nrm * -26, a + d * 0.42 + nrm * -26
            HL.append(np.array([q0, q1]))
SPARKS = [np.array([x0 + 60, y0 + 150]), np.array([x1 - 120, y0 + 60]), np.array([LOGO_C[0] + 40, y1 - 90])]

# ---------------------------------------------------------------- stencil type
TEXT_C = W / 2
A_BASE, P_BASE = y1 + 70 + 200, y1 + 70 + 200 + 64 + 70
astris, _ = K.line_letters("big-shoulders-stencil-display-900", "ASTRIS", 200, TEXT_C, A_BASE, 0.10)
prod, _ = K.line_letters("big-shoulders-stencil-display-800", "PRODUCTIONS", 70, TEXT_C, P_BASE, 0.62)
A_MASK = K.letters_mask(astris)
P_MASK = K.letters_mask(prod)
A_HALO = cv2.GaussianBlur(A_MASK, (0, 0), 9)
P_HALO = cv2.GaussianBlur(P_MASK, (0, 0), 6)
TX0, TX1 = TEXT_C - 900, TEXT_C + 900


def camera(t):
    dx = 7 * math.sin(t * 1.3) + 4 * math.sin(t * 2.9 + 1)
    dy = 5 * math.sin(t * 1.1 + 2) + 3 * math.sin(t * 3.7)
    rot = 0.18 * math.sin(t * 0.9)
    sh = 46 * C.pulse(t, T_LAND, 0.004, 0.25)
    sx, sy, sr = C.shake_offsets(t, 3)
    z = 1.0 + 0.045 * C.smoothstep(0, DUR, t) + 0.03 * C.pulse(t, T_LAND, 0.004, 0.18)
    return dx + sx * sh, dy + sy * sh, rot + sr * sh * 0.02, z


def frame(i):
    t = i / C.FPS
    flash = 1.0 * C.pulse(t, T_LAND + 0.04, 0.012, 0.07)
    flicker = 1.0 + 0.05 * math.sin(t * 47) * math.sin(t * 13)          # sodium lamp hum
    light = LIGHT0 * flicker if flash < 0.01 else lighting(flash) * flicker
    img = ALB * light
    paint = np.zeros((H, W), np.float32)
    pcol = np.zeros((H, W, 3), np.float32)

    def lay(cov, col):
        nonlocal paint, pcol
        cov = np.clip(cov, 0, 1)
        pcol = pcol * (1 - cov[..., None]) + np.asarray(col, np.float32) * cov[..., None]
        paint = np.maximum(paint, cov)

    # 3D block, then the rainbow-fade fill sprayed in passes
    fp = C.clamp((t - T_FILL0) / (T_FILL1 - T_FILL0))
    if fp > 0:
        cov = spray_lines(PASSES, fp, 120, 22)
        fillcov = cov * np.clip((6 - SDF) / 6, 0, 1)
        lay(BLOCK * np.clip(cov * 1.4, 0, 1) * (1 - MASK), K.rgb("#3b0f5e"))
        lay(fillcov, FADE)
        lay(SPECKS * np.clip(cov * 3, 0, 1) * 0.6, FADE)
    # outline
    lp = C.clamp((t - T_LINE0) / (T_LINE1 - T_LINE0))
    if lp > 0:
        oc = spray_lines(CONTOURS, lp, 22, 5)
        lay(oc, K.rgb("#0c0b10"))
    # highlights and sparkles
    hp = C.clamp((t - T_HI0) / (T_HI1 - T_HI0))
    if hp > 0:
        lay(spray_lines(HL, hp, 12, 3) * 0.95, K.rgb("#ffffff"))
        sp = np.zeros((H, W), np.float32)
        for k, c in enumerate(SPARKS):
            a = C.clamp(hp * 3 - k)
            if a > 0:
                for ang in (0, math.pi / 2):
                    dv = np.array([math.cos(ang), math.sin(ang)]) * 46 * a
                    cv2.line(sp, tuple(np.round((c - dv) * 16).astype(int)), tuple(np.round((c + dv) * 16).astype(int)), 1.0,
                             7, cv2.LINE_AA, 4)
                cv2.circle(sp, tuple(np.round(c * 16).astype(int)), int(16 * 9 * a), 1.0, -1, cv2.LINE_AA, 4)
        lay(cv2.GaussianBlur(sp, (0, 0), 1.5), K.rgb("#ffffff"))
    # drips crawl down the bricks
    if t > T_LAND - 0.3:
        dm = np.zeros((H, W), np.float32)
        dc = np.zeros((H, W, 3), np.float32)
        for d in DR:
            tk = t - d["t0"]
            if tk <= 0:
                continue
            L = d["v"] * (1 - math.exp(-tk / 1.1)) * 1.1 + 10
            col = K.rgb("#0c0b10") if d["black"] else FADE[int(min(H - 1, d["y"] - 10)), int(d["x"])]
            p0, p1 = (d["x"], d["y"]), (d["x"] + 2 * math.sin(d["y"]), d["y"] + L)
            cv2.line(dm, (int(p0[0] * 16), int(p0[1] * 16)), (int(p1[0] * 16), int(p1[1] * 16)), 1.0, int(d["w"] * 0.6), cv2.LINE_AA, 4)
            cv2.circle(dm, (int(p1[0] * 16), int(p1[1] * 16)), int(d["w"] * 0.55 * 16), 1.0, -1, cv2.LINE_AA, 4)
            cv2.line(dc, (int(p0[0] * 16), int(p0[1] * 16)), (int(p1[0] * 16), int(p1[1] * 16)), tuple(float(c) for c in col),
                     int(d["w"] * 0.6), cv2.LINE_AA, 4)
            cv2.circle(dc, (int(p1[0] * 16), int(p1[1] * 16)), int(d["w"] * 0.55 * 16), tuple(float(c) for c in col), -1, cv2.LINE_AA, 4)
        pcol = pcol * (1 - dm[..., None]) + dc
        paint = np.maximum(paint, dm)
    # splatter on the landing
    if t >= T_LAND:
        sc = C.clamp((t - T_LAND) / 0.06)
        splat = np.zeros((H, W), np.float32)
        rr = np.random.default_rng(77)
        for k in range(26):
            c = np.array([rr.uniform(x0 - 150, x1 + 150), rr.uniform(y0 - 100, y1 + 60)])
            if MASK[int(np.clip(c[1], 0, H - 1)), int(np.clip(c[0], 0, W - 1))] > 0.5:
                continue
            rad = rr.uniform(6, 26) * sc
            cv2.circle(splat, tuple(np.round(c * 16).astype(int)), int(rad * 16), 1.0, -1, cv2.LINE_AA, 4)
            for j in range(5):
                q = c + rr.normal(0, rad * 2.2, 2)
                cv2.circle(splat, tuple(np.round(q * 16).astype(int)), int(rr.uniform(2, 7) * sc * 16), 1.0, -1, cv2.LINE_AA, 4)
        lay(splat, FADE)
    # stencilled type: soft overspray halo, then the crisp letter
    for (mask, halo, t0, col) in ((A_MASK, A_HALO, T_ST1, K.rgb("#f4f1e8")), (P_MASK, P_HALO, T_ST2, K.rgb("#ffd21f"))):
        k = C.clamp((t - t0) / 0.28)
        if k > 0:
            wipe = np.clip(((xx - TX0) / (TX1 - TX0) - (k * 1.3 - 0.15)) / -0.08, 0, 1)
            lay(halo * 0.35 * wipe, col)
            lay(mask * wipe, col)
    # paint sits on the wall: textured by the bricks, lit by the same light
    tex = (0.84 + 0.22 * ROUGH)[..., None]
    lum = light.mean(axis=2, keepdims=True)
    plit = (0.42 + 0.85 * np.clip(lum, 0, 1.4)) * (0.88 + 0.12 * light / np.maximum(lum, 1e-3))
    img = img * (1 - paint[..., None]) + pcol * tex * plit * paint[..., None]
    # wet sheen near the ground
    img += (np.clip((yy - H * 0.78) / (H * 0.22), 0, 1) ** 2)[..., None] * K.rgb("#ffb070") * 0.05
    dx, dy, rot, z = camera(t)
    img = C.warp(img, dx, dy, rot, z * 1.03, border=cv2.BORDER_REFLECT101)
    if flash > 0.02:
        img = img + flash * 0.25
    return POST.finish(img, i, bloom=0.35 + 0.6 * flash, threshold=0.78)


# ---------------------------------------------------------------- sound
def audio():
    m = S.Mix(DUR)
    city = S.sos(S.noise(DUR, "brown", 301), "lowpass", 220) * 0.5 + S.sos(S.noise(DUR, "pink", 302), "bandpass", [300, 1200]) * 0.08
    m.add(city / np.max(np.abs(city)), 0.0, gain=0.08, send=0.1)
    hum = np.sin(2 * np.pi * 120 * S.tt(DUR)) * 0.02 + np.sin(2 * np.pi * 240 * S.tt(DUR)) * 0.01
    m.add(hum, 0.0, gain=0.5, pan=-0.5, send=0.0)
    m.add(X.can_rattle(4, 9.5, seed=303), 0.0, gain=0.55, pan=0.15, send=0.2)
    # fill passes: one hiss per pass, panning with the arm
    n = len(PASSES)
    dt = (T_FILL1 - T_FILL0) / n
    for k in range(n):
        x = X.spray(dt * 0.95, seed=310 + k)
        m.add(x, T_FILL0 + k * dt, gain=0.45, pan=0.5 if k % 2 == 0 else -0.5, send=0.15)
    # outline: tighter bursts, highlights: short psst
    for k in range(6):
        m.add(X.spray(0.1, seed=330 + k, colour=1.4), T_LINE0 + k * (T_LINE1 - T_LINE0) / 6, gain=0.5, pan=(-1) ** k * 0.3, send=0.15)
    for k in range(3):
        m.add(X.spray(0.07, seed=340 + k, colour=1.6), T_HI0 + k * 0.08, gain=0.45, pan=0.2, send=0.2)
    # the landing: flash click, deep thump, bass drop, wet splats
    click = S.sos(S.noise(0.05, "white", 350), "highpass", 3000) * S.env_exp(0.05, 0.0005, 0.006)
    m.add(click, T_LAND + 0.03, gain=0.6, pan=0.3, send=0.3)
    m.add(S.impact(2.2, weight=1.2, bright=0.6, metal=0.2, seed=351, sub_f=(70, 34)), T_LAND, gain=0.75, send=0.25)
    m.add(X.bass_drop(1.4, 95, 32), T_LAND, gain=0.55, send=0.0)
    for k in range(5):
        m.add(X.paper_slap(360 + k, 0.6), T_LAND + 0.02 + k * 0.03, gain=0.18, pan=float(R.uniform(-0.6, 0.6)), send=0.2)
    # stencils
    m.add(X.spray(0.32, seed=370), T_ST1, gain=0.55, pan=-0.1, send=0.2)
    m.add(X.spray(0.28, seed=371, colour=1.2), T_ST2, gain=0.45, pan=0.1, send=0.2)
    m.add(X.can_rattle(2, 10, seed=372), T_ST2 + 0.55, gain=0.25, pan=0.4, send=0.25)
    mix = m.master(ir_seconds=1.6, wet=0.7, peak_db=-1.5, tail_fade=0.12)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [4, 14, 22, 30, 38, 46, 52, 55, 56, 60, 66, 75, 90, 119], tag="ident03")
