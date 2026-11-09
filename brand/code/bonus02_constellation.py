"""
ASTRIS PRODUCTIONS - Bonus 02: CONSTELLATION (7.0 s)

"Astris" - of the stars. A deep, quiet night sky full of twinkling stars. One by one, bright stars ignite at
the logo's corners, each with a glassy note climbing a pentatonic scale; fine lines of light connect them like
a star chart, and the film strip's sprocket holes light up as a row of tiny stars. A rainbow aurora rises behind,
a shimmer of rainbow light sweeps across the constellation, and the type appears as starlight beneath.
Matches banner/profile set 4 ("of the stars").
Sound: glass pings, a soft choir-like pad, sparkles, a shimmer sweep and a warm closing chord.
"""
import math

import numpy as np

import common as C
import kit as K
import sound as S
import sfx as X

cv2 = C.cv2
NAME = "astris-bonus-02"
DUR = 7.0
FPS = C.FPS
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=2201, grain=0.018, vignette=0.36, vig_inner=0.3, grain_size=1.0, grain_floor=0.2)
STARLIGHT = K.rgb("#eef1ff")
LINE_COL = K.rgb("#cdd8ff")

lock = K.Lockup2(LOGO, logo_h=760, lines=[("syncopate-700", "ASTRIS", 150, 0.32, None),
                                            ("montserrat-500", "PRODUCTIONS", 50, 0.0, 1.0)],
                 gaps=(170, 62), centre=(W / 2, H / 2 - 10))
T_STAR0, T_STAR_GAP = 0.95, 0.16
T_LINES0, T_SEG = 1.55, 0.2
T_HOLES0, T_HOLES1 = 2.75, 3.55
T_AUR0, T_AUR1 = 2.6, 4.4
T_SWEEP0, T_SWEEP1 = 3.75, 4.65
T_TXT0, T_PROD0 = 4.35, 5.0
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
yh, xh = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32)

# ------------------------------------------------------------------------------------------------
# the constellation: corner stars (+ mid-edge stars on long edges), edges in drawing order, hole stars
# ------------------------------------------------------------------------------------------------
POLYS = lock.logo_polys()
MAIN = [q for q in POLYS if abs(cv2.contourArea(q.astype(np.float32))) > 20000]
HOLES = [q for q in POLYS if abs(cv2.contourArea(q.astype(np.float32))) <= 20000]
STARS, EDGES = [], []
for q in sorted(MAIN, key=lambda q: q[:, 0].min()):
    ap = cv2.approxPolyDP(q.astype(np.float32).reshape(-1, 1, 2), 8.0, True).reshape(-1, 2)
    ring = []
    for j in range(len(ap)):
        a, b = ap[j], ap[(j + 1) % len(ap)]
        ring.append(a)
        if np.linalg.norm(b - a) > 520:
            ring.append(a + (b - a) * 0.5)
    base = len(STARS)
    STARS += ring
    EDGES += [(base + j, base + (j + 1) % len(ring)) for j in range(len(ring))]
STARS = np.array(STARS, np.float32)
# ignition order: sweep left to right, top to bottom
ORDER = np.argsort(STARS[:, 0] * 1.0 + STARS[:, 1] * 0.35)
T_IGN = np.zeros(len(STARS))
T_IGN[ORDER] = T_STAR0 + np.arange(len(STARS)) * T_STAR_GAP
HOLE_C = np.array(sorted([q.mean(0) for q in HOLES], key=lambda p: -p[1]), np.float32)     # bottom to top
LOGO_M = C.poly_mask_ss(POLYS, ss=2)

# ------------------------------------------------------------------------------------------------
# sky: gradient + nebula + a static field of faint stars + a set of twinkling stars
# ------------------------------------------------------------------------------------------------
def build_sky(seed=2202):
    r = np.random.default_rng(seed)
    v = yy / H
    img = K.rgb("#03041a") * (1 - v[..., None]) + K.rgb("#0d0a30") * v[..., None]
    neb = cv2.resize(K.fbm(H // 8, W // 8, seed, 6), (W, H), interpolation=cv2.INTER_CUBIC)
    neb2 = cv2.resize(K.fbm(H // 8, W // 8, seed + 1, 6), (W, H), interpolation=cv2.INTER_CUBIC)
    img = img + (np.clip(neb - 0.42, 0, 1) ** 1.6)[..., None] * K.rgb("#3b2a8f") * 0.75
    img = img + (np.clip(neb2 - 0.55, 0, 1) ** 1.8)[..., None] * K.rgb("#8a2a7a") * 0.45
    st8 = np.zeros((H, W), np.uint8)
    for _ in range(5200):
        x, y = r.uniform(0, W), r.uniform(0, H)
        b = r.uniform(0.1, 0.7) ** 2
        cv2.circle(st8, (int(x * 4), int(y * 4)), int(4 * (0.7 + 1.1 * b)), int(b * 255), -1, cv2.LINE_AA, 2)
    st = st8.astype(np.float32) / 255
    img = img + (st + cv2.GaussianBlur(st, (0, 0), 2.5) * 0.5)[..., None] * K.rgb("#dfe6ff")
    return img.astype(np.float32)


SKY = build_sky()
TW = np.random.default_rng(2203).uniform(0, 1, (700, 6)).astype(np.float32)   # x, y, size, bright, freq, phase


def twinkles(t):
    st8 = np.zeros((H, W), np.uint8)
    for x, y, s, b, f, ph in TW:
        k = (0.55 + 0.45 * math.sin(t * (1.5 + 5 * f) + ph * 6.283)) * (0.25 + 0.75 * b * b)
        cv2.circle(st8, (int(x * W * 4), int(y * H * 4)), int(4 * (1.0 + 2.2 * s * s)), int(k * 255), -1, cv2.LINE_AA, 2)
    st = st8.astype(np.float32) / 255
    return st + cv2.GaussianBlur(st, (0, 0), 3.0) * 0.7


# ------------------------------------------------------------------------------------------------
# aurora (half resolution): rainbow curtains with drifting rays and a bright, waving lower lip
# ------------------------------------------------------------------------------------------------
AUR_R = np.random.default_rng(2204)
RIBBONS = []
for (y_l, y_r, amp, waves, height, k, hue0, span) in [(0.50, 0.41, 0.035, 2.1, 0.17, 0.42, 0.95, 0.85),
                                                      (0.95, 0.89, 0.025, 3.0, 0.06, 0.16, 0.30, 0.75)]:
    n = W * 2
    layers = []
    for scale, wt in ((3, 0.45), (9, 0.35), (40, 0.35), (160, 0.4)):
        g = AUR_R.standard_normal(n // scale + 4).astype(np.float32)
        layers.append((scale, wt, g))
    mod = AUR_R.uniform(0, 1, n // 300 + 4).astype(np.float32)
    RIBBONS.append(dict(y_l=y_l, y_r=y_r, amp=amp, waves=waves, height=height, k=k, hue0=hue0, span=span,
                        layers=layers, mod=mod, ph=AUR_R.uniform(0, 6.283, 3)))


def aurora(t, strength):
    h, w = H // 2, W // 2
    out = np.zeros((h, w, 3), np.float32)
    x1 = np.arange(w, dtype=np.float32)
    for rb in RIBBONS:
        xn = x1 / w
        edge = h * (rb["y_l"] + (rb["y_r"] - rb["y_l"]) * xn + rb["amp"] * np.sin(xn * math.pi * rb["waves"] + rb["ph"][0] + 0.35 * t)
                    + rb["amp"] * 0.35 * np.sin(xn * math.pi * rb["waves"] * 2.7 + rb["ph"][1] - 0.5 * t))
        edge += h * 0.06 * (1 - strength)                          # rises into place as it fades in
        rays = np.zeros(w, np.float32)
        for scale, wt, g in rb["layers"]:
            xs = (x1 * 2 + 30 * t * (1 + 0.3 * wt)) / scale
            rays += np.interp(xs, np.arange(len(g)), g) * wt
        rays = np.clip(0.55 + 0.35 * rays, 0.05, 1.3)
        rm = np.clip(0.35 + 0.75 * np.interp((x1 * 2 + 12 * t) / 300, np.arange(len(rb["mod"])), rb["mod"]), 0, 1)
        d = edge[None, :] - yh
        dp = np.clip(d, 0, None)
        height = rb["height"] * h
        prof = np.exp(-dp / height) * (1 - np.exp(-dp / 2.5)) + np.exp(-((d - 7) / 8) ** 2) * 1.6 \
            + np.exp(-np.clip(-d, 0, None) / 3) * (d <= 0) * 0.5
        sl = np.clip(xh + d * 0.06, 0, w - 1).astype(np.int32)
        a = prof * (rays * rm)[sl] * rb["k"]
        hue = C.hue_wheel(rb["hue0"] + xh / w * rb["span"] + dp / height * 0.10 + 0.02 * t)
        out += hue * a[..., None]
    out = out + cv2.GaussianBlur(out, (0, 0), 7) * 0.5 + cv2.GaussianBlur(out, (0, 0), 25) * 0.22
    return cv2.resize(out * strength, (W, H), interpolation=cv2.INTER_LINEAR)


# ------------------------------------------------------------------------------------------------
# drawing helpers
# ------------------------------------------------------------------------------------------------
def bigblur(m, sigma, f=4):
    """A wide Gaussian done at 1/f resolution (identical to the eye, a fraction of the cost)."""
    small = cv2.resize(m, (W // f, H // f), interpolation=cv2.INTER_AREA)
    return cv2.resize(cv2.GaussianBlur(small, (0, 0), sigma / f), (W, H), interpolation=cv2.INTER_LINEAR)


def lowres(fn, f=4):
    """Evaluate a smooth per-pixel colour field at 1/f resolution and scale it up."""
    ys, xs = np.mgrid[0:H // f, 0:W // f].astype(np.float32) * f
    return cv2.resize(fn(xs, ys), (W, H), interpolation=cv2.INTER_LINEAR)


def u8(v):
    """Intensity (0..2) as a value for the 8-bit anti-aliased drawing layers."""
    return int(np.clip(v / 2.0, 0, 1) * 255)


def f32(layer):
    return layer.astype(np.float32) * (2.0 / 255)


def star_flare(layer, spikes, p, r, k):
    """Star core + 4-point spikes, drawn anti-aliased into uint8 layers (255 = intensity 2.0)."""
    cv2.circle(layer, (int(p[0] * 16), int(p[1] * 16)), max(1, int(16 * r)), u8(k), -1, cv2.LINE_AA, 4)
    for a, ln in ((0.0, 5.5), (math.pi / 2, 5.5), (math.pi / 4, 2.4), (-math.pi / 4, 2.4)):
        dv = np.array([math.cos(a), math.sin(a)]) * r * ln * (0.6 + 0.4 * min(k, 1.6))
        cv2.line(spikes, tuple(np.round((p - dv) * 16).astype(int)), tuple(np.round((p + dv) * 16).astype(int)),
                 u8(k * 0.6), 2, cv2.LINE_AA, 4)


def shooting_star(k):
    """A meteor streaking down-left across the upper sky; k in 0..1 over its flight."""
    p0, p1 = np.array([2900.0, 180.0]), np.array([1650.0, 760.0])
    head = p0 + (p1 - p0) * C.expo_out(k, 1.5)
    tail = head - (p1 - p0) * 0.28 * (1 - 0.6 * k)
    fade = math.sin(math.pi * min(1.0, k * 1.05))
    st8 = np.zeros((H, W), np.uint8)
    n = 24
    for j in range(n):
        a = tail + (head - tail) * j / n
        b = tail + (head - tail) * (j + 1) / n
        cv2.line(st8, tuple(np.round(a * 16).astype(int)), tuple(np.round(b * 16).astype(int)), int(255 * ((j + 1) / n) ** 2), 3, cv2.LINE_AA, 4)
    cv2.circle(st8, tuple(np.round(head * 16).astype(int)), 16 * 4, 255, -1, cv2.LINE_AA, 4)
    st = st8.astype(np.float32) / 255
    return (st[..., None] * 1.2 + cv2.GaussianBlur(st, (0, 0), 5)[..., None] * K.rgb("#bcd0ff")) * fade


def frame(i):
    t = i / FPS
    img = SKY.copy()
    img += twinkles(t)[..., None] * K.rgb("#e8eeff")
    a_str = C.smoothstep(T_AUR0, T_AUR1, t)
    if a_str > 0:
        img += aurora(t, a_str)
    # a pool of night behind the type so it reads cleanly over the aurora
    if t > T_TXT0 - 0.3:
        img *= (1 - 0.38 * C.smoothstep(T_TXT0 - 0.3, T_TXT0 + 0.9, t) * POOL)[..., None]
    # a shooting star early on
    ss = C.clamp((t - 0.30) / 0.42)
    if 0 < ss < 1:
        img += shooting_star(ss)
    # shimmer sweep: a diagonal band of rainbow light crossing the constellation
    sw = C.clamp((t - T_SWEEP0) / (T_SWEEP1 - T_SWEEP0))
    band = None
    if 0 < sw < 1:
        off = C.expo_in_out(sw, 2.5) * 2000
        band = lowres(lambda x_, y_: np.exp(-(((x_ - 1250) + (y_ - 400) * 0.55 - off) / 170) ** 2))
    # the shape glows faintly once it's connected, then keeps a soft iridescent shimmer
    body = C.smoothstep(T_LINES0 + 1.2, T_SWEEP0 + 0.4, t)
    if body > 0:
        irid = lowres(lambda x_, y_: C.hue_wheel((x_ * 0.00025 + y_ * 0.00018 - 0.08 * t) % 1.0))
        tint = K.rgb("#8fa2ff") * 0.6 + irid * 0.4 * C.smoothstep(T_SWEEP0, T_SWEEP1, t)
        img += (LOGO_M * 0.085 * body)[..., None] * tint
        img += (LOGO_GLOW * 0.10 * body)[..., None] * K.rgb("#7f8fff")
    # connecting lines, drawn segment by segment with a bright travelling head
    ln8 = np.zeros((H, W), np.uint8)
    heads = []
    for e, (a, b) in enumerate(EDGES):
        k = C.clamp((t - T_LINES0 - e * T_SEG * 0.8) / T_SEG)
        if k <= 0:
            continue
        pa, pb = STARS[a], STARS[b]
        pe = pa + (pb - pa) * C.expo_out(k, 3)
        cv2.line(ln8, tuple(np.round(pa * 16).astype(int)), tuple(np.round(pe * 16).astype(int)), 255, 3, cv2.LINE_AA, 4)
        if k < 1:
            heads.append(pe)
    ln = ln8.astype(np.float32) * (0.85 / 255)
    sp = np.zeros((H, W), np.uint8)
    spk = np.zeros((H, W), np.uint8)
    for p in heads:
        star_flare(sp, spk, p, 5, 1.2)
    # the corner stars ignite with a flare, then twinkle gently
    for j, p in enumerate(STARS):
        dt = t - T_IGN[j]
        if dt <= 0:
            continue
        flare = 1.0 + 1.4 * math.exp(-dt / 0.18) * min(1.0, dt / 0.04)
        tw = 1.0 + 0.12 * math.sin(t * 3.1 + j * 1.7)
        star_flare(sp, spk, p, 11, min(1.0, dt / 0.06) * flare * tw)
    # sprocket holes: a run of tiny stars climbing the strip
    for j, p in enumerate(HOLE_C):
        th = T_HOLES0 + (T_HOLES1 - T_HOLES0) * j / max(1, len(HOLE_C) - 1)
        dt = t - th
        if dt > 0:
            k = min(1.0, dt / 0.05) * (1 + 1.2 * math.exp(-dt / 0.15)) * (0.85 + 0.15 * math.sin(t * 4 + j))
            cv2.circle(sp, (int(p[0] * 16), int(p[1] * 16)), int(16 * 5.5), u8(k * 0.9), -1, cv2.LINE_AA, 4)
    sp, spk = f32(sp), f32(spk)
    ln6 = cv2.GaussianBlur(ln, (0, 0), 4)
    lines_rgb = (ln[..., None] * LINE_COL + ln6[..., None] * K.rgb("#8fa8ff") * 0.9
                 + bigblur(ln, 16)[..., None] * K.rgb("#6f7fff") * 0.35)
    stars_rgb = (sp[..., None] * 1.3 + cv2.GaussianBlur(sp, (0, 0), 6)[..., None] * K.rgb("#cfd9ff") * 1.6
                 + bigblur(sp, 24)[..., None] * K.rgb("#8f9fff") * 0.8
                 + cv2.GaussianBlur(spk, (0, 0), 1.0)[..., None] * K.rgb("#e8eeff") * 0.9)
    lit = lines_rgb + stars_rgb
    if band is not None:
        lit = lit * (1 + band[..., None] * 1.2) + (band * (LOGO_M * 0.35 + ln6 * 2.0))[..., None] * HUE_SWEEP
    img += lit
    # the type, as starlight
    if t >= T_TXT0:
        letters = lock.line(0)
        al = [C.smoothstep(0, 1, (t - T_TXT0 - k * 0.08) / 0.32) for k in range(len(letters))]
        am = K.letters_mask(letters, alpha=al)
        img += (cv2.GaussianBlur(am, (0, 0), 10) * 0.35 + bigblur(am, 30) * 0.2)[..., None] * K.rgb("#9fb0ff")
        img = K.comp(img, am, STARLIGHT)
        sk = np.zeros((H, W), np.uint8)
        sks = np.zeros((H, W), np.uint8)
        for k, L in enumerate(letters):
            dt = t - T_TXT0 - k * 0.08
            if 0 < dt < 0.6:
                allp = np.concatenate(L["polys"])
                p = np.array([allp[:, 0].max() - 10, allp[:, 1].min() + 6])
                star_flare(sk, sks, p, 6, 1.4 * math.sin(math.pi * dt / 0.6))
        sk, sks = f32(sk), f32(sks)
        img += (sk[..., None] + cv2.GaussianBlur(sk, (0, 0), 8)[..., None] * 1.2 + cv2.GaussianBlur(sks, (0, 0), 1)[..., None]) * K.rgb("#eef2ff")
    if t >= T_PROD0:
        pl = lock.line(1)
        al = [C.smoothstep(0, 1, (t - T_PROD0 - k * 0.03) / 0.35) for k in range(len(pl))]
        img = K.comp(img, K.letters_mask(pl, alpha=al), K.rgb("#c6cff5"))
    z = 1.035 - 0.035 * C.smoothstep(0, DUR, t)
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0.0, z)
    img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    return POST.finish(img, i, bloom=0.3, threshold=0.85)


def _pool():
    m = K.letters_mask(lock.line(0) + lock.line(1))
    m = cv2.dilate(m, np.ones((81, 81), np.uint8))
    return np.clip(bigblur(m, 110) * 1.5, 0, 1)


POOL = _pool()
LOGO_GLOW = bigblur(LOGO_M, 40)
HUE_SWEEP = lowres(lambda x_, y_: C.hue_wheel((x_ * 0.0004 - y_ * 0.0002 + 0.3) % 1.0))


# ------------------------------------------------------------------------------------------------
# sound
# ------------------------------------------------------------------------------------------------
def audio():
    m = S.Mix(DUR)
    d3, a3, d4, fs4, a4, e5 = (S.midi(n) for n in (50, 57, 62, 66, 69, 76))
    m.add(S.whoosh(0.7, peak=0.4, f_lo=1500, f_hi=7000, q=1.4, pan_from=0.6, pan_to=-0.2, seed=2209), 0.28, gain=0.07, send=0.6)
    m.add(S.pad([d3, a3, d4, fs4, a4], DUR, attack=2.2, release=1.6, cutoff=(300, 1700), level=1.0, seed=2210), 0.0, gain=0.22, send=0.5)
    penta = [74, 76, 78, 81, 83, 86, 88, 90, 93, 95, 98]           # D major pentatonic, climbing
    for rank, j in enumerate(ORDER):
        f = S.midi(penta[min(rank, len(penta) - 1)])
        pan = float(np.clip((STARS[j][0] - W / 2) / (W / 2), -1, 1)) * 0.7
        m.add(X.glass_ping(f, 2.4), T_IGN[j], gain=0.2, pan=pan, send=0.6)
        m.add(X.glass_ping(f * 2, 1.2), T_IGN[j] + 0.01, gain=0.05, pan=pan, send=0.6)
    m.add(S.shimmer(T_LINES0 + len(EDGES) * T_SEG * 0.8 - T_LINES0 + 0.6, root=1500, density=22, level=1.0, seed=2211, rise=0.3),
          T_LINES0, gain=0.10, send=0.6)
    for j in range(len(HOLE_C)):
        th = T_HOLES0 + (T_HOLES1 - T_HOLES0) * j / max(1, len(HOLE_C) - 1)
        m.add(S.tick(2600 + 90 * j, 0.06, 1.0, 0.2, 2220 + j, 0.4), th, gain=0.05, pan=-0.2 + 0.02 * j, send=0.5)
    m.add(S.reverse_swell(0.9, 1.0, 2230, 2600), T_SWEEP0 - 0.5, gain=0.18, send=0.4)
    m.add(S.whoosh(1.1, peak=0.55, f_lo=600, f_hi=6000, q=0.8, pan_from=-0.7, pan_to=0.7, seed=2231), T_SWEEP0, gain=0.12, send=0.5)
    m.add(S.shimmer(1.6, root=2000, density=30, level=1.0, seed=2232, rise=0.2), T_SWEEP0 + 0.1, gain=0.14, send=0.6)
    m.add(S.sting([d4, a4, S.midi(74), S.midi(78), S.midi(81)], 3.2, level=1.0, bright=0.55, seed=2233), T_TXT0, gain=0.3, send=0.55)
    m.add(S.sub_build(1.2, 30, 46, 1.0, 2.0), T_TXT0 - 1.2, gain=0.12, send=0.0)
    m.add(S.chime(S.midi(86), 3.0, 1.0, 2.4), T_PROD0, gain=0.12, pan=0.2, send=0.6)
    mix = m.master(ir_seconds=3.2, wet=0.85, peak_db=-1.5, tail_fade=0.6)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [6, 26, 40, 50, 64, 76, 88, 96, 104, 112, 128, 167], tag="bonus02")
