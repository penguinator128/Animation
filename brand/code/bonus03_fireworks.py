"""
ASTRIS PRODUCTIONS - Bonus 03: FIREWORKS (6.5 s)

A summer night over dark hills. Rockets whistle up and burst: a red-gold peony, a blue-violet chrysanthemum
with long streaks, a drooping golden willow, and the sky flashes with each one; smoke drifts, lit from inside.
Then the big one climbs to the centre and bursts into a full rainbow sphere - which, instead of falling, hangs
in the air and gathers itself into the logo, spark by spark. The logo glows solid gold-white with a rainbow
halo, a fizzing fuse runs along the baseline and lights ASTRIS letter by letter, and PRODUCTIONS settles under.
Sound: launch thumps and whistles, booms with long echoes, crackle, crickets, a shimmering rise, a fuse fizz
and a warm closing chord.
"""
import math

import numpy as np

import common as C
import kit as K
import sound as S
import sfx as X

cv2 = C.cv2
NAME = "astris-bonus-03"
DUR = 7.0
FPS = C.FPS
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=2301, grain=0.02, vignette=0.38, vig_inner=0.3, grain_size=1.0, grain_floor=0.2)
G = 260.0                                         # gravity, px/s^2
lock = K.Lockup2(LOGO, logo_h=700, lines=[("syncopate-700", "ASTRIS", 150, 0.30, None),
                                            ("montserrat-500", "PRODUCTIONS", 50, 0.0, 1.0)],
                 gaps=(150, 62), centre=(W / 2, H / 2 - 80))
LC = lock.logo_c.astype(np.float64)
T_BIG = 2.55
T_FORM0, T_FORM1 = T_BIG + 0.40, T_BIG + 1.25
T_SOLID0, T_SOLID1 = T_BIG + 1.62, T_BIG + 2.15          # the sparks hold the logo's shape for a beat first
T_FUSE0, T_FUSE1 = 4.62, 5.25
T_PROD = 5.15
RNG = np.random.default_rng(2302)


# ------------------------------------------------------------------------------------------------
# bursts: closed-form ballistics with linear drag  p(t) = p0 + v0(1-e^-kt)/k + g(t/k - (1-e^-kt)/k^2)
# ------------------------------------------------------------------------------------------------
def ballistic(p0, v0, k, g, tau):
    e = np.exp(-k * tau)
    a = (1 - e) / k
    return p0 + v0 * a[..., None] + np.stack([np.zeros_like(tau), g * (tau / k - a / k)], -1)


class Burst:
    def __init__(self, t, pos, n, speed, k, life, trail, hues, sat=1.0, g=G, crackle=0.0, sphere=True, glitter=0.0,
                 width=2):
        self.t, self.pos, self.n, self.k, self.life, self.trail, self.g = t, np.asarray(pos, np.float64), n, k, life, trail, g
        d = RNG.standard_normal((n, 3))
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        if not sphere:
            d[:, 2] = 0
            d /= np.linalg.norm(d, axis=1, keepdims=True)
        self.v0 = d[:, :2] * speed * RNG.uniform(0.92, 1.08, (n, 1))
        self.lives = life * RNG.uniform(0.75, 1.15, n)
        h = RNG.uniform(hues[0], hues[1], n) if len(hues) == 2 else np.full(n, hues[0])
        self.col = C.hue_wheel(h % 1.0) * sat + (1 - sat) * np.float32([1.0, 0.8, 0.45])
        self.crackle = RNG.random(n) < crackle
        self.glitter = glitter
        self.seed = RNG.integers(0, 1 << 30, n)
        self.width = width
        self.flash_col = self.col.mean(0)

    def positions(self, t):
        tau = np.maximum(0.0, t - self.t) + np.zeros(self.n)
        return ballistic(self.pos, self.v0, self.k, self.g, tau)

    def brightness(self, t, f):
        tau = t - self.t
        x = np.clip(tau / self.lives, 0, 1.2)
        b = np.where(x < 1, 1 - x ** 3, 0.0) * np.minimum(1.0, tau / 0.03)
        flick = ((self.seed * 2654435761 + f * 40503) % 997) / 997.0
        b = np.where(self.crackle & (x > 0.62), b * (flick > 0.45) * 1.6, b)
        if self.glitter:
            b = b * (0.65 + 0.7 * (((self.seed + f * 7919) % 101) / 101.0) ** 3)
        return b

    def colour(self, t):
        tau = t - self.t
        hot = np.clip(1 - tau / 0.18, 0, 1)
        cool = np.clip(tau / self.life - 0.6, 0, 1) * 0.5
        c = self.col * (1 - hot) + np.float32([1.0, 0.95, 0.85]) * hot
        return c * (1 - cool) + c * np.float32([1.0, 0.55, 0.35]) * cool

    def flash(self, t):
        tau = t - self.t
        return 0.0 if tau < 0 else math.exp(-tau / 0.22) * min(1.0, tau / 0.02)


class Rocket:
    def __init__(self, t0, t1, ground_x, burst_pos, seed):
        self.t0, self.t1 = t0, t1
        self.g0 = np.array([ground_x, H + 40.0])
        self.b = np.asarray(burst_pos, np.float64)
        r = np.random.default_rng(seed)
        self.wob = r.uniform(-30, 30)
        ns = 46
        self.st = np.sort(r.uniform(t0, t1, ns))
        self.sv = np.stack([r.normal(0, 60, ns), r.uniform(20, 140, ns)], 1)
        self.sl = r.uniform(0.25, 0.6, ns)

    def at(self, t):
        s = np.clip((t - self.t0) / (self.t1 - self.t0), 0, 1)
        e = 1 - (1 - s) ** 2.2
        p = self.g0 + (self.b - self.g0) * e
        return p + np.array([self.wob * math.sin(s * math.pi), 0.0])


BURSTS = [Burst(0.95, (0.24 * W, 0.30 * H), 380, 950, 1.6, 1.8, 0.07, (0.97, 1.10), crackle=0.35),
          Burst(1.30, (0.77 * W, 0.24 * H), 440, 1050, 1.3, 2.1, 0.22, (0.55, 0.78)),
          Burst(1.75, (0.40 * W, 0.17 * H), 280, 720, 0.9, 2.9, 0.45, (0.10, 0.13), sat=0.35, g=330, glitter=1.0, crackle=0.2),
          Burst(2.25, (0.63 * W, 0.37 * H), 240, 700, 1.7, 1.4, 0.06, (0.80, 0.95), crackle=0.5)]
ROCKETS = [Rocket(0.20, 0.95, 0.27 * W, BURSTS[0].pos, 1), Rocket(0.55, 1.30, 0.72 * W, BURSTS[1].pos, 2),
           Rocket(1.00, 1.75, 0.42 * W, BURSTS[2].pos, 3), Rocket(1.65, 2.25, 0.60 * W, BURSTS[3].pos, 4),
           Rocket(1.75, T_BIG, 0.50 * W, LC, 5)]


# ------------------------------------------------------------------------------------------------
# the big rainbow sphere that gathers into the logo
# ------------------------------------------------------------------------------------------------
def logo_targets(n_line=1150, n_fill=450):
    polys = lock.logo_polys()
    per = np.array([np.sum(np.linalg.norm(np.roll(p, -1, 0) - p, axis=1)) for p in polys])
    pts = []
    for p, L in zip(polys, per):
        m = max(3, int(round(n_line * L / per.sum())))
        seg = np.roll(p, -1, 0) - p
        cum = np.concatenate([[0], np.cumsum(np.linalg.norm(seg, axis=1))])
        for s in np.linspace(0, cum[-1], m, endpoint=False):
            j = min(np.searchsorted(cum, s, side="right") - 1, len(p) - 1)
            f = (s - cum[j]) / max(1e-6, cum[j + 1] - cum[j])
            pts.append(p[j] + seg[j] * f)
    m = C.poly_mask(polys)
    ys, xs = np.nonzero(m > 0.5)
    pick = RNG.choice(len(xs), n_fill, replace=False)
    pts += list(np.stack([xs[pick], ys[pick]], 1).astype(np.float64))
    return np.array(pts, np.float64)


TARGETS = logo_targets()
NB = len(TARGETS)
_d = RNG.standard_normal((NB, 3))
_d /= np.linalg.norm(_d, axis=1, keepdims=True)
BIG_V = _d[:, :2] * 2300 * RNG.uniform(0.9, 1.08, (NB, 1))
BIG_K, BIG_G = 2.5, 70.0
# match sparks to targets by angle so the sphere folds into the shape without crossing over itself
ang_p = np.arctan2(BIG_V[:, 1], BIG_V[:, 0])
ang_t = np.arctan2(TARGETS[:, 1] - LC[1], TARGETS[:, 0] - LC[0])
BIG_T = np.empty_like(TARGETS)
BIG_T[np.argsort(ang_p)] = TARGETS[np.argsort(ang_t)]
BIG_COL = C.hue_wheel(((ang_p / (2 * math.pi)) + 0.5) % 1.0)
BIG_SEED = RNG.integers(0, 1 << 30, NB)
SWIRL = 0.5


def big_positions(t):
    tau = np.full(NB, max(0.0, t - T_BIG))
    p = ballistic(LC, BIG_V, BIG_K, BIG_G, tau)
    w = C.smoothstep(T_FORM0, T_FORM1, t)
    if w <= 0:
        return p
    d = p - BIG_T
    a = SWIRL * (1 - w)
    ca, sa = math.cos(a), math.sin(a)
    d = np.stack([d[:, 0] * ca - d[:, 1] * sa, d[:, 0] * sa + d[:, 1] * ca], 1)
    return BIG_T + d * (1 - w) ** 2.2


# ------------------------------------------------------------------------------------------------
# static scenery: sky, faint stars, hills; smoke texture
# ------------------------------------------------------------------------------------------------
def build_scene(seed=2303):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = yy / H
    sky = K.rgb("#02030d") * (1 - v[..., None]) + K.rgb("#0b0c24") * v[..., None]
    r = np.random.default_rng(seed)
    st = np.zeros((H, W), np.uint8)
    for _ in range(2600):
        x, y = r.uniform(0, W), r.uniform(0, H * 0.85)
        b = r.uniform(0.1, 0.6) ** 2
        cv2.circle(st, (int(x * 4), int(y * 4)), int(4 * (0.7 + b)), int(255 * b), -1, cv2.LINE_AA, 2)
    sky = sky + (st.astype(np.float32) / 255)[..., None] * K.rgb("#dfe6ff") * 0.8
    # hills with a ragged tree line
    x1 = np.arange(W, dtype=np.float32)
    ridge = H * 0.885 + 60 * np.sin(x1 / W * 5.1 + 0.7) + 35 * np.sin(x1 / W * 11.3 + 2.1)
    trees = np.zeros(W, np.float32)
    for _ in range(260):
        cx, wd, ht = r.uniform(0, W), r.uniform(14, 46), r.uniform(20, 95)
        trees = np.maximum(trees, ht * np.clip(1 - np.abs(x1 - cx) / wd, 0, 1) ** 0.8)
    top = ridge - trees
    hm = np.zeros((H * 2, W * 2), np.uint8)
    pts = np.concatenate([np.stack([x1 * 2, top * 2], 1), [[W * 2, H * 2], [0, H * 2]]]).astype(np.int32)
    cv2.fillPoly(hm, [pts], 255, cv2.LINE_AA)
    hills = cv2.resize(hm, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    rim = np.clip(cv2.GaussianBlur(hills, (0, 0), 3) - hills * 0.98, 0, 1) * 2.0
    return sky.astype(np.float32), hills, rim


SKY, HILLS, RIM = build_scene()
SMOKE_TEX = cv2.resize(K.fbm(H // 16, W // 16, 2304, 5), (W // 4, H // 4), interpolation=cv2.INTER_CUBIC)
SMOKE_TEX = np.clip((SMOKE_TEX - 0.3) * 1.6, 0, 1).astype(np.float32)
YQ, XQ = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) * 4


def light_field(t):
    """Quarter-res RGB: sky flashes from every burst + the lit smoke drifting after them."""
    acc = np.zeros((H // 4, W // 4, 3), np.float32)
    smoke = np.zeros((H // 4, W // 4), np.float32)
    srcs = [(b.t, b.pos, b.flash_col, 1.0, 0.8) for b in BURSTS] + [(T_BIG, LC, np.float32([1.0, 0.85, 0.95]), 0.85, 1.0)]
    for tb, pos, col, k, sz in srcs:
        if t < tb:
            continue
        tau = t - tb
        fl = math.exp(-tau / 0.22) * min(1.0, tau / 0.02)
        c = pos + np.array([60.0 * tau, -20.0 * tau])
        d2 = (XQ - c[0]) ** 2 + (YQ - c[1]) ** 2
        rr = (300 + 260 * min(tau, 2.5)) * sz
        smoke += np.exp(-d2 / (2 * rr * rr)) * min(1.0, tau / 0.4) * 0.5 * math.exp(-tau / 4.0)
        if fl > 0.004:
            acc += col * (fl * k * (0.04 + 0.22 * np.exp(-d2 / (2 * 1100.0 ** 2))))[..., None]
    smoke *= SMOKE_TEX
    lum = acc.sum(axis=2, keepdims=True) * 0.33 + 0.02
    tint = acc / (acc.sum(axis=2, keepdims=True) + 1e-4)
    acc += smoke[..., None] * (lum * 2.2 * (0.4 + 0.6 * tint * 3) + np.float32([0.012, 0.012, 0.018]))
    return acc


# ------------------------------------------------------------------------------------------------
# drawing sparks (8-bit anti-aliased layer, 255 = intensity 2.0)
# ------------------------------------------------------------------------------------------------
def draw_trail(layer, pts_list, col, b, width):
    """pts_list: positions from head (index 0) to tail; brightness fades toward the tail."""
    n = len(pts_list) - 1
    for j in range(n):
        a, c = pts_list[j], pts_list[j + 1]
        k = b * (1 - j / n) ** 1.6
        if k < 0.02:
            continue
        v = np.clip(col * k / 2.0, 0, 1) * 255
        cv2.line(layer, (int(a[0] * 16), int(a[1] * 16)), (int(c[0] * 16), int(c[1] * 16)),
                 (float(v[0]), float(v[1]), float(v[2])), width, cv2.LINE_AA, 4)


def frame(i):
    t = i / FPS
    layer = np.zeros((H, W, 3), np.uint8)
    # rockets: hot head, short glowing trail, and the sparks they shed
    for rk in ROCKETS:
        if rk.t0 <= t < rk.t1 + 0.02:
            pts = [rk.at(t - d) for d in np.linspace(0, 0.16, 6)]
            draw_trail(layer, pts, np.float32([1.0, 0.85, 0.55]), 1.8, 4)
        for ts, sv, sl in zip(rk.st, rk.sv, rk.sl):
            tau = t - ts
            if 0 < tau < sl and ts < rk.t1:
                p0 = rk.at(ts)
                pts = [ballistic(p0, sv[None], 1.5, G, np.array([max(0.0, tau - d)]))[0] for d in (0, 0.05, 0.1)]
                draw_trail(layer, pts, np.float32([1.0, 0.7, 0.35]), 1.2 * (1 - tau / sl), 2)
    # bursts
    for bst in BURSTS:
        tau = t - bst.t
        if tau <= 0 or tau > bst.life * 1.2:
            continue
        b = bst.brightness(t, i)
        cols = bst.colour(t)
        trail_pts = [bst.positions(t - d) for d in np.linspace(0, min(bst.trail, tau), 5)]
        for j in range(bst.n):
            if b[j] > 0.02:
                draw_trail(layer, [tp[j] for tp in trail_pts], cols[j], b[j] * 1.5, bst.width)
    # the big one: hangs, then gathers into the logo, then glitters while the solid logo takes over
    if t > T_BIG:
        tau = t - T_BIG
        p_now = big_positions(t)
        hist = [big_positions(t - d) for d in (0.0, 0.03, 0.06, 0.1)] if tau > 0.1 else [p_now, big_positions(max(T_BIG, t - 0.05))]
        hot = max(0.0, 1 - tau / 0.18)
        fade = 1 - C.smoothstep(T_SOLID0 + 0.1, T_SOLID1 + 0.7, t)
        tw = (((BIG_SEED + i * 7919) % 101) / 101.0)
        b = (1.5 + 0.8 * hot) * (0.55 + 0.6 * tw ** 2) * fade * min(1.0, tau / 0.03)
        cols = BIG_COL * (1 - hot) + hot
        settle = C.smoothstep(T_FORM1 - 0.3, T_FORM1 + 0.05, t)      # moving streaks -> glittering points
        glint = (((BIG_SEED * 7 + i * 104729) % 211) / 211.0) > 0.93
        for j in range(NB):
            if b[j] <= 0.03:
                continue
            if settle < 1:
                draw_trail(layer, [hp[j] for hp in hist], cols[j], b[j] * (1 - settle), 3)
            if settle > 0:
                v = np.clip(cols[j] * b[j] * settle * (1.25 if glint[j] else 0.9) / 2.0, 0, 1) * 255
                cv2.circle(layer, (int(p_now[j, 0] * 16), int(p_now[j, 1] * 16)), int(16 * (6.5 if glint[j] else 4.2)),
                           (float(v[0]), float(v[1]), float(v[2])), -1, cv2.LINE_AA, 4)
    sparks = layer.astype(np.float32) * (2.0 / 255)
    img = SKY.copy()
    light = cv2.resize(light_field(t), (W, H), interpolation=cv2.INTER_LINEAR)
    img += light
    # solid logo made of light, with a rainbow halo
    s = C.smoothstep(T_SOLID0, T_SOLID1, t)
    if s > 0:
        img += (HALO * s)
        img = img * (1 - (LOGO_M * s)[..., None]) + LOGO_FILL * (LOGO_M * s * (1 + 1.4 * s * (1 - s)))[..., None]
    img += sparks + cv2.GaussianBlur(sparks, (0, 0), 3) * 0.8 + bigblur3(sparks, 14) * 0.5
    # hills in silhouette, rim-lit by the sky
    img = img * (1 - HILLS[..., None]) + (np.float32([0.006, 0.006, 0.01]) + light * 0.15) * HILLS[..., None]
    img += RIM[..., None] * light * 1.5
    # type: a fizzing fuse lights ASTRIS letter by letter; PRODUCTIONS follows
    if t > T_FUSE0 - 0.05:
        img = draw_type(img, t, i)
    return POST.finish(img, i, bloom=0.4, threshold=0.8)


def bigblur3(img, sigma, f=4):
    small = cv2.resize(img, (W // f, H // f), interpolation=cv2.INTER_AREA)
    return cv2.resize(cv2.GaussianBlur(small, (0, 0), sigma / f), (W, H), interpolation=cv2.INTER_LINEAR)


def _logo_layers():
    m = C.poly_mask_ss(lock.logo_polys(), ss=2)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    allp = np.concatenate(lock.logo_polys())
    v = np.clip((yy - allp[:, 1].min()) / (allp[:, 1].max() - allp[:, 1].min()), 0, 1)
    fill = (K.rgb("#fff1d2") * (1 - v[..., None]) + K.rgb("#ffbf55") * v[..., None]) * 0.97
    ang = np.arctan2(yy - LC[1], xx - LC[0])
    hue = C.hue_wheel(((ang / (2 * math.pi)) + 0.5) % 1.0)
    halo = (bigblur3(np.repeat(m[..., None], 3, 2), 20) * 0.9 + bigblur3(np.repeat(m[..., None], 3, 2), 70) * 0.6) * hue
    outer = C.poly_mask_ss([q for q in lock.logo_polys() if abs(cv2.contourArea(q.astype(np.float32))) > 20000], ss=2)
    return m, fill.astype(np.float32), (halo * (1 - outer[..., None])).astype(np.float32)


LOGO_M, LOGO_FILL, HALO = _logo_layers()
ASTRIS_L = lock.line(0)
PROD_L = lock.line(1)
A_BOX = np.concatenate([q for L in ASTRIS_L for q in L["polys"]])
FUSE_Y = A_BOX[:, 1].max() + 28
FUSE_X0, FUSE_X1 = A_BOX[:, 0].min() - 40, A_BOX[:, 0].max() + 40
LETTER_X = [np.concatenate(L["polys"])[:, 0].mean() for L in ASTRIS_L]


def draw_type(img, t, i):
    k = C.clamp((t - T_FUSE0) / (T_FUSE1 - T_FUSE0))
    fx = FUSE_X0 + (FUSE_X1 - FUSE_X0) * k
    al = []
    for x in LETTER_X:
        ti = T_FUSE0 + (x - FUSE_X0) / (FUSE_X1 - FUSE_X0) * (T_FUSE1 - T_FUSE0)
        al.append(C.smoothstep(ti - 0.02, ti + 0.12, t))
    am = K.letters_mask(ASTRIS_L, alpha=al)
    img = img + (cv2.GaussianBlur(am, (0, 0), 8) * 0.45 + bigblur3(np.repeat(am[..., None], 3, 2), 30)[..., 0] * 0.3)[..., None] * K.rgb("#ffb347")
    img = K.comp(img, am, K.rgb("#fff3dc"))
    if 0 < k < 1:
        # the fuse: a hot spark spitting little sparks as it runs along the baseline
        layer = np.zeros((H, W, 3), np.uint8)
        r = np.random.default_rng(i * 31 + 7)
        p0 = np.array([fx, FUSE_Y])
        for _ in range(40):
            v = np.array([r.normal(0, 260), r.uniform(-420, 60)])
            tau = r.uniform(0.02, 0.3)
            pts = [ballistic(p0, v[None], 2.0, 900, np.array([max(0.0, tau - d)]))[0] for d in (0, 0.03, 0.06)]
            draw_trail(layer, pts, np.float32([1.0, 0.75, 0.4]), 1.6 * (1 - tau / 0.3), 2)
        cv2.circle(layer, (int(fx * 16), int(FUSE_Y * 16)), 16 * 9, (255, 240, 200), -1, cv2.LINE_AA, 4)
        sp = layer.astype(np.float32) * (2.0 / 255)
        img = img + sp + cv2.GaussianBlur(sp, (0, 0), 6) * 1.2
    if t > T_PROD:
        alp = [C.smoothstep(0, 1, (t - T_PROD - j * 0.025) / 0.35) for j in range(len(PROD_L))]
        img = K.comp(img, K.letters_mask(PROD_L, alpha=alp), K.rgb("#f0d9b0"))
    return img


# ------------------------------------------------------------------------------------------------
# sound
# ------------------------------------------------------------------------------------------------
def boom(seed, size=1.0):
    r = np.random.default_rng(seed)
    d = 2.6
    t = S.tt(d)
    body = np.sin(2 * np.pi * (48 * size ** -0.3) * t + 3 * np.exp(-t / 0.05)) * np.exp(-t / (0.35 * size))
    crack = S.sos(r.standard_normal(len(t)), "bandpass", (180, 2400), 2) * np.exp(-t / 0.09)
    rumble = S.sos(r.standard_normal(len(t)), "lowpass", 300, 2) * np.exp(-t / 0.9) * 0.6
    x = body * 1.0 + crack * 0.8 + rumble
    echo = np.zeros_like(x)
    lag = int(0.38 * S.SR)
    echo[lag:] = S.sos(x[:-lag], "lowpass", 1200, 2) * 0.35
    return (x + echo) * np.minimum(1, t / 0.002)


def crackle(dur, seed, rate=110):
    r = np.random.default_rng(seed)
    n = int(dur * S.SR)
    out = np.zeros(n)
    k = 0
    while True:
        k += r.exponential(1 / rate)
        if k >= dur:
            break
        i0 = int(k * S.SR)
        ln = int(S.SR * r.uniform(0.001, 0.004))
        if i0 + ln >= n:
            break
        out[i0:i0 + ln] += r.standard_normal(ln) * np.exp(-np.arange(ln) / (ln * 0.3)) * r.uniform(0.3, 1.0)
    env = np.exp(-np.arange(n) / (S.SR * dur * 0.45))
    return S.sos(out, "highpass", 1500, 2) * env


def whistle(dur, seed, f0=800, f1=2300):
    t = S.tt(dur)
    r = np.random.default_rng(seed)
    f = f0 + (f1 - f0) * (t / dur) ** 0.7
    ph = 2 * np.pi * np.cumsum(f) / S.SR + 0.4 * np.sin(2 * np.pi * 7 * t)
    tone = np.sin(ph) * 0.6 + 0.2 * np.sin(2 * ph)
    hiss = S.sos(r.standard_normal(len(t)), "bandpass", (2500, 7000), 2) * 0.35
    env = np.minimum(1, t / 0.05) * np.minimum(1, (dur - t) / 0.04)
    return (tone + hiss) * env


def crickets(dur, seed):
    r = np.random.default_rng(seed)
    t = S.tt(dur)
    x = np.zeros(len(t))
    for f, rate, ph in ((4400, 2.6, 0.0), (4750, 2.1, 0.3)):
        chirp = (np.sin(2 * np.pi * rate * t + ph * 6) > 0.6).astype(float)
        chirp = np.convolve(chirp, np.ones(200) / 200, mode="same")
        x += np.sin(2 * np.pi * f * t) * chirp * (0.5 + 0.5 * np.sin(2 * np.pi * 30 * t) ** 2)
    return x * 0.5 + S.sos(r.standard_normal(len(t)), "lowpass", 500, 2) * 0.4


def audio():
    m = S.Mix(DUR)
    m.add(crickets(DUR, 2310), 0.0, gain=0.05, send=0.1)
    pans = [-0.5, 0.55, -0.2, 0.25, 0.0]
    for j, rk in enumerate(ROCKETS):
        m.add(S.tick(90, 0.3, 1.0, 0.4, 2311 + j, 1.4), rk.t0, gain=0.35, pan=pans[j], send=0.2)
        m.add(whistle(rk.t1 - rk.t0, 2320 + j, 700 + 120 * j, 2000 + 200 * j), rk.t0, gain=0.11, pan=pans[j], send=0.35)
    for j, b in enumerate(BURSTS):
        m.add(boom(2330 + j, 1.0 if j != 2 else 0.8), b.t, gain=0.55, pan=pans[j], send=0.3)
        if b.crackle.any() or b.glitter:
            m.add(crackle(1.6 if not b.glitter else 2.2, 2340 + j, 90 if not b.glitter else 160), b.t + b.life * 0.55, gain=0.22, pan=pans[j], send=0.25)
    m.add(boom(2350, 1.5), T_BIG, gain=0.75, send=0.35)
    m.add(S.sub_drop(1.8, 75, 34, 0.3, 1.1), T_BIG, gain=0.4, send=0.0)
    m.add(S.reverse_swell(0.8, 1.0, 2351, 2600), T_FORM0, gain=0.12, send=0.4)
    m.add(S.shimmer(1.5, root=1700, density=34, level=1.0, seed=2352, rise=0.45), T_FORM0, gain=0.16, send=0.5)
    # fuse fizz, sweeping left to right, with a little pop at each letter
    fz = S.sos(np.random.default_rng(2360).standard_normal(int((T_FUSE1 - T_FUSE0 + 0.1) * S.SR)), "bandpass", (1800, 7500), 2)
    fz *= 0.6 + 0.4 * np.random.default_rng(2361).random(len(fz)) ** 4
    fz *= np.minimum(1, np.arange(len(fz)) / 800) * np.minimum(1, (len(fz) - np.arange(len(fz))) / 2000)
    pan_curve = np.linspace(-0.6, 0.6, len(fz))
    m.add(np.stack([fz * np.sqrt((1 - pan_curve) / 2), fz * np.sqrt((1 + pan_curve) / 2)]), T_FUSE0, gain=0.12, send=0.2)
    for j, x in enumerate(LETTER_X):
        ti = T_FUSE0 + (x - FUSE_X0) / (FUSE_X1 - FUSE_X0) * (T_FUSE1 - T_FUSE0)
        m.add(X.paper_pop(2370 + j, 1.6), ti, gain=0.10, pan=-0.6 + 0.24 * j, send=0.3)
    chord = [S.midi(n) for n in (53, 60, 65, 69, 72, 77)]
    m.add(S.sting(chord, 3.0, level=1.0, bright=0.7, seed=2380), T_SOLID0 + 0.1, gain=0.34, send=0.45)
    m.add(S.chime(S.midi(84), 2.6, 1.0, 2.2), T_PROD, gain=0.10, send=0.6)
    mix = m.master(ir_seconds=2.4, wet=0.6, peak_db=-1.5, tail_fade=0.4)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [84, 90, 94, 98, 102, 106, 110, 167], tag="bonus03")
