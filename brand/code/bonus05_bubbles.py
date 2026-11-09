"""
ASTRIS PRODUCTIONS - Bonus 05: SOAP BUBBLES (6.5 s)

Dusk-dark air with soft bokeh. Soap bubbles drift up and across, wobbling, their thin films swirling with real
interference colours (magenta, gold, green, blue bands that move as the film drains). They find each other in
the middle and merge - plip, plip - into one big bubble with the logo floating inside it. It pops: the film
tears away in a blink, a ring of droplets sprays out, and the logo is left behind - pearly white, with a soap-film
sheen - with ASTRIS PRODUCTIONS beneath. A few stray bubbles keep drifting through the hold.
Sound: airy pad, kalimba notes, a pentatonic run of bloops as bubbles merge, a crisp pop and droplet sparkle,
and a warm chord.
"""
import math

import numpy as np

import common as C
import kit as K
import sound as S
import sfx as X

cv2 = C.cv2
NAME = "astris-bonus-05"
DUR = 6.5
FPS = C.FPS
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=2501, grain=0.016, vignette=0.34, vig_inner=0.3, grain_size=1.0, grain_floor=0.2)
lock = K.Lockup2(LOGO, logo_h=620, lines=[("fredoka-600", "ASTRIS", 165, 0.16, None),
                                            ("montserrat-500", "PRODUCTIONS", 48, 0.0, 1.0)],
                 gaps=(150, 64), centre=(W / 2, H / 2 + 20))
LC = lock.logo_c.astype(np.float64)
T_POP = 3.55
T_TXT, T_PROD = 3.95, 4.40
R_BIG = 660.0
RNG = np.random.default_rng(2502)
NOISE = K.fbm(256, 256, 2503, 6, aspect=1.0).astype(np.float32)
NOISE = (NOISE - NOISE.min()) / (NOISE.max() - NOISE.min())


# ------------------------------------------------------------------------------------------------
# thin-film interference: reflected colour for film thickness d (nm) seen at angle cos_t
# ------------------------------------------------------------------------------------------------
LAMBDA = np.array([650, 610, 570, 540, 510, 480, 450], np.float32)
TO_RGB = np.array([[1.00, 0.05, 0.00], [0.95, 0.35, 0.00], [0.55, 0.85, 0.00], [0.15, 1.00, 0.10],
                   [0.00, 0.75, 0.55], [0.00, 0.30, 1.00], [0.35, 0.00, 1.00]], np.float32)
TO_RGB /= TO_RGB.sum(0, keepdims=True)


def film_colour(d, cos_t, n=1.33):
    ct = np.sqrt(np.clip(1 - (1 - cos_t ** 2) / (n * n), 0, 1))
    opd = 2 * n * d * ct
    I = np.sin(math.pi * opd[..., None] / LAMBDA) ** 2          # constructive at OPD = (m + 1/2) lambda
    return (I @ TO_RGB) * 1.15


# ------------------------------------------------------------------------------------------------
# bubbles
# ------------------------------------------------------------------------------------------------
class Bubble:
    def __init__(self, k, merge):
        r = np.random.default_rng(2600 + k)
        self.k = k
        self.R0 = r.uniform(70, 200)
        side = r.choice(["bottom", "left", "right"], p=[0.6, 0.2, 0.2])
        if side == "bottom":
            self.p0 = np.array([r.uniform(0.1, 0.9) * W, H + self.R0 + r.uniform(0, 200)])
        elif side == "left":
            self.p0 = np.array([-self.R0 - 50, r.uniform(0.45, 0.95) * H])
        else:
            self.p0 = np.array([W + self.R0 + 50, r.uniform(0.45, 0.95) * H])
        self.ts = r.uniform(0.0, 1.4)
        self.merge = merge
        if merge:
            self.tm = r.uniform(2.15, 3.3)
            a = r.uniform(0, 2 * math.pi)
            self.p1 = LC + np.array([math.cos(a), math.sin(a)]) * r.uniform(150, 420)
        else:
            # drifters keep to the sides of the frame, so the lockup stays clear
            sx = r.choice([r.uniform(0.03, 0.24), r.uniform(0.76, 0.97)])
            self.p0[0] = sx * W if side == "bottom" else self.p0[0]
            self.tm = self.ts + r.uniform(4.5, 6.5)
            self.p1 = np.array([np.clip(sx + r.uniform(-0.06, 0.06), 0.02, 0.98) * W, -self.R0 - 100])
        self.mid = (self.p0 + self.p1) / 2 + np.array([r.uniform(-500, 500) if merge else r.uniform(-120, 120), r.uniform(-300, 100)])
        self.wob = r.uniform(0.6, 1.6, 3)
        self.ph = r.uniform(0, 6.28, 4)
        self.spin = r.uniform(-0.6, 0.6)
        self.thick = r.uniform(240, 400)

    def state(self, t):
        """(centre, radius) or None."""
        if t < self.ts:
            return None
        s = C.clamp((t - self.ts) / (self.tm - self.ts))
        e = s * s * (3 - 2 * s) if self.merge else s
        a = (1 - e) ** 2 * self.p0 + 2 * (1 - e) * e * self.mid + e * e * self.p1
        a = a + np.array([30 * math.sin(t * self.wob[0] + self.ph[0]), 22 * math.sin(t * self.wob[1] + self.ph[1])])
        R = self.R0
        if self.merge and t > self.tm:
            # absorbed: shrinks into the big bubble while sliding to its centre
            k = C.clamp((t - self.tm) / 0.14)
            if k >= 1:
                return None
            a = a + (LC - a) * k * 0.4
            R = self.R0 * (1 - k)
        if not self.merge and s >= 1:
            return None
        return a, R


BUBBLES = [Bubble(k, merge=k < 15) for k in range(23)]
MERGERS = sorted([b for b in BUBBLES if b.merge], key=lambda b: b.tm)
LATE = []                                       # a few new bubbles drifting up through the hold
for k in range(5):
    b = Bubble(100 + k, merge=False)
    b.ts = T_POP + 0.3 + k * 0.45
    b.tm = b.ts + 3.6
    b.R0 *= 0.7
    LATE.append(b)


def big_radius(t):
    acc = 0.0
    for b in MERGERS:
        k = C.clamp((t - b.tm) / 0.14)
        acc += (b.R0 * 2.1) ** 2 * k
    base = R_BIG * C.smoothstep(2.0, 3.45, t)
    return min(R_BIG, math.sqrt(acc + (base * 0.55) ** 2))


def draw_bubble(img, c, R, t, seed, thick, spin, alpha=1.0, hole=None):
    """Composite one soap bubble onto img (in place) at centre c with radius R."""
    if R < 2:
        return
    x0, x1 = int(max(0, c[0] - R - 3)), int(min(W, c[0] + R + 4))
    y0, y1 = int(max(0, c[1] - R - 3)), int(min(H, c[1] + R + 4))
    if x1 <= x0 or y1 <= y0:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    u, v = (xs - c[0]) / R, (ys - c[1]) / R
    rr = np.sqrt(u * u + v * v)
    cover = np.clip((1 - rr) * R / 1.3 + 0.5, 0, 1)
    if hole is not None:
        cover = cover * hole(xs, ys)
    if cover.max() <= 0:
        return
    nz = np.sqrt(np.clip(1 - rr * rr, 0, 1))
    # film thickness: swirling, draining toward the bottom
    a = spin * t + seed
    ca, sa = math.cos(a), math.sin(a)
    su, sv = u * ca - v * sa, u * sa + v * ca
    nx = ((su * 0.7 + 0.5 + 0.13 * math.sin(t * 0.9 + seed)) * 255).astype(np.float32)
    ny = ((sv * 0.7 + 0.5 + 0.11 * math.cos(t * 0.7 + seed)) * 255).astype(np.float32)
    sw = cv2.remap(NOISE, nx, ny, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    d = 300 + thick * 1.2 * sw + 170 * np.clip(v, -1, 1) + 60 * np.sin(su * 3.0 + t)       # 2nd-4th order: vivid bands
    col = film_colour(d, nz)
    fres = 0.04 + 0.96 * (1 - nz) ** 5
    env = 0.55 + 0.45 * np.clip(-v, -1, 1)                    # the sky above reflects brighter than the ground
    refl = col * (0.42 + 0.9 * fres)[..., None] * env[..., None] * 1.25
    # window highlights
    h1 = np.exp(-(((u + 0.38) / 0.15) ** 4 + ((v + 0.42) / 0.10) ** 4)) * 0.85
    h2 = np.exp(-(((u - 0.45) / 0.10) ** 2 + ((v - 0.50) / 0.07) ** 2)) * 0.7
    rim = np.exp(-((1 - rr) * R / 3.0) ** 2) * 0.35
    patch = img[y0:y1, x0:x1]
    a3 = (cover * alpha)[..., None]
    patch[:] = patch * (1 - a3 * (0.10 + 0.25 * fres[..., None])) + (refl + (h1 + h2 + rim)[..., None]) * a3


# ------------------------------------------------------------------------------------------------
# backdrop and the logo
# ------------------------------------------------------------------------------------------------
def build_bg(seed=2504):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = yy / H
    img = K.rgb("#071624") * (1 - v[..., None]) + K.rgb("#1a0f33") * v[..., None]
    r = np.random.default_rng(seed)
    bok = np.zeros((H, W, 3), np.float32)
    for _ in range(46):
        c = (int(r.uniform(0, W)), int(r.uniform(0, H)))
        rad = int(r.uniform(30, 150))
        col = K.rgb(r.choice(["#ff8ad8", "#7fe8ff", "#b79bff", "#ffd28a", "#9dffcf"]))
        m = np.zeros((H, W), np.uint8)
        cv2.circle(m, c, rad, 255, -1, cv2.LINE_AA)
        bok += (m.astype(np.float32) / 255)[..., None] * col * r.uniform(0.03, 0.10)
    bok = cv2.GaussianBlur(bok, (0, 0), 6)
    return (img + bok).astype(np.float32)


BG = build_bg()


def _logo():
    m = C.poly_mask_ss(lock.logo_polys(), ss=2)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    n = K.bevel_normals(m, 22, 45)
    u, v = (xx - LC[0]) / 400, (yy - LC[1]) / 400
    sw = cv2.resize(NOISE, (W, H))
    d = 520 * (0.6 + 0.8 * sw) + 120 * v
    sheen = film_colour(d.astype(np.float32), np.clip(n[..., 2], 0.2, 1))
    L = np.array([-0.4, -0.75, 0.55], np.float32)
    L /= np.linalg.norm(L)
    dif = np.clip((n * L).sum(-1), 0, 1)
    body = (0.80 + 0.22 * dif)[..., None] * K.rgb("#fbf8ff") + sheen * 0.32
    return m, body.astype(np.float32)


LOGO_M, LOGO_RGB = _logo()
GLOW = cv2.resize(cv2.GaussianBlur(cv2.resize(LOGO_M, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), 10), (W, H))
ASTRIS_L, PROD_L = lock.line(0), lock.line(1)
DROPS = RNG.uniform(0, 1, (170, 5))


def frame(i):
    t = i / FPS
    img = BG.copy()
    img = np.roll(img, int(-8 * t), axis=1)
    # the logo: floating inside the big bubble, then revealed by the pop
    Rb = big_radius(t)
    pop = C.clamp((t - T_POP) / 0.09)
    reveal = 0.0 if t < 2.4 else (0.55 * C.smoothstep(2.4, T_POP, t) if t < T_POP else 1.0)
    if reveal > 0:
        s = 1.0
        if t > T_POP:
            s = 1 + 0.035 * math.exp(-(t - T_POP) / 0.18) * math.sin((t - T_POP) * 26)
        lm, lrgb = LOGO_M, LOGO_RGB
        if s != 1.0:
            M = cv2.getRotationMatrix2D((float(LC[0]), float(LC[1])), 0.0, s)
            lm = cv2.warpAffine(LOGO_M, M, (W, H))
            lrgb = cv2.warpAffine(LOGO_RGB, M, (W, H))
        img += (GLOW * reveal * 0.25)[..., None] * K.rgb("#c8b8ff")
        img = img * (1 - (lm * reveal)[..., None]) + lrgb * (lm * reveal)[..., None]
    # small bubbles (behind and in front)
    for b in BUBBLES + LATE:
        st = b.state(t)
        if st is not None:
            draw_bubble(img, st[0], st[1], t, b.ph[2], b.thick, b.spin)
    # the big bubble, torn away from its top-right when it pops
    if Rb > 4 and pop < 1:
        p0 = LC + np.array([0.55, -0.62]) * Rb
        reach = pop * 2.3 * Rb

        def hole(xs, ys):
            dd = np.hypot(xs - p0[0], ys - p0[1])
            return np.clip((dd - reach) / 6, 0, 1)
        draw_bubble(img, LC + np.array([0, 6 * math.sin(t * 1.3)]), Rb, t, 1.7, 520, 0.25, 1.0, hole if pop > 0 else None)
        if pop > 0:
            # the tearing edge glints
            ys, xs = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
            dd = np.hypot(xs - p0[0], ys - p0[1])
            rr = np.hypot(xs - LC[0], ys - LC[1])
            edge = np.exp(-((dd - reach) / 14) ** 2) * (rr < Rb)
            img += cv2.resize(edge.astype(np.float32), (W, H))[..., None] * 0.6
    # droplets flung from the rim
    if t > T_POP:
        tau = t - T_POP
        if tau < 0.9:
            dl = np.zeros((H, W), np.uint8)
            for a_, sp, rad, delay, _ in DROPS:
                tt_ = tau - delay * 0.08
                if tt_ <= 0:
                    continue
                ang = a_ * 2 * math.pi
                p = LC + np.array([math.cos(ang), math.sin(ang)]) * R_BIG
                v = np.array([math.cos(ang), math.sin(ang)]) * (500 + 900 * sp)
                q = p + v * (1 - math.exp(-2.2 * tt_)) / 2.2 + np.array([0, 520 * tt_ * tt_])
                k = max(0.0, 1 - tt_ / 0.8)
                cv2.circle(dl, (int(q[0] * 16), int(q[1] * 16)), int(16 * (3 + 6 * rad) * (0.5 + 0.5 * k)), int(255 * k), -1, cv2.LINE_AA, 4)
            d = dl.astype(np.float32) / 255
            img += (d[..., None] * K.rgb("#f2f6ff") * 1.2 + cv2.GaussianBlur(d, (0, 0), 5)[..., None] * K.rgb("#b8d8ff") * 0.6)
    # the type
    if t > T_TXT:
        al = [C.smoothstep(0, 1, (t - T_TXT - j * 0.06) / 0.35) for j in range(len(ASTRIS_L))]
        def per(k, n):
            kk = C.clamp((t - T_TXT - k * 0.06) / 0.5)
            return {"dy": 40 * (1 - kk) ** 3, "s": 0.85 + 0.15 * C.spring(t - T_TXT - k * 0.06, 14, 0.5)}
        am = K.letters_mask(lock.line(0, per), alpha=al)
        img += (cv2.GaussianBlur(am, (0, 0), 12) * 0.25)[..., None] * K.rgb("#c8b8ff")
        img = K.comp(img, am, K.rgb("#fbf8ff"))
    if t > T_PROD:
        alp = [C.smoothstep(0, 1, (t - T_PROD - j * 0.025) / 0.35) for j in range(len(PROD_L))]
        img = K.comp(img, K.letters_mask(PROD_L, alpha=alp), K.rgb("#d9d0f5"))
    return POST.finish(img, i, bloom=0.3, threshold=0.85)


# ------------------------------------------------------------------------------------------------
# sound
# ------------------------------------------------------------------------------------------------
def audio():
    m = S.Mix(DUR)
    m.add(S.pad([S.midi(n) for n in (55, 62, 67, 71, 74)], DUR, attack=1.6, release=1.4, cutoff=(500, 2600), level=1.0, seed=2510),
          0.0, gain=0.16, send=0.5)
    m.add(S.sos(S.noise(DUR, "pink", 2511), "bandpass", (300, 2000), 2) * 0.05, 0.0, gain=1.0, send=0.2)
    for k, (tk, nn) in enumerate(((0.35, 79), (0.95, 83), (1.5, 86), (2.0, 91))):
        m.add(X.kalimba(S.midi(nn), 1.6), tk, gain=0.16, pan=-0.4 + 0.25 * k, send=0.5)
    penta = [67, 69, 71, 74, 76, 79, 81, 83, 86, 88, 91, 93, 95, 98, 100]
    for k, b in enumerate(MERGERS):
        pan = float(np.clip((b.p1[0] - W / 2) / (W / 2), -1, 1)) * 0.6
        m.add(X.bloop(S.midi(penta[min(k, len(penta) - 1)]) * 0.5, 2520 + k, 0.8), b.tm, gain=0.16, pan=pan, send=0.35)
    # the pop: a crisp click, a wet plop, a spray of tiny droplets and a sparkle
    rng = np.random.default_rng(2530)
    click = S.sos(rng.standard_normal(int(0.004 * S.SR)), "highpass", 2000, 2) * np.exp(-np.arange(int(0.004 * S.SR)) / 40)
    m.add(click, T_POP, gain=0.9, send=0.2)
    tt = np.arange(int(0.08 * S.SR)) / S.SR
    plop = np.sin(2 * np.pi * (900 - 3000 * tt) * tt) * np.exp(-tt / 0.02)
    m.add(plop, T_POP, gain=0.35, send=0.3)
    for k in range(26):
        f = rng.uniform(2500, 6000)
        m.add(S.tick(f, 0.05, 1.0, 0.6, 2540 + k, 0.2), T_POP + rng.uniform(0.02, 0.5), gain=0.05, pan=rng.uniform(-0.8, 0.8), send=0.4)
    m.add(S.shimmer(1.4, root=2200, density=30, level=1.0, seed=2570, rise=0.1), T_POP + 0.02, gain=0.10, send=0.6)
    m.add(S.reverse_swell(0.6, 1.0, 2571, 2200), T_POP - 0.6, gain=0.12, send=0.3)
    chord = [S.midi(n) for n in (55, 62, 67, 71, 74, 79)]
    m.add(S.sting(chord, 3.0, level=1.0, bright=0.55, seed=2572), T_TXT, gain=0.28, send=0.5)
    m.add(S.chime(S.midi(91), 2.6, 1.0, 2.2), T_PROD, gain=0.08, pan=0.3, send=0.6)
    for k, b in enumerate(LATE):
        m.add(X.bloop(S.midi(79 + 2 * k) * 0.5, 2580 + k, 0.5), b.ts + 0.4, gain=0.05, pan=0.3 - 0.15 * k, send=0.5)
    mix = m.master(ir_seconds=2.4, wet=0.7, peak_db=-1.5, tail_fade=0.5)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [40, 76, 84, 155], tag="bonus05")
