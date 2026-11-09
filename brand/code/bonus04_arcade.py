"""
ASTRIS PRODUCTIONS - Bonus 04: RETRO ARCADE - "LEVEL UP" (6.0 s)

A CRT glows with a scrolling pixel starfield and a blinking INSERT COIN. A coin drops: the logo arrives as
chunky 8-bit pixel art in four colours. Every few beats it LEVELS UP - the pixels halve in size and the palette
grows (4 > 8 > 16 > 64 > 256 colours > near-smooth), the score ticks up, the chiptune climbs a key - until a
flash, the CRT curvature snaps flat and everything lands in full HD: a glossy rainbow logo and a chunky
arcade-title ASTRIS. The music levels up too, from square waves into a big, warm, wide synth chord.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import signal

import common as C
import kit as K
import sound as S
import sfx as X

cv2 = C.cv2
NAME = "astris-bonus-04"
DUR = 6.0
FPS = C.FPS
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=2401, grain=0.014, vignette=0.30, vig_inner=0.35, grain_size=1.0, grain_floor=0.2)
INK = K.rgb("#140726")

lock = K.Lockup2(LOGO, logo_h=640, lines=[("bowlby-one-400", "ASTRIS", 190, 0.08, None),
                                            ("montserrat-500", "PRODUCTIONS", 50, 0.0, 1.0)],
                 gaps=(120, 72), centre=(W / 2, H / 2 + 30))

# level: (start time, pixel size, palette)
T_COIN = 0.55
LEVELS = [(0.75, 60, "p4"), (1.35, 30, "p8"), (1.85, 15, "p16"), (2.30, 8, "rgb222"), (2.70, 4, "rgb332"),
          (3.05, 2, "rgb555"), (3.40, 1, None)]
T_HD = LEVELS[-1][0]
T_SHINE0, T_SHINE1 = 3.95, 4.55
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16 - 0.5
P4 = ["#0b0826", "#ff3fa4", "#3fd0ff", "#ffffff"]
P8 = P4 + ["#ffd23f", "#7a3fff", "#2a1a6e", "#ff7a2f"]
P16 = P8 + ["#3fff7a", "#ff2f2f", "#2f7aff", "#ffa0d0", "#a0fff0", "#5a2f8f", "#000000", "#170d40"]
PALS = {k: np.array([K.rgb(h) for h in v], np.float32) for k, v in (("p4", P4), ("p8", P8), ("p16", P16))}
SPREAD = {"p4": 0.42, "p8": 0.30, "p16": 0.22}
UNI = {"rgb222": (4, 4, 4), "rgb332": (8, 8, 4), "rgb555": (32, 32, 32)}


# ------------------------------------------------------------------------------------------------
# the HD lockup (premultiplied RGBA), built once
# ------------------------------------------------------------------------------------------------
def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def shade(m, fill, width, height, spec_k=0.9):
    n = K.bevel_normals(m, width, height)
    L = np.array([-0.45, -0.75, 0.55], np.float32)
    L /= np.linalg.norm(L)
    Hh = (L + np.array([0, 0, 1], np.float32))
    Hh /= np.linalg.norm(Hh)
    dif = np.clip((n * L).sum(-1), 0, 1)
    sp = np.clip((n * Hh).sum(-1), 0, 1) ** 40
    return fill * (0.55 + 0.6 * dif[..., None]) + sp[..., None] * spec_k


def build_lockup():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rgb = np.zeros((H, W, 3), np.float32)
    a = np.zeros((H, W), np.float32)

    def over(col, alpha):
        nonlocal rgb, a
        al = np.clip(alpha, 0, 1)
        rgb = rgb * (1 - al[..., None]) + col * al[..., None]
        a = a + al * (1 - a)

    lm = C.poly_mask_ss(lock.logo_polys(), ss=2)
    am = K.letters_mask(lock.line(0))
    pm = K.letters_mask(lock.line(1))
    both = np.maximum(lm, am)
    # drop shadow, then thick ink outline
    sh = cv2.GaussianBlur(cv2.dilate(both, disk(12)), (0, 0), 2.0)
    sh = np.roll(np.roll(sh, 18, 0), 18, 1)
    over(K.rgb("#07021a"), sh * 0.85)
    over(INK, np.clip(cv2.GaussianBlur(cv2.dilate(both, disk(13)), (0, 0), 1.0), 0, 1))
    over(INK, np.clip(cv2.GaussianBlur(cv2.dilate(pm, disk(8)), (0, 0), 1.0), 0, 1))
    # glossy rainbow logo
    allp = np.concatenate(lock.logo_polys())
    v = np.clip((yy - allp[:, 1].min()) / (allp[:, 1].max() - allp[:, 1].min()), 0, 1)
    lf = C.spectrum(v * 0.92) * 1.0 + 0.18 * np.clip(1 - v * 2.2, 0, 1)[..., None]
    over(shade(lm, lf, 20, 55), lm)
    # arcade-title ASTRIS: yellow > orange > hot pink, bevelled
    ap = np.concatenate([q for L in lock.line(0) for q in L["polys"]])
    va = np.clip((yy - ap[:, 1].min()) / (ap[:, 1].max() - ap[:, 1].min()), 0, 1)
    keys = [(0.0, "#fff27a"), (0.45, "#ffb21f"), (1.0, "#ff3f7a")]
    af = np.stack([np.interp(va, [k for k, _ in keys], [K.rgb(h)[c] for _, h in keys]) for c in range(3)], -1).astype(np.float32)
    over(shade(am, af, 14, 40, 0.7), am)
    over(K.rgb("#f6f2ff"), pm)
    return (rgb * a[..., None]).astype(np.float32), a.astype(np.float32), lm, am, np.maximum(np.maximum(lm, am), pm)


LOCK_P, LOCK_A, LOGO_M, ASTRIS_M, FILL_M = build_lockup()
SHINE_M = np.maximum(LOGO_M, ASTRIS_M)

# ------------------------------------------------------------------------------------------------
# background: gradient + three layers of stars scrolling left (parallax)
# ------------------------------------------------------------------------------------------------
_r = np.random.default_rng(2402)
STARS = [(_r.uniform(0, 1, (n, 2)).astype(np.float32), sp, br) for n, sp, br in ((260, 0.010, 0.35), (120, 0.028, 0.6), (45, 0.07, 1.0))]


def bg_low(t, b):
    """The pixel-era background: a dark, nearly flat sky (so small palettes keep it clean) and star pixels -
    only the brightest, nearest stars on the chunkiest grids, more of them as the resolution climbs."""
    h, w = H // b, W // b
    v = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    img = np.broadcast_to(K.rgb("#050318") * (1 - v) + K.rgb("#110826") * v, (h, w, 3)).copy()
    for li, (pos, sp, br) in enumerate(STARS):
        if (b >= 30 and li < 2) or (b >= 15 and li < 1):
            continue
        if b >= 30:
            pos = pos[:18]
        x = ((pos[:, 0] - sp * t * 16) % 1.0) * w
        y = pos[:, 1] * h
        xi, yi = np.clip(x.astype(int), 0, w - 1), np.clip(y.astype(int), 0, h - 1)
        img[yi, xi] = np.maximum(img[yi, xi], br)
    return img


def bg_hd(t):
    v = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    img = np.broadcast_to(K.rgb("#050318") * (1 - v) + K.rgb("#1a0d3c") * v, (H, W, 3)).copy()
    img += NEB
    st = np.zeros((H, W), np.uint8)
    for pos, sp, br in STARS:
        x = ((pos[:, 0] - sp * t * 16) % 1.0) * W
        y = pos[:, 1] * H
        for xi, yi in zip(x, y):
            cv2.circle(st, (int(xi * 16), int(yi * 16)), int(16 * (2.0 + 3.0 * br)), int(255 * br), -1, cv2.LINE_AA, 4)
    s = st.astype(np.float32) / 255
    return img + (s + cv2.GaussianBlur(s, (0, 0), 4) * 0.8)[..., None] * K.rgb("#e8ecff")


def _neb():
    yy = np.linspace(-1, 1, H, dtype=np.float32)[:, None]
    xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
    return (np.exp(-(xx ** 2 * 1.2 + (yy + 0.1) ** 2 * 2.0) * 2.2) * 0.22)[..., None] * K.rgb("#5a2fa0")


NEB = _neb().astype(np.float32)


# ------------------------------------------------------------------------------------------------
# quantise + dither (Bayer 4x4)
# ------------------------------------------------------------------------------------------------
def quantise(img, mode, dmask=None):
    """Snap to the level's palette. Dithering is applied only where dmask is set (the artwork), so the
    background stays clean and flat like a real 8-bit screen."""
    h, w = img.shape[:2]
    d = np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w]
    if dmask is not None:
        d = d * dmask
    if mode in PALS:
        pal = PALS[mode]
        c = np.clip(img + d[..., None] * SPREAD[mode], 0, 1)
        dist = ((c[:, :, None, :] - pal[None, None]) ** 2).sum(-1)
        return pal[np.argmin(dist, axis=-1)]
    lv = np.array(UNI[mode], np.float32) - 1
    c = np.clip(img + d[..., None] / lv, 0, 1)
    return np.round(c * lv) / lv


# ------------------------------------------------------------------------------------------------
# HUD on an 8-px grid (480 x 270 cells)
# ------------------------------------------------------------------------------------------------
HF = {s: ImageFont.truetype(str(C.FONT_DIR / "vt323-400.ttf"), s) for s in (18, 20, 28)}


def hud(t, level_idx, score):
    im = Image.new("L", (W // 8, H // 8), 0)
    sh = Image.new("L", (W // 8, H // 8), 0)
    d, ds = ImageDraw.Draw(im), ImageDraw.Draw(sh)
    d.fontmode = ds.fontmode = "1"

    def txt(xy, s, size, anchor="la"):
        ds.text((xy[0] + 1, xy[1] + 1), s, font=HF[size], fill=255, anchor=anchor)
        d.text(xy, s, font=HF[size], fill=255, anchor=anchor)

    if t < LEVELS[0][0]:
        if (t < 0.25) or (0.40 <= t):
            txt((W // 16, H // 16), "INSERT COIN", 28, "mm")
    else:
        lv = "HD" if level_idx == len(LEVELS) - 1 else f"LV {level_idx + 1}"
        txt((14, 10), lv, 20)
        txt((W // 8 - 14, 10), f"SCORE {score:06d}", 20, "ra")
        tl = LEVELS[level_idx][0]
        k = t - tl
        if k < 0.42 and int(k / 0.07) % 2 == 0:
            txt((W // 16, 34), "START!" if level_idx == 0 else ("LEVEL UP!" if level_idx < len(LEVELS) - 1 else "HD!"), 20, "mm")
    a = cv2.resize(np.asarray(im, np.float32) / 255, (W, H), interpolation=cv2.INTER_NEAREST)
    s = cv2.resize(np.asarray(sh, np.float32) / 255, (W, H), interpolation=cv2.INTER_NEAREST)
    return a, s


def score_at(t):
    sc = 0
    for k, (tl, _, _) in enumerate(LEVELS):
        if t >= tl:
            gain = 1000 * (k + 1) ** 2
            sc += int(gain * C.clamp((t - tl) / 0.35))
    return sc


def level_at(t):
    idx = -1
    for k, (tl, _, _) in enumerate(LEVELS):
        if t >= tl:
            idx = k
    return idx


def frame(i):
    t = i / FPS
    idx = level_at(t)
    if idx == -1:                                           # attract mode: stars + INSERT COIN
        img = cv2.resize(quantise(bg_low(t, 15), "p8", 0.0), (W, H), interpolation=cv2.INTER_NEAREST)
    elif idx < len(LEVELS) - 1:
        tl, b, mode = LEVELS[idx]
        k = C.clamp((t - tl) / 0.22)
        dy = int(-34 * math.sin(math.pi * k))                # a little hop on every level-up
        lp = np.roll(LOCK_P, dy, 0)
        la = np.roll(LOCK_A, dy, 0)
        h, w = H // b, W // b
        lp_s = cv2.resize(lp, (w, h), interpolation=cv2.INTER_AREA)
        la_s = cv2.resize(la, (w, h), interpolation=cv2.INTER_AREA)
        low = bg_low(t, b) * (1 - la_s[..., None]) + lp_s
        fm = cv2.resize(np.roll(FILL_M, dy, 0), (w, h), interpolation=cv2.INTER_AREA)
        img = cv2.resize(quantise(low, mode, np.clip(fm * 2, 0, 1)), (W, H), interpolation=cv2.INTER_NEAREST)
    else:
        img = bg_hd(t) * (1 - LOCK_A[..., None]) + LOCK_P
        s = C.clamp((t - T_SHINE0) / (T_SHINE1 - T_SHINE0))
        if 0 < s < 1:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            band = np.exp(-(((xx - 900) + (yy - 400) * 0.6 - s * 2400) / 90) ** 2)
            img += (band * SHINE_M * 0.9)[..., None]
    # HUD (fades out once we're in HD)
    hud_k = 1.0 - C.smoothstep(T_HD + 0.45, T_HD + 0.85, t)
    if hud_k > 0:
        a, s = hud(t, max(idx, 0), score_at(t))
        img = img * (1 - (s * hud_k)[..., None]) + K.rgb("#ff2f9a") * (s * hud_k)[..., None]
        img = img * (1 - (a * hud_k)[..., None]) + K.rgb("#ffffff") * (a * hud_k)[..., None]
    # level-up flash
    for k, (tl, _, _) in enumerate(LEVELS):
        if 0 <= t - tl < 0.3:
            img = img + (0.55 if k < len(LEVELS) - 1 else 1.2) * math.exp(-(t - tl) / 0.06)
    if 0 <= t - T_COIN < 0.2:
        img = img + 0.25 * math.exp(-(t - T_COIN) / 0.05)
    # the CRT: scanlines, glow and curvature - gone in a snap at HD
    crt = 1.0 - C.smoothstep(T_HD, T_HD + 0.18, t)
    if crt > 0:
        glow = cv2.GaussianBlur(cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), 3)
        c = img + cv2.resize(glow, (W, H)) * 0.35
        c = K.scanlines(c, period=6, depth=0.32)
        c = K.crt_curve(c, 0.055)
        img = img * (1 - crt) + c * crt
    return POST.finish(img, i, bloom=0.25 if t >= T_HD else 0.12, threshold=0.85, grain=None if t >= T_HD else 0.008)


# ------------------------------------------------------------------------------------------------
# sound: chiptune that levels up into a big synth chord
# ------------------------------------------------------------------------------------------------
def sq(f, dur, duty=0.25, crush=True):
    t = S.tt(dur)
    x = np.where((t * f) % 1.0 < duty, 1.0, -1.0)
    x = S.sos(x, "lowpass", 9000, 2)
    return x


def tri(f, dur):
    t = S.tt(dur)
    x = 2 * np.abs(2 * ((t * f) % 1.0) - 1) - 1
    return np.round(x * 7.5) / 7.5                          # 4-bit stepped triangle


def chip_env(n, dec=0.12, steps=15):
    e = np.exp(-np.arange(n) / (S.SR * dec))
    return np.round(e * steps) / steps


def noise_hit(dur, rate=12000, seed=0):
    r = np.random.default_rng(seed)
    n = int(dur * S.SR)
    hold = int(S.SR / rate)
    x = np.repeat(r.choice([-1.0, 1.0], n // hold + 1), hold)[:n]
    return x * chip_env(n, dur * 0.3)


def audio():
    m = S.Mix(DUR)
    beat = 0.4
    # attract-mode blips, the coin
    for tb in (0.0, 0.40):
        m.add(sq(S.midi(84), 0.06, 0.5) * chip_env(int(0.06 * S.SR), 0.03), tb, gain=0.12, send=0.05)
    for k, nn in enumerate((84, 88, 91, 96)):
        m.add(sq(S.midi(nn), 0.05, 0.25) * chip_env(int(0.05 * S.SR), 0.04), T_COIN + k * 0.035, gain=0.16, send=0.08)
    # the chiptune: each level a whole tone higher, faster arpeggios as it levels up
    roots = [48, 50, 52, 54, 56, 58]
    for k in range(len(LEVELS) - 1):
        t0, t1 = LEVELS[k][0], LEVELS[k + 1][0]
        r = roots[k]
        triad = [r, r + 4, r + 7, r + 12]
        # level-up jingle
        for j, nn in enumerate(triad + [r + 16]):
            m.add(sq(S.midi(nn + 12), 0.045, 0.5) * chip_env(int(0.045 * S.SR), 0.05), t0 + j * 0.028, gain=0.14, pan=0.2, send=0.08)
        m.add(noise_hit(0.12, 6000, 2410 + k), t0, gain=0.10, send=0.05)
        step = 0.1 if k < 3 else 0.05
        tt_ = t0 + 0.15
        j = 0
        while tt_ < t1 - 0.02:
            nn = triad[j % 4] + 24
            m.add(sq(S.midi(nn), step * 0.9, 0.125) * chip_env(int(step * 0.9 * S.SR), 0.06), tt_, gain=0.07, pan=-0.3, send=0.05)
            tt_ += step
            j += 1
        tb = t0
        while tb < t1 - 0.02:
            m.add(tri(S.midi(r - 12), beat * 0.45) * chip_env(int(beat * 0.45 * S.SR), 0.2), tb, gain=0.22, send=0.02)
            m.add(noise_hit(0.04, 14000, int(tb * 1000)), tb + beat / 2, gain=0.05, send=0.02)
            tb += beat / 2
    # HD: the sound levels up too
    m.add(S.reverse_swell(0.7, 1.0, 2420, 2400), T_HD - 0.7, gain=0.16, send=0.3)
    m.add(S.impact(2.6, weight=0.9, bright=0.7, metal=0.2, seed=2421), T_HD, gain=0.42, send=0.3)
    chord = [S.midi(n) for n in (48, 55, 60, 64, 67, 72, 76)]
    m.add(X.synth_stab(chord, 2.6, seed=2422, bright=0.8), T_HD, gain=0.34, send=0.45)
    m.add(X.strings(chord[1:], 2.6, attack=0.08, release=1.2, seed=2423, bright=0.9), T_HD, gain=0.22, send=0.6)
    m.add(S.shimmer(1.4, root=1800, density=24, level=1.0, seed=2424, rise=0.2), T_HD + 0.05, gain=0.08, send=0.6)
    m.add(X.glass_ping(S.midi(96), 1.6), T_SHINE0 + 0.15, gain=0.08, pan=0.3, send=0.6)
    mix = m.master(ir_seconds=2.0, wet=0.6, peak_db=-1.5, tail_fade=0.35)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [26, 40, 50, 60, 70, 78, 86, 143], tag="bonus04")
