"""
ASTRIS PRODUCTIONS - Intro 1: GO CRAZY (10.0 s)

"A star is born" (astris = of the stars). We jump to hyperspace toward a stellar core that keeps
charging: particle bursts and shockwaves arrive faster and faster, light ribbons spiral into the
vortex, lightning crackles, flares bloom and the camera shakes harder. Then everything implodes in
one sharp inhale, a beat of silence... the core detonates in a RAINBOW shockwave that bends the
starfield, a white flash, and the logo SLAMS in at the epicentre. ASTRIS slams in a beat later,
PRODUCTIONS glides in, and the lockup holds for 2.8 s while embers drift and a glint crosses it.
"""
import math
import sys

import numpy as np

import common as C
import sound as S

cv2 = C.cv2
NAME = "astris-hero-1-go-crazy"
DUR = 10.0
N = int(DUR * C.FPS)

# ---- the beat sheet: every visual event here has a sound at the same time ----------------------
T_IGNITE = 0.25
T_WARP = 0.50
BURSTS = [1.25, 2.50, 3.45, 4.20, 4.75, 5.15]
T_RIBBONS = 2.0
T_LIGHTNING = 3.4
T_IMPLODE = 5.35
T_HUSH = 5.80
T_PEAK = 143 / 24       # rainbow shockwave (5.958 s, 4 clean frames before the flash)
T_FLASH = 6.155        # white flash
T_SLAM = 6.25          # logo lands (frame 150)
T_ASTRIS = 6.625       # ASTRIS slams (frame 159)
T_PROD = 6.95          # PRODUCTIONS glides in
T_GLINT = 8.10         # light glint across the lockup

LOGO = C.Logo()
LOCK = C.Lockup(LOGO)
POST = C.Post(seed=11, grain=0.024, vignette=0.34)
CX, CY, _ = LOCK.logo_xy(1.0)
C0 = np.array([CX, CY])

# ---- precomputed fields (shared with the worker processes via fork) ------------------------------
XL, YL = C.small_grid(4)
RR_LOW = np.hypot(XL - CX, YL - CY)
_YY, _XX = np.mgrid[0:C.H, 0:C.W].astype(np.float32)
RR = np.hypot(_XX - CX, _YY - CY)
UX, UY = (_XX - CX) / np.maximum(RR, 1), (_YY - CY) / np.maximum(RR, 1)

# hyperspace travel: integrate speed on a fine grid so position is a pure function of t
_tg = np.linspace(0, DUR, 20001)


def _speed(t):
    if t < T_WARP:
        return 0.04
    if t < T_IMPLODE:
        k = (t - T_WARP) / (T_IMPLODE - T_WARP)
        return 0.04 + 1.75 * k ** 1.7
    if t < T_HUSH:
        k = (t - T_IMPLODE) / (T_HUSH - T_IMPLODE)
        return -2.8 * math.sin(math.pi * min(1, k * 1.1)) ** 0.7 - 0.2
    if t < T_PEAK:
        return 0.0
    return 0.02


_v = np.array([_speed(t) for t in _tg])
_D = np.concatenate([[0], np.cumsum((_v[1:] + _v[:-1]) / 2 * np.diff(_tg))])


def travel(t):
    return float(np.interp(t, _tg, _D))


def speed(t):
    return float(np.interp(t, _tg, _v))


# starfield
_r = np.random.default_rng(1)
NS = 1900
ST_X = _r.uniform(-1, 1, NS) * 1.6
ST_Y = _r.uniform(-1, 1, NS) * 1.0
ST_Z = _r.uniform(0, 1, NS)
ST_MAG = _r.uniform(0.35, 1.0, NS) ** 2
ST_COL = np.array([[0.85, 0.92, 1.0], [0.75, 0.82, 1.0], [1.0, 0.92, 0.85], [0.9, 0.85, 1.0]], np.float32)[
    _r.integers(0, 4, NS)]
FOCAL = 0.42 * C.W


def _fbm(w, h, seed, octaves=6):
    r = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gw, gh = max(2, int(3 * 2 ** o)), max(2, int(2 * 2 ** o))
        g = r.standard_normal((gh, gw)).astype(np.float32)
        acc += cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        tot += amp
        amp *= 0.55
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min())


_n1, _n2 = _fbm(960, 540, 5), _fbm(960, 540, 9)
NEB = (np.clip(_n1 - 0.35, 0, 1)[..., None] ** 1.6 * np.array([0.10, 0.18, 0.55]) +
       np.clip(_n2 - 0.45, 0, 1)[..., None] ** 1.8 * np.array([0.45, 0.15, 0.65]) +
       (np.clip(_n1 * _n2 - 0.3, 0, 1)[..., None] ** 2) * np.array([0.1, 0.6, 0.7])).astype(np.float32) * 0.9


def energy(t):
    if t < T_IGNITE:
        return 0.0
    if t < T_IMPLODE:
        return 0.18 + 0.82 * ((t - T_IGNITE) / (T_IMPLODE - T_IGNITE)) ** 1.5
    if t < T_HUSH:
        return 1.0 + 0.8 * (t - T_IMPLODE) / (T_HUSH - T_IMPLODE)
    if t < T_PEAK:
        return 0.15
    return 0.0


# ================================================================================================
# drawing helpers
# ================================================================================================
def P(p):
    return (int(round(p[0] * 16)), int(round(p[1] * 16)))


def line(img, a, b, col, w):
    cv2.line(img, P(a), P(b), tuple(float(c) for c in col), int(max(1, w)), cv2.LINE_AA, shift=4)


def draw_stars(full, t):
    v = speed(t)
    D = travel(t)
    z = np.mod(ST_Z - D, 1.0) * 0.985 + 0.015
    trail = np.clip(v * 0.075, -0.6, 0.6)
    z_prev = z + trail
    calm = t >= T_PEAK
    fade_in = C.smoothstep(0.0, 0.6, t)
    hush = 1.0 if not (T_HUSH <= t < T_PEAK) else 0.25
    after = 1.0 if t < T_PEAK else 0.45 + 0.55 * C.smoothstep(T_SLAM + 0.3, T_SLAM + 1.5, t)
    for i in range(NS):
        zi, zp = z[i], z_prev[i]
        if zp <= 0.015 or zp > 1.0 or abs(zp - zi) > 0.7:
            zp = zi
        a = np.array([CX + FOCAL * ST_X[i] / zi, CY + FOCAL * ST_Y[i] / zi])
        b = np.array([CX + FOCAL * ST_X[i] / zp, CY + FOCAL * ST_Y[i] / zp])
        near = 1 - zi
        bright = ST_MAG[i] * (0.25 + 1.6 * near ** 2) * C.smoothstep(0.0, 0.25, near) * fade_in * hush * after
        if bright < 0.01:
            continue
        if not (-400 < a[0] < C.W + 400 and -400 < a[1] < C.H + 400):
            continue
        w = 1 + 3.5 * near ** 2.5
        col = ST_COL[i] * bright
        if calm or np.hypot(*(a - b)) < 1.5:
            cv2.circle(full, P(a), int(16 * (0.8 + w * 0.5)), tuple(float(c) for c in col * 1.4), -1, cv2.LINE_AA, 4)
        else:
            line(full, b, a, col, w)


def draw_core(full, low, t):
    E = energy(t)
    if E <= 0:
        return
    size = 1.0
    if T_IMPLODE <= t < T_HUSH:                # compress to a needle point while getting hotter
        size = 1.0 - 0.75 * (t - T_IMPLODE) / (T_HUSH - T_IMPLODE)
    ign = C.pulse(t, T_IGNITE, 0.02, 0.35)
    r0 = (14 + 90 * E) * size
    glow = (1.0 / (1 + (RR_LOW / r0) ** 2) ** 1.4) * (0.8 + 1.4 * E) + np.exp(-RR_LOW / (220 + 500 * E * size)) * 0.25 * E
    low += glow[..., None] * np.array([0.75, 0.88, 1.0], np.float32)
    # white-hot point + diffraction spikes (a star)
    cv2.circle(full, P(C0), int(16 * (6 + 22 * E * size)), (2.2, 2.2, 2.3), -1, cv2.LINE_AA, 4)
    spin = 0.25 * t + 0.6 * travel(t)
    L = (300 + 1400 * E) * size + 900 * ign
    for k in range(6):
        a = spin + k * math.pi / 3
        d = np.array([math.cos(a), math.sin(a)])
        for frac, w, g in ((1.0, 2, 0.35), (0.55, 4, 0.5), (0.25, 7, 0.7)):
            line(full, C0 - d * L * frac, C0 + d * L * frac, (g * 0.8, g * 0.9, g), w)
    # anamorphic streak
    prof = np.exp(-((YL[:, :1] - CY) / (10 + 10 * E)) ** 2) * np.exp(-np.abs(XL[:1] - CX) / (900 + 2200 * E))
    low += (prof * (0.6 + 1.2 * E + 1.5 * ign))[..., None] * np.array([0.45, 0.68, 1.0], np.float32)


def draw_ghosts(low, t, strength, src=None):
    """Lens ghosts mirrored through the frame centre from a light source."""
    if strength < 0.01:
        return
    src = C0 if src is None else src
    cen = np.array([C.W / 2, C.H / 2])
    for k, rad, col in ((-0.45, 70, (0.3, 0.6, 1.0)), (0.35, 140, (0.6, 0.4, 1.0)), (0.9, 60, (0.3, 1.0, 0.8)),
                        (1.4, 230, (0.4, 0.5, 1.0)), (1.9, 110, (1.0, 0.6, 0.3))):
        p = cen + (cen - src) * k
        d = np.hypot(XL - p[0], YL - p[1])
        disc = np.clip((rad - d) / 14, 0, 1) * (0.5 + 0.5 * np.clip(d / rad, 0, 1) ** 4)
        low += disc[..., None] * np.array(col, np.float32) * 0.05 * strength


def burst_particles(full, t, tb, seed, n, spd, life, tint=(0.55, 0.8, 1.0), rainbow=0.0, width=2.5, origin=None):
    tau = t - tb
    if tau < 0 or tau > life * 1.3:
        return
    origin = C0 if origin is None else origin
    r = np.random.default_rng(seed)
    ang = r.uniform(0, 2 * math.pi, n)
    v = spd * r.lognormal(0, 0.45, n)
    k = r.uniform(1.6, 3.4, n)
    L = life * r.uniform(0.45, 1.3, n)
    sq = r.uniform(0.55, 1.0, n)            # a little depth: some sparks travel toward the lens
    hues = C.hue_wheel(ang / (2 * math.pi))
    warm = r.uniform(0, 1, n) < 0.18
    for i in range(n):
        if tau > L[i]:
            continue
        d1 = v[i] / k[i] * (1 - math.exp(-k[i] * tau))
        d0 = v[i] / k[i] * (1 - math.exp(-k[i] * max(0.0, tau - 0.045)))
        dirv = np.array([math.cos(ang[i]), math.sin(ang[i]) * sq[i]])
        a, b = origin + dirv * d0, origin + dirv * d1
        f = (1 - tau / L[i]) ** 1.5
        cool = min(1.0, tau / (L[i] * 0.5))
        base = np.array([1.0, 0.72, 0.4]) if warm[i] else np.array(tint)
        if rainbow > 0:
            base = base * (1 - rainbow) + hues[i] * rainbow
        col = (np.array([1.0, 1.0, 1.0]) * (1 - cool) + base * cool) * f * 1.6
        line(full, a, b, col, width * (0.6 + 0.8 * f))


def ring(low, t, tb, rmax, tc, w0, wg, amp, col, decay, r0=0.0):
    tau = t - tb
    if tau < 0 or tau > decay * 6:
        return
    R = r0 + rmax * (1 - math.exp(-tau / tc))
    w = w0 + wg * tau
    I = np.exp(-((RR_LOW - R) / w) ** 2) * amp * math.exp(-tau / decay)
    low += I[..., None] * np.array(col, np.float32)


def rainbow_ring(low, t):
    tau = t - T_PEAK
    if tau < 0 or tau > 1.4:
        return 0.0, 0.0, 0.0
    R = 150 + 3200 * (1 - math.exp(-tau / 0.2))
    w = 90 + 420 * tau
    amp = 1.05 * math.exp(-tau / 0.40)
    u = (RR_LOW - R) / w
    env = np.exp(-u ** 2 * 0.9)
    col = C.spectrum(np.clip(0.5 - u * 0.33, 0, 1))
    low += col * (env * amp)[..., None]
    # a faint second ring behind it
    R2 = 2200 * (1 - math.exp(-tau / 0.3))
    u2 = (RR_LOW - R2) / (w * 0.7)
    low += C.spectrum(np.clip(0.5 - u2 * 0.33, 0, 1)) * (np.exp(-u2 ** 2) * amp * 0.35)[..., None]
    return R, w, amp


def refract(full, R, w, amp):
    """Bends whatever is behind an expanding ring (shockwave lens)."""
    u = (RR - R) / w
    d = (amp * 46.0) * u * np.exp(-u * u)
    return cv2.remap(full, _XX - UX * d, _YY - UY * d, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)


def ribbons(full, low, t):
    if t < T_RIBBONS or t >= T_HUSH:
        return
    k = C.smoothstep(T_RIBBONS, T_RIBBONS + 0.6, t)
    imp = C.smoothstep(T_IMPLODE, T_HUSH, t)
    ang0 = 0.9 * (t - T_RIBBONS) + 1.6 * (t - T_RIBBONS) ** 2.2 / 4 + 9 * imp ** 2
    R0 = (1500 - 380 * C.smoothstep(T_RIBBONS, T_IMPLODE, t)) * (1 - imp) + 1
    cols = [(0.4, 0.85, 1.0), (0.7, 0.45, 1.0), (1.0, 1.0, 1.0), (1.0, 0.7, 0.35), (0.35, 0.55, 1.0)]
    for j in range(5):
        ph = ang0 + j * 2 * math.pi / 5
        th = np.linspace(0, 4.2, 70)
        rr = R0 * np.exp(-0.42 * th)
        ax = ph - th
        pts = np.stack([CX + rr * np.cos(ax), CY + rr * np.sin(ax) * 0.62], 1)
        for s in range(len(th) - 1):
            f = math.sin(math.pi * s / (len(th) - 1)) ** 1.5 * k
            c = np.array(cols[j]) * f
            line(full, pts[s], pts[s + 1], c * 1.3, 3)
            a, b = pts[s] / 4, pts[s + 1] / 4
            cv2.line(low, P(a), P(b), tuple(float(x) for x in c * 0.5), 6, cv2.LINE_AA, 4)


def lightning(full, low, t):
    if t < T_LIGHTNING or t >= T_HUSH:
        return
    slot = int(t * 14)
    r = np.random.default_rng(1000 + slot)
    inten = C.smoothstep(T_LIGHTNING, T_IMPLODE, t) * (0.6 + 0.4 * r.uniform())
    nb = 2 + int(5 * C.smoothstep(T_LIGHTNING, T_IMPLODE, t))
    for b in range(nb):
        a = r.uniform(0, 2 * math.pi)
        R = r.uniform(250, 760) * (1 - 0.6 * C.smoothstep(T_IMPLODE, T_HUSH, t))
        pts = [C0.copy(), C0 + R * np.array([math.cos(a), math.sin(a) * 0.8])]
        for lvl in range(6):
            new = [pts[0]]
            for p0, p1 in zip(pts[:-1], pts[1:]):
                mid = (p0 + p1) / 2
                dv = p1 - p0
                nrm = np.array([-dv[1], dv[0]]) / (np.linalg.norm(dv) + 1e-6)
                new += [mid + nrm * r.normal(0, np.linalg.norm(dv) * 0.22), p1]
            pts = new
        for p0, p1 in zip(pts[:-1], pts[1:]):
            line(full, p0, p1, (0.95 * inten, 0.85 * inten, 1.3 * inten), 2)
            cv2.line(low, P(p0 / 4), P(p1 / 4), (0.25 * inten, 0.15 * inten, 0.5 * inten), 4, cv2.LINE_AA, 4)


def infall(full, t):
    if t < 3.8 or t >= T_HUSH:
        return
    k = C.smoothstep(3.8, 4.6, t)
    r = np.random.default_rng(77)
    n = 520
    a0 = r.uniform(0, 2 * math.pi, n)
    r0 = r.uniform(600, 2200, n)
    ph = r.uniform(0, 1, n)
    rate = 0.55 + 1.6 * C.smoothstep(3.8, T_HUSH, t)
    for i in range(n):
        p = (ph[i] + t * rate) % 1.0
        p0 = max(0.0, p - 0.035)
        def pos(pp):
            rr = r0[i] * (1 - pp) ** 1.6
            a = a0[i] + 2.4 * pp
            return np.array([CX + rr * math.cos(a), CY + rr * math.sin(a) * 0.7])
        f = p ** 1.5 * k
        line(full, pos(p0), pos(p), (0.55 * f, 0.8 * f, 1.0 * f), 2)


# ================================================================================================
# the logo + type
# ================================================================================================
def logo_scale(t):
    if t < T_FLASH:
        return None
    if t < T_SLAM:
        return 2.9 - 1.9 * C.expo_in((t - T_FLASH) / (T_SLAM - T_FLASH), 4.0)
    tau = t - T_SLAM
    return 1.0 - 0.035 * math.exp(-tau / 0.07)


def cam_scale(t):
    return 1.0 + 0.03 * C.smoothstep(T_SLAM + 0.4, DUR, t)


EMBER_N = 240
_er = np.random.default_rng(55)
_outer = LOGO.polys
_pts = np.concatenate([p for p in _outer])
EMB_SRC = _pts[_er.integers(0, len(_pts), EMBER_N)]
EMB_BIRTH = _er.uniform(T_SLAM, DUR - 0.5, EMBER_N)
EMB_LIFE = _er.uniform(1.4, 3.2, EMBER_N)
EMB_V = _er.uniform(25, 90, EMBER_N)
EMB_PH = _er.uniform(0, 6.28, EMBER_N)
EMB_WARM = _er.uniform(0, 1, EMBER_N) < 0.35


def draw_embers(full, t, Sc):
    cx, cy, h = LOCK.logo_xy(Sc)
    for i in range(EMBER_N):
        tau = t - EMB_BIRTH[i]
        if tau < 0 or tau > EMB_LIFE[i]:
            continue
        p = np.array([cx, cy]) + EMB_SRC[i] * h
        p = p + np.array([22 * math.sin(EMB_PH[i] + tau * 1.7) + 12 * tau, -EMB_V[i] * tau])
        f = math.sin(math.pi * tau / EMB_LIFE[i]) ** 1.2 * (0.6 + 0.4 * math.sin(EMB_PH[i] + 9 * tau))
        col = (1.0, 0.7, 0.4) if EMB_WARM[i] else (0.55, 0.82, 1.0)
        cv2.circle(full, P(p), int(16 * 2.6), tuple(float(c * f * 0.9) for c in col), -1, cv2.LINE_AA, 4)


SPARK_N = 560
_sr = np.random.default_rng(66)
SPK_SRC = _pts[_sr.integers(0, len(_pts), SPARK_N)]
SPK_V = _sr.lognormal(0, 0.5, SPARK_N) * 1500
SPK_K = _sr.uniform(2.0, 4.0, SPARK_N)
SPK_L = _sr.uniform(0.25, 0.85, SPARK_N)


def edge_sparks(fx, t):
    tau = t - T_SLAM
    if tau < 0 or tau > 0.9:
        return
    cx, cy, h = LOCK.logo_xy(cam_scale(t))
    for i in range(SPARK_N):
        if tau > SPK_L[i]:
            continue
        src = np.array([cx, cy]) + SPK_SRC[i] * h
        dirv = SPK_SRC[i] / (np.linalg.norm(SPK_SRC[i]) + 1e-6)
        d1 = SPK_V[i] / SPK_K[i] * (1 - math.exp(-SPK_K[i] * tau))
        d0 = SPK_V[i] / SPK_K[i] * (1 - math.exp(-SPK_K[i] * max(0.0, tau - 0.04)))
        f = (1 - tau / SPK_L[i]) ** 1.6
        col = np.array([0.8, 0.9, 1.0]) * f * 1.5
        line(fx, src + dirv * d0, src + dirv * d1, col, 2)


def draw_logo(img, t):
    s = logo_scale(t)
    if s is None:
        return img
    Sc = s * cam_scale(t)
    # motion blur the slam by averaging sub-frame masks
    if T_FLASH <= t < T_SLAM:
        subs = [logo_scale(max(T_FLASH, t - k * (0.5 / C.FPS) / 7)) * cam_scale(t) for k in range(8)]
        m = sum(C.poly_mask(LOCK.logo_polys(sv)) for sv in subs) / len(subs)
    else:
        m = C.poly_mask_ss(LOCK.logo_polys(Sc), ss=2)
    tau = t - T_SLAM
    heat = 1.0 + (0.45 * math.exp(-max(tau, 0) / 0.10) if tau >= 0 else 1.0)
    cx, cy, h = LOCK.logo_xy(Sc)
    grad = np.clip(1.06 - 0.22 * (_YY - (cy - h / 2)) / h, 0.8, 1.06)
    col = np.array([0.90, 0.94, 1.0], np.float32)
    glint = 0.0
    if T_GLINT <= t <= T_GLINT + 0.9:
        g = (t - T_GLINT) / 0.9
        pos = -0.3 + 1.6 * C.expo_in_out(g, 5)
        band = (_XX - (cx - h * 0.9)) / (h * 1.8) - (_YY - cy) / (h * 3.5)
        glint = np.exp(-((band - pos) / 0.035) ** 2) * 0.9
    lum = (grad * heat + glint)[..., None] * col
    img = img * (1 - m[..., None]) + lum * m[..., None]
    rim = 0.20 + 0.45 * math.exp(-max(tau, 0) / 0.25)
    C.add_glow_mask(img, m, np.array([0.3, 0.55, 1.0]) * rim, sigmas=(8, 36, 130), weights=(0.45, 0.3, 0.25))
    return img, m


def draw_text(img, t):
    if t < T_ASTRIS - 0.16:
        return img
    Sc = cam_scale(t)
    # ASTRIS: letters fly in from very wide tracking and land hard on T_ASTRIS (motion-blurred)
    def tr_at(tx):
        if tx >= T_ASTRIS:
            return 1.0
        return 1.0 + 2.2 * (1 - C.expo_in((tx - (T_ASTRIS - 0.16)) / 0.16, 3.5))

    if t < T_ASTRIS + 0.03:
        ms = [LOCK.word_mask("astris", Sc, track_mul=tr_at(t - k * (0.5 / C.FPS) / 19)) for k in range(20)]
        ma = sum(ms) / len(ms) * C.smoothstep(T_ASTRIS - 0.16, T_ASTRIS - 0.06, t)
    else:
        ma = LOCK.word_mask("astris", Sc)
    heat = 1.0 + 0.8 * math.exp(-max(0, t - T_ASTRIS) / 0.14)
    img = img * (1 - ma[..., None]) + np.array([0.92, 0.95, 1.0], np.float32) * heat * ma[..., None]
    if t >= T_PROD:
        n = 11
        order = np.abs(np.arange(n) - (n - 1) / 2) / ((n - 1) / 2)       # reveal from the centre out
        al = [C.expo_out((t - T_PROD - o * 0.18) / 0.45, 5) for o in order]
        tp = 1.0 + 0.3 * (1 - C.expo_out((t - T_PROD) / 0.9, 5))
        mp = LOCK.word_mask("prod", Sc, alpha=al, track_mul=tp)
        img = img * (1 - mp[..., None]) + np.array([0.80, 0.86, 0.95], np.float32) * mp[..., None]
    return img


# ================================================================================================
# frame
# ================================================================================================
def shake_amp(t):
    a = 2 + 12 * C.smoothstep(T_WARP, T_IMPLODE, t) ** 1.5 if t < T_IMPLODE else 0
    if T_IMPLODE <= t < T_HUSH:
        a = 22
    for b in BURSTS:
        a += 26 * C.pulse(t, b, 0.01, 0.18)
    a += 70 * C.pulse(t, T_PEAK, 0.01, 0.3) + 110 * C.pulse(t, T_SLAM, 0.005, 0.24) + 30 * C.pulse(t, T_ASTRIS, 0.005, 0.15)
    if t > T_SLAM + 1.2:
        a *= 0.0
    return a


def frame(i):
    t = i / C.FPS
    full = np.zeros((C.H, C.W, 3), np.float32)
    low = np.zeros((C.H // 4, C.W // 4, 3), np.float32)

    # nebula: drifts toward us with the travel, lights up with the explosions
    D = travel(t)
    zoom = 1.0 + 0.18 * (D % 4.0) / 4.0 + 0.02 * t
    M = cv2.getRotationMatrix2D((CX / 4, CY / 4), 6 * math.sin(0.2 * t) + 25 * C.smoothstep(T_IMPLODE, T_HUSH, t), zoom)
    neb = cv2.warpAffine(NEB, M, (C.W // 4, C.H // 4), borderMode=cv2.BORDER_REFLECT101)
    lit = 0.35 + 0.65 * C.smoothstep(0, 1.5, t) + 0.6 * C.pulse(t, T_PEAK, 0.02, 0.5) + 0.35 * C.pulse(t, T_SLAM, 0.01, 0.6)
    if T_HUSH <= t < T_PEAK:
        lit *= 0.2
    if t > T_SLAM:
        lit *= 0.75
    nb = neb * lit
    low += nb / (1.0 + nb * 1.6)          # soft-clipped so explosions light the gas without blowing it out

    draw_stars(full, t)
    fx = np.zeros_like(full)
    lowfx = np.zeros_like(low)
    infall(fx, t)
    ribbons(fx, lowfx, t)
    lightning(fx, lowfx, t)
    full += fx
    low += lowfx
    fx[:] = 0
    draw_core(fx, low, t)
    full += fx
    fx[:] = 0
    for k, b in enumerate(BURSTS):
        burst_particles(fx, t, b, 300 + k, 260 + 60 * k, 2600 + 300 * k, 1.1)
        ring(low, t, b, 2000 + 200 * k, 0.35, 20, 140, 0.55, (0.55, 0.78, 1.0), 0.4)
        draw_ghosts(low, t, C.pulse(t, b, 0.01, 0.25) * 2.0)
        low += (C.pulse(t, b, 0.01, 0.12) * 0.25) * np.array([0.6, 0.75, 1.0], np.float32)
    draw_ghosts(low, t, energy(t) * 0.7)

    # PEAK: rainbow shockwave + rainbow-tinted burst
    R, w, amp = rainbow_ring(low, t)
    burst_particles(fx, t, T_PEAK, 900, 1100, 4200, 1.3, rainbow=0.75, width=3.0)
    if t >= T_PEAK - 0.02:
        low += (np.exp(-RR_LOW / 380) * C.pulse(t, T_PEAK, 0.015, 0.07) * 1.6)[..., None] * np.array([1.0, 0.97, 0.92], np.float32)
    # SLAM: white shockwave + sparks off the logo
    ring(low, t, T_SLAM, 3300, 0.32, 16, 200, 0.6, (0.8, 0.9, 1.0), 0.35, r0=620)
    edge_sparks(fx, t)
    full += fx
    ring(low, t, T_ASTRIS, 2400, 0.25, 20, 160, 0.35, (0.7, 0.85, 1.0), 0.25)

    full += C.up(low)
    if amp > 0.02:
        full = refract(full, R, w, amp)
    tau = t - T_SLAM
    if 0 <= tau < 1.0:
        Rs, ws = 620 + 3300 * (1 - math.exp(-tau / 0.32)), 16 + 200 * tau
        full = refract(full, Rs, ws, 1.0 * math.exp(-tau / 0.35))
        full *= 1.0 - 0.6 * C.pulse(t, T_SLAM, 0.004, 0.22)     # the world dips so the logo punches out

    # white flash
    fl = C.pulse(t, T_FLASH, 0.045, 0.038) * 1.35
    full += fl

    # logo, embers, type
    out = draw_logo(full, t)
    if isinstance(out, tuple):
        full, m = out
        emb = np.zeros_like(full)
        draw_embers(emb, t, logo_scale(t) * cam_scale(t))
        full += emb
    full = draw_text(full, t)

    # camera: shake, zoom punches, chromatic aberration on the big hits
    a = shake_amp(t)
    if a > 0.05:
        dx, dy, rot = C.shake_offsets(t, 7)
        punch = 1.0 + 0.045 * C.pulse(t, T_SLAM, 0.004, 0.16) + 0.02 * C.pulse(t, T_PEAK, 0.01, 0.2) + \
            sum(0.012 * C.pulse(t, b, 0.01, 0.12) for b in BURSTS)
        full = C.warp(full, dx * a, dy * a, rot * a * 0.012, 1.02 * punch, center=(CX, CY))
    ca = 0.004 * C.pulse(t, T_PEAK, 0.02, 0.3) + 0.007 * C.pulse(t, T_SLAM, 0.004, 0.25) + \
        sum(0.0015 * C.pulse(t, b, 0.01, 0.15) for b in BURSTS)
    if ca > 0.0003:
        full = C.chromatic(full, ca, center=(CX, CY))
    bloom = 0.55 + 0.5 * energy(t) + 0.5 * C.pulse(t, T_PEAK, 0.02, 0.3) + 0.35 * C.pulse(t, T_SLAM, 0.01, 0.25)
    if t > T_SLAM:
        bloom = 0.42 + 0.2 * math.exp(-(t - T_SLAM) / 0.25)
    return POST.finish(full, i, bloom=bloom, threshold=0.7)


# ================================================================================================
# sound: every beat above has a sound
# ================================================================================================
def audio():
    m = S.Mix(DUR)
    # bed: rumble + sub build that climbs through the warp, cut by the implosion
    rb = S.rumble(T_IMPLODE + 0.4, level=1.0, f=60, seed=2,
                  swell=lambda tt: 0.25 + 0.75 * np.clip(tt / T_IMPLODE, 0, 1) ** 1.6)
    n1 = int(round(T_IMPLODE * S.SR))
    env = np.ones(len(rb))
    env[n1:] = np.linspace(1, 0, len(rb) - n1)            # the implosion sucks the rumble away
    m.add(rb * env, 0.0, gain=0.55, send=0.05)
    m.add(S.sub_build(T_IMPLODE - 2.4, 30, 55, curve=2.2), 2.4, gain=0.45, send=0.0)
    # ignition ping
    m.add(S.chime(S.midi(86), 3.0, decay=1.4), T_IGNITE, gain=0.22, pan=0.0, send=0.5)
    m.add(S.chime(S.midi(93), 2.0, decay=1.0), T_IGNITE + 0.01, gain=0.10, pan=0.2, send=0.5)
    # warp jump whoosh + long air
    m.add(S.whoosh(1.6, peak=0.45, f_lo=120, f_hi=5200, q=0.9, pan_from=-0.3, pan_to=0.3, seed=31), T_WARP - 0.3,
          gain=0.8, send=0.2)
    # bursts: small impacts + whooshes, getting bigger and closer together
    for k, b in enumerate(BURSTS):
        m.add(S.impact(1.6, weight=0.35 + 0.08 * k, bright=0.8, metal=0.4, seed=40 + k, sub_f=(70, 40)), b,
              gain=0.38 + 0.05 * k, send=0.25)
        m.add(S.whoosh(0.55, peak=0.85, f_lo=400, f_hi=6000, q=1.3, pan_from=(-1) ** k * 0.6, pan_to=0,
                       seed=50 + k), b - 0.47, gain=0.35, send=0.2)
    # ribbons: circling swirl (pan rotates)
    dur_rb = T_HUSH - T_RIBBONS
    x = S.sweep(S.noise(dur_rb, "pink", 61), "bp", 700 + 2200 * (S.tt(dur_rb) / dur_rb) ** 1.4, 2.0)
    x *= np.clip(S.tt(dur_rb) / 0.8, 0, 1) * (0.3 + 0.7 * (S.tt(dur_rb) / dur_rb) ** 1.5)
    rate = 0.6 + 3.5 * (S.tt(dur_rb) / dur_rb) ** 2
    m.add(S.pan2(x / np.max(np.abs(x)), np.sin(2 * np.pi * np.cumsum(rate) / S.SR)), T_RIBBONS, gain=0.22, send=0.3)
    # lightning crackles
    rr = np.random.default_rng(71)
    t = T_LIGHTNING
    while t < T_HUSH - 0.05:
        dur = rr.uniform(0.04, 0.12)
        cr = S.sos(S.noise(dur, "white", int(t * 1000)), "bandpass", [1800, 9000], 2) * S.env_exp(dur, 0.001, dur / 3)
        cr *= (rr.uniform(0, 1, len(cr)) < 0.35)                       # crackle texture
        m.add(cr, t, gain=0.12 + 0.18 * (t - T_LIGHTNING) / (T_HUSH - T_LIGHTNING), pan=rr.uniform(-0.7, 0.7), send=0.3)
        t += rr.uniform(0.05, 0.16) * (1.2 - 0.6 * (t - T_LIGHTNING) / (T_HUSH - T_LIGHTNING))
    # riser into the implosion, then the inhale (reverse swell) and silence
    m.add(S.riser(T_IMPLODE - 3.3, 220, 4200, seed=73), 3.3, gain=0.42, send=0.25)
    m.add(S.reverse_swell(T_HUSH - T_IMPLODE + 0.05, seed=75, f=3500), T_IMPLODE, gain=0.55, send=0.1)
    m.add(S.sub_build(T_HUSH - T_IMPLODE, 60, 28, curve=0.6) * 0.8, T_IMPLODE, gain=0.5, send=0.0)
    # PEAK: rainbow shockwave = boom + sparkle burst
    m.add(S.impact(2.6, weight=0.9, bright=1.2, metal=0.6, seed=81, sub_f=(90, 38)), T_PEAK, gain=0.62, send=0.3)
    m.add(S.shimmer(2.5, root=S.midi(84), density=34, seed=83, rise=0.12), T_PEAK, gain=0.30, send=0.5)
    m.add(S.whoosh(0.5, peak=0.15, f_lo=9000, f_hi=1500, q=0.8, pan_from=0, pan_to=0, seed=85, tail_f=300), T_PEAK,
          gain=0.35, send=0.3)
    # FLASH crack + SLAM: the huge hit with the resolved final sting
    m.add(S.sos(S.noise(0.08, "white", 87), "highpass", 3000) * S.env_exp(0.08, 0.0005, 0.018), T_FLASH, gain=0.5,
          send=0.4)
    m.add(S.whoosh(0.14, peak=0.95, f_lo=1500, f_hi=8000, q=0.8, pan_from=0, pan_to=0, seed=89), T_SLAM - 0.13,
          gain=0.5, send=0.1)
    m.add(S.impact(3.6, weight=1.6, bright=1.1, metal=1.0, seed=91, sub_f=(95, 30)), T_SLAM, gain=1.0, send=0.35)
    chord = [S.midi(38), S.midi(45), S.midi(50), S.midi(54), S.midi(57), S.midi(64)]
    m.add(S.sting(chord, 3.7, bright=1.0, seed=93), T_SLAM, gain=0.55, send=0.4)
    # ASTRIS slam (second hit) + PRODUCTIONS shimmer swipe
    m.add(S.whoosh(0.2, peak=0.92, f_lo=800, f_hi=7000, q=1.0, pan_from=-0.8, pan_to=0.0, seed=95), T_ASTRIS - 0.18,
          gain=0.4, send=0.2)
    m.add(S.impact(2.0, weight=0.6, bright=1.0, metal=0.5, seed=97, sub_f=(80, 45)), T_ASTRIS, gain=0.45, send=0.3)
    m.add(S.shimmer(2.6, root=S.midi(81), density=26, seed=99, rise=0.5), T_PROD, gain=0.22, send=0.6)
    # glint chime in the hold and a final airy tail
    m.add(S.chime(S.midi(90), 1.9, decay=0.9), T_GLINT + 0.35, gain=0.13, pan=0.3, send=0.6)
    m.add(S.chime(S.midi(97), 1.6, decay=0.7), T_GLINT + 0.42, gain=0.07, pan=0.45, send=0.6)
    m.duck(T_HUSH, T_PEAK, depth_db=-40, fade=0.06)       # the held breath before the detonation
    mix = m.master(ir_seconds=2.8, wet=0.9, peak_db=-1.5, tail_fade=0.12)
    S.report(mix, NAME)
    return mix


def main():
    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    C.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    if "--test" in sys.argv:
        fr = [int(a) for a in sys.argv[2].split(",")] if len(sys.argv) > 2 else \
            [12, 40, 70, 100, 125, 136, 142, 145, 147, 150, 153, 160, 170, 200, 239]
        print(C.save_test_frames("intro1", frame, fr))
        return
    wav = C.AUDIO_DIR / f"{NAME}.wav"
    S.write_wav24(wav, audio())
    C.render_video(NAME, N, frame, wav, workers=3)


if __name__ == "__main__":
    main()
