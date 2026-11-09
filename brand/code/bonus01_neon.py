"""
ASTRIS PRODUCTIONS - Bonus 01: NEON SIGN (5.5 s)

A dark room, a brick wall, a neon sign we can only just make out: cold glass tubes catching a little light.
A switch clacks. The logo's tubes sputter and stutter to life one piece at a time, each flicker throwing pink
light across the bricks; ASTRIS follows letter by letter in ice blue (the R is stubborn and takes three goes),
then PRODUCTIONS. Then it all settles into a steady, humming glow while the camera slowly leans in.
Sound: the buzz and sizzle of the tubes (gated by the same flicker), ignition crackles, a switch, a mains hum,
and a warm synth chord when the whole sign is finally lit.
"""
import math

import numpy as np
from scipy import signal

import common as C
import kit as K
import sound as S
import sfx as X

cv2 = C.cv2
NAME = "astris-bonus-01"
DUR = 5.5
FPS = C.FPS
N = int(round(DUR * FPS))
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=2101, grain=0.022, vignette=0.42, vig_inner=0.25, grain_size=1.1, grain_floor=0.2)
PINK, ICE = K.rgb("#ff2f9a"), K.rgb("#36e2ff")

lock = K.Lockup2(LOGO, logo_h=760, lines=[("syncopate-700", "ASTRIS", 176, 0.30, None),
                                            ("montserrat-500", "PRODUCTIONS", 58, 0.0, 1.0)],
                 gaps=(150, 66), centre=(W / 2, H / 2 - 10))
CEN = np.array([W / 2, H / 2 - 10])
L_DIR = np.array([-0.45, -0.7, 0.55]) / np.linalg.norm([-0.45, -0.7, 0.55])
HV = (L_DIR + np.array([0, 0, 1.0])) / np.linalg.norm(L_DIR + np.array([0, 0, 1.0]))


# ------------------------------------------------------------------------------------------------
# flicker scripts (per frame).  '.' off  'd' dim  'h' half  'o' on  'X' over-bright flash; then steady
# ------------------------------------------------------------------------------------------------
LEVEL = {".": 0.0, "d": 0.3, "h": 0.6, "o": 1.0, "X": 1.3}


def script(f0, pattern):
    lv = np.zeros(N + 40, np.float32)
    for k, ch in enumerate(pattern):
        if f0 + k < len(lv):
            lv[f0 + k] = LEVEL[ch]
    s = f0 + len(pattern)
    for f in range(s, len(lv)):
        lv[f] = 0.82 + 0.18 * (1 - math.exp(-(f - s) / 6.0))       # warm-up: neon brightens as it settles
    return lv


# ------------------------------------------------------------------------------------------------
# the wall
# ------------------------------------------------------------------------------------------------
def build_wall(seed=2102):
    r = np.random.default_rng(seed)
    bw, bh, mort = 330, 128, 13
    tint = np.zeros((H, W, 3), np.float32)
    hmap = np.zeros((H, W), np.float32)
    for row in range(-1, H // bh + 2):
        off = (row % 2) * bw // 2 + int(r.uniform(-20, 20))
        for col in range(-1, W // bw + 2):
            x0, y0 = col * bw + off, row * bh
            c = np.array([r.uniform(0.30, 0.42), r.uniform(0.16, 0.22), r.uniform(0.17, 0.24)], np.float32) * r.uniform(0.8, 1.15)
            cv2.rectangle(tint, (x0 + mort // 2, y0 + mort // 2), (x0 + bw - mort // 2, y0 + bh - mort // 2), c.tolist(), -1)
            cv2.rectangle(hmap, (x0 + mort // 2, y0 + mort // 2), (x0 + bw - mort // 2, y0 + bh - mort // 2), 1.0, -1)
    mortar = (hmap < 0.5)[..., None]
    tex = cv2.resize(K.fbm(H // 4, W // 4, seed + 1, 7), (W, H), interpolation=cv2.INTER_CUBIC)
    fine = cv2.GaussianBlur(r.standard_normal((H, W)).astype(np.float32), (0, 0), 1.2)
    alb = np.where(mortar, np.float32([0.20, 0.19, 0.20]), tint) * (0.75 + 0.5 * tex[..., None]) * (1 + 0.10 * fine[..., None])
    hmap = cv2.GaussianBlur(hmap, (0, 0), 3.5) + 0.06 * tex
    gx = cv2.Sobel(hmap, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(hmap, cv2.CV_32F, 0, 1, ksize=3)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx, dy = xx - CEN[0], yy - CEN[1]
    d = np.hypot(dx, dy) + 1e-3
    # grazing light from the sign: brick edges that face it catch more light
    relief = np.clip(1 - 2.2 * (gx * dx + gy * dy) / d, 0.45, 1.8)
    return alb.astype(np.float32), relief.astype(np.float32)


WALL, RELIEF = build_wall()


# ------------------------------------------------------------------------------------------------
# tubes: each group is a set of shapes; its tube runs along the outline at `inset`, `half` wide
# ------------------------------------------------------------------------------------------------
class Tube:
    def __init__(self, polys, col, inset, half, levels, weight=1.0):
        m = C.poly_mask_ss(polys, ss=2)
        allp = np.concatenate(polys)
        pad = 40
        x0, y0 = int(max(0, allp[:, 0].min() - pad)), int(max(0, allp[:, 1].min() - pad))
        x1, y1 = int(min(W, allp[:, 0].max() + pad)), int(min(H, allp[:, 1].max() + pad))
        self.box = (x0, y0, x1, y1)
        mc = m[y0:y1, x0:x1]
        b = (mc > 0.5).astype(np.uint8)
        sdf = cv2.distanceTransform(1 - b, cv2.DIST_L2, 5) - cv2.distanceTransform(b, cv2.DIST_L2, 5)
        sdf = cv2.GaussianBlur(sdf, (0, 0), 1.0)
        v = sdf + inset
        self.alpha = np.clip((half - np.abs(v)) / 1.3 + 0.5, 0, 1).astype(np.float32)
        u = np.clip(v / half, -1, 1)
        gx = cv2.Sobel(sdf, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(sdf, cv2.CV_32F, 0, 1, ksize=3)
        gn = np.hypot(gx, gy) + 1e-6
        nx, ny, nz = u * gx / gn, u * gy / gn, np.sqrt(np.clip(1 - u * u, 0, 1))
        spec = np.clip(nx * HV[0] + ny * HV[1] + nz * HV[2], 0, 1) ** 36
        diff = np.clip(nx * L_DIR[0] + ny * L_DIR[1] + nz * L_DIR[2], 0, 1)
        self.glass = (np.float32([0.05, 0.05, 0.06]) * (0.4 + diff[..., None]) + spec[..., None] * 0.55).astype(np.float32)
        core = (1 - u * u) ** 1.6
        col = np.asarray(col, np.float32)
        self.lit = (col * 1.05 * (1 - core[..., None]) + (0.92 + 0.38 * col) * core[..., None]).astype(np.float32)
        # contact shadow on the wall (tubes sit a few cm proud on stand-offs)
        sh = cv2.GaussianBlur(self.alpha, (0, 0), 7)
        self.shadow = np.roll(np.roll(sh, 16, 0), 10, 1) * 0.55
        # halo in the air (half res) and the light thrown on the wall (1/8 res)
        full = np.zeros((H, W), np.float32)
        full[y0:y1, x0:x1] = self.alpha
        half_r = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        self.glow = (cv2.GaussianBlur(half_r, (0, 0), 3) * 1.1 + cv2.GaussianBlur(half_r, (0, 0), 12) * 0.85 +
                     cv2.GaussianBlur(half_r, (0, 0), 36) * 0.55)
        e8 = cv2.resize(full, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        self.light = cv2.GaussianBlur(e8, (0, 0), 9) * 9 + cv2.GaussianBlur(e8, (0, 0), 40) * 26 + cv2.GaussianBlur(e8, (0, 0), 110) * 60
        self.col = col
        self.levels = levels
        self.weight = weight

    def level(self, i):
        return float(self.levels[i])


def film_piece():
    """Index of the logo piece that carries the sprocket holes (the one with the most contours)."""
    counts = [len(LOGO.piece_polys(k)) for k in range(2)]
    return int(np.argmax(counts))


FILM = film_piece()
BAR = 1 - FILM
astris = lock.line(0)
prod = lock.line(1)

R_PATTERN = "h..d...X.d....o"
TUBES = [Tube(lock.logo_polys(pieces=[BAR]), PINK, 15, 8.0, script(14, "X..h...o.Xo"), 1.2),
         Tube(lock.logo_polys(pieces=[FILM]), PINK, 15, 8.0, script(18, "h.....X.d..o"), 1.4)]
for k, L in enumerate(astris):
    TUBES.append(Tube(L["polys"], ICE, 7, 5.0, script(36 + 3 * k, R_PATTERN if L["ch"] == "R" else "X.o"), 0.35))
TUBES.append(Tube([q for L in prod for q in L["polys"]], ICE, 0, 2.6, script(58, "d.h..X.o"), 0.7))
T_ALL = max(int(np.argmax(t.levels >= 0.82)) for t in TUBES) / FPS     # the moment the whole sign is lit

MOTES = np.random.default_rng(2103).uniform(0, 1, (170, 5)).astype(np.float32)


def frame(i):
    t = i / FPS
    levels = [tb.level(i) for tb in TUBES]
    # light on the wall: a little cold ambient from above + everything the tubes throw
    yy8 = np.linspace(0, 1, H // 8, dtype=np.float32)[:, None, None]
    light8 = np.broadcast_to(np.float32([0.045, 0.050, 0.068]) * (1.3 - 0.8 * yy8), (H // 8, W // 8, 3)).copy()
    glow2 = np.zeros((H // 2, W // 2, 3), np.float32)
    for tb, lv in zip(TUBES, levels):
        if lv > 0:
            light8 += tb.light[..., None] * tb.col * (lv * tb.weight * 0.11)
            glow2 += tb.glow[..., None] * tb.col * (lv * 0.75)
    light = cv2.resize(light8, (W, H), interpolation=cv2.INTER_CUBIC)
    img = WALL * light * RELIEF[..., None]
    # tubes: contact shadow, then glass (unlit) blending into emission (lit)
    for tb, lv in zip(TUBES, levels):
        x0, y0, x1, y1 = tb.box
        reg = img[y0:y1, x0:x1]
        reg *= (1 - tb.shadow * (0.5 + 0.5 * min(1.0, light[y0:y1, x0:x1].mean() * 6)))[..., None]
        e = min(lv, 1.3)
        tube_rgb = tb.glass * (1 - min(e, 1.0)) + tb.lit * e
        a = tb.alpha[..., None]
        img[y0:y1, x0:x1] = reg * (1 - a) + tube_rgb * a
    img += cv2.resize(glow2, (W, H), interpolation=cv2.INTER_LINEAR)
    # dust motes drifting through the light
    total = sum(lv * tb.weight for tb, lv in zip(TUBES, levels))
    if total > 0.05:
        dm = np.zeros((H, W), np.float32)
        for mx, my, ms, mvx, mph in MOTES:
            x = (mx * W + (mvx - 0.5) * 140 * t + 30 * math.sin(t * 0.7 + mph * 6)) % W
            y = (my * H - 40 * t * (0.3 + ms) + 20 * math.cos(t * 0.5 + mph * 5)) % H
            near = math.exp(-((x - CEN[0]) ** 2 + (y - CEN[1]) ** 2) / (2 * 1100 ** 2))
            cv2.circle(dm, (int(x * 4), int(y * 4)), int(4 * (1.5 + 3.5 * ms)), float(near * (0.3 + 0.7 * ms)), -1, cv2.LINE_AA, 2)
        dm = cv2.GaussianBlur(dm, (0, 0), 1.6)
        img += dm[..., None] * np.float32([1.0, 0.75, 0.95]) * min(1.0, total / 4) * 0.35
    # a slow lean in
    z = 1.0 + 0.055 * C.smoothstep(0, DUR, t)
    M = cv2.getRotationMatrix2D((float(CEN[0]), float(CEN[1])), 0.0, z)
    img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    return POST.finish(img, i, bloom=0.35, threshold=0.8)


# ------------------------------------------------------------------------------------------------
# sound
# ------------------------------------------------------------------------------------------------
def env_from_levels(levels, ramp_ms=3.0):
    n = int(round(DUR * S.SR))
    per = S.SR / FPS
    idx = np.minimum((np.arange(n) / per).astype(int), len(levels) - 1)
    e = np.asarray(levels, np.float64)[idx]
    k = max(1, int(ramp_ms / 1000 * S.SR))
    return np.convolve(e, np.ones(k) / k, mode="same")


def buzz(n, seed):
    t = np.arange(n) / S.SR
    r = np.random.default_rng(seed)
    pulse = signal.square(2 * np.pi * 120 * t, duty=0.16)
    pulse = S.sos(pulse, "lowpass", 2600, 2) + 0.3 * S.sos(pulse, "bandpass", (900, 1400), 2)
    sizz = S.sos(r.standard_normal(n), "bandpass", (2800, 9000), 2) * (0.5 + 0.5 * np.sin(2 * np.pi * 120 * t)) ** 6
    hum = 0.6 * np.sin(2 * np.pi * 60 * t) + 0.25 * np.sin(2 * np.pi * 180 * t)
    return 0.35 * pulse + 0.9 * sizz + 0.35 * hum


def audio():
    m = S.Mix(DUR)
    n = m.n
    m.add(S.sos(S.noise(DUR, "pink", 2110), "lowpass", 900, 2) * 0.05, 0.0, gain=1.0, send=0.0)     # room tone
    m.add(X.clack(520, 2111, 0.06), 10 / FPS, gain=0.6, pan=-0.3, send=0.3)
    m.add(S.tick(140, 0.25, 1.0, 0.3, 2112, 1.0), 10 / FPS + 0.01, gain=0.5, send=0.2)
    rng = np.random.default_rng(2113)
    for k, tb in enumerate(TUBES):
        lv = tb.levels[:N]
        env = env_from_levels(lv)
        pan = float(np.clip(((tb.box[0] + tb.box[2]) / 2 - W / 2) / (W / 2), -1, 1)) * 0.6
        b = buzz(n, 2120 + k) * env * (0.55 if k < 2 else 0.3)
        m.add(b, 0.0, gain=0.42, pan=pan, send=0.12)
        # crackle on every rising edge, a tiny glass "tink" on the very first ignition
        first = True
        for f in range(1, N):
            jump = lv[f] - lv[f - 1]
            if jump > 0.2 and lv[f - 1] < 0.85:
                cr = S.sos(rng.standard_normal(int(S.SR * rng.uniform(0.008, 0.02))), "highpass", 1200, 2)
                cr *= np.exp(-np.arange(len(cr)) / (S.SR * 0.004))
                m.add(cr, f / FPS, gain=0.32 * jump, pan=pan, send=0.15)
                m.add(S.tick(rng.uniform(2200, 3400), 0.08, 1.0, 1.0, 2140 + f, 0.2), f / FPS, gain=0.10 * jump, pan=pan, send=0.2)
                if first:
                    m.add(X.glass_ping(rng.uniform(3800, 5200), 0.7), f / FPS, gain=0.05, pan=pan, send=0.5)
                    first = False
    # when the whole sign is lit: a deep thump and a warm, wide synth chord
    m.add(S.sub_drop(1.6, 70, 38, 0.25, 0.9), T_ALL, gain=0.45, send=0.05)
    chord = [S.midi(n_) for n_ in (50, 57, 62, 64, 69, 74)]
    m.add(X.synth_stab(chord, 2.6, seed=2150, bright=0.7), T_ALL, gain=0.36, send=0.45)
    m.add(S.reverse_swell(0.6, 1.0, 2151, 1800), T_ALL - 0.6, gain=0.16, send=0.3)
    mix = m.master(ir_seconds=1.8, wet=0.55, peak_db=-1.5, tail_fade=0.25)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [4, 14, 16, 22, 30, 38, 46, 50, 56, 62, 70, 131], tag="bonus01")
