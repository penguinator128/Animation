"""
ASTRIS PRODUCTIONS - Ident 06: GLITCH (3.0 s, very fast)

Corrupted signal: the frame tears - RGB channels split, horizontal slices jump, rows get pixel-sorted, macro-
blocks smear (datamosh), interlaced lines slip, whole frames flash negative or stutter-repeat - in acid
chartreuse, hot magenta and electric cyan on black. Then it LOCKS into one perfectly clean frame: white logo,
chunky mono type, a blinking terminal cursor.
Sound: digital stutter, static bursts, bit-crushed chirps, then a sharp lock-in hit and a clean tone.
"""
import math

import numpy as np

import common as C
import kit as K
import sfx as X
import sound as S

cv2 = C.cv2
NAME = "astris-ident-06"
DUR = 3.0
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=606, grain=0.02, vignette=0.30)
LOCK_F = 46                                   # frame 46 = 1.917 s: the clean lock
T_LOCK = LOCK_F / C.FPS
ACID, MAG, CYAN = K.rgb("#c6ff00"), K.rgb("#ff1fd1"), K.rgb("#00f0ff")

lock = K.Lockup2(LOGO, logo_h=760, lines=[("rubik-mono-one-400", "ASTRIS", 140, 0.18, None),
                                            ("space-mono-700", "PRODUCTIONS", 48, 0.0, 1.0)],
                 gaps=(150, 74), centre=(W / 2, H / 2 - 10))
LOGO_M = C.poly_mask_ss(lock.logo_polys(), ss=2)
A_M = K.letters_mask(lock.line(0))
P_letters = lock.line(1)
P_M = K.letters_mask(P_letters)
last = P_letters[-1]
CUR_X = last["centre"][0] + last["width"] / 2 + 40
CUR_Y = lock.baselines[1]
CURSOR = np.zeros((H, W), np.float32)
cv2.rectangle(CURSOR, (int(CUR_X), int(CUR_Y - 46)), (int(CUR_X + 26), int(CUR_Y + 2)), 1.0, -1, cv2.LINE_AA)

CLEAN = np.zeros((H, W, 3), np.float32) + K.rgb("#030305")
CLEAN = K.comp(CLEAN, LOGO_M, [0.96, 0.97, 1.0])
CLEAN = K.comp(CLEAN, A_M, [0.96, 0.97, 1.0])
CLEAN = K.comp(CLEAN, P_M, ACID)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def pixel_sort(img, r, bands, g):
    out = img
    for _ in range(bands):
        y0 = int(r.integers(0, H - 40))
        h = int(r.integers(20, int(40 + 260 * g)))
        x0 = int(r.integers(0, W // 2))
        x1 = int(min(W, x0 + r.integers(400, 2200)))
        seg = out[y0:y0 + h, x0:x1]
        lum = seg.mean(axis=2)
        idx = np.argsort(lum, axis=1)
        if r.uniform() < 0.5:
            idx = idx[:, ::-1]
        out[y0:y0 + h, x0:x1] = np.take_along_axis(seg, idx[..., None], axis=1)
    return out


def slices(img, r, n, amp):
    out = img.copy()
    y = 0
    while y < H:
        h = int(r.integers(8, 160))
        if r.uniform() < n:
            out[y:y + h] = np.roll(img[y:y + h], int(r.normal(0, amp)), axis=1)
        y += h
    return out


def datamosh(img, r, n):
    out = img.copy()
    B = 64
    for _ in range(n):
        x, y = int(r.integers(0, W // B)) * B, int(r.integers(0, H // B)) * B
        w, h = int(r.integers(1, 6)) * B, int(r.integers(1, 3)) * B
        mode = r.uniform()
        if mode < 0.4:                       # smear one column of pixels across the block
            col = img[y:y + h, x:x + 1]
            out[y:y + h, x:x + w] = col
        elif mode < 0.75:                    # copy a block from elsewhere
            sx, sy = int(r.integers(0, W - w)), int(r.integers(0, H - h))
            out[y:y + h, x:x + w] = img[sy:sy + h, sx:sx + w][: out[y:y + h, x:x + w].shape[0], : out[y:y + h, x:x + w].shape[1]]
        else:                                # garbage colour block
            c = [ACID, MAG, CYAN][int(r.integers(0, 3))] * r.uniform(0.3, 1.0)
            blk = out[y:y + h, x:x + w]
            blk[:] = c * (0.6 + 0.4 * (r.random(blk.shape[:2]) > 0.5))[..., None]
    return out


def glitch_frame(i):
    r = np.random.default_rng(6000 + i)
    k = i / LOCK_F
    g = 0.55 + 0.45 * r.uniform() if i < 8 else (0.25 + 0.6 * r.uniform() ** 2)
    if LOCK_F - 7 <= i < LOCK_F - 3:          # the stutter just before the lock: one frame repeats
        r = np.random.default_rng(6000 + LOCK_F - 7)
        g = 0.9
    elif i >= LOCK_F - 3:                     # final convulsion
        g = 1.0
    base = CLEAN.copy()
    # the logo/type flicker in and out, and sometimes swap for a colour channel ghost
    if r.uniform() < 0.25 * g:
        base = np.zeros_like(base) + K.rgb("#030305")
    if r.uniform() < 0.3:
        base = base * np.array([[ACID, MAG, CYAN][int(r.integers(0, 3))]])[0]
    img = slices(base, r, 0.35 + 0.5 * g, 30 + 380 * g)
    if r.uniform() < 0.8:
        img = pixel_sort(img, r, int(2 + 6 * g), g)
    img = datamosh(img, r, int(10 + 60 * g))
    sh = 10 + 90 * g
    img = K.chroma_shift(img, r.normal(0, sh), r.normal(0, sh), r.normal(0, sh * 0.2))
    # interlace slip and scan noise
    if r.uniform() < 0.6:
        img[1::2] = np.roll(img[1::2], int(r.normal(0, 24 * g)), axis=1)
    if r.uniform() < 0.5:
        y0 = int(r.integers(0, H - 200))
        band = img[y0:y0 + 120]
        band[:] = band * 0.4 + (r.random(band.shape[:2])[..., None] * 0.8) * [CYAN, MAG, ACID][int(r.integers(0, 3))]
    if r.uniform() < 0.12:
        img = 1.0 - np.clip(img, 0, 1)          # negative flash
    img = K.scanlines(img, period=6, depth=0.35)
    return img


def frame(i):
    t = i / C.FPS
    if i < LOCK_F:
        img = glitch_frame(i)
        return POST.finish(img, i, bloom=0.35, threshold=0.7)
    img = CLEAN.copy()
    tl = t - T_LOCK
    # lock-in: a single bright scanline sweeps once, then everything is perfectly still
    if tl < 0.12:
        y = H * (tl / 0.12)
        img += (np.exp(-((yy[:, :1] - y) / 5) ** 2) * 1.6 + np.exp(-((yy[:, :1] - y) / 60) ** 2) * 0.12)[..., None] * np.array([0.9, 1.0, 0.95], np.float32)
    if (int(t * 2.4) % 2 == 0) and tl > 0.25:
        img = K.comp(img, CURSOR, ACID)
    return POST.finish(img, i, bloom=0.35 + 0.25 * math.exp(-tl / 0.12), threshold=0.7)


def audio():
    m = S.Mix(DUR)
    r = np.random.default_rng(66)
    t = 0.0
    while t < T_LOCK - 0.08:
        kind = r.uniform()
        d = r.uniform(0.03, 0.14)
        if kind < 0.35:
            x = X.static_burst(d, seed=int(t * 1000), crush=int(r.integers(3, 7)))
        elif kind < 0.6:
            x = X.stutter(X.beep(r.uniform(400, 3200), 0.03), 0.015, int(r.integers(3, 8)))
        elif kind < 0.8:
            f0 = r.uniform(200, 2000)
            tt = S.tt(d)
            x = np.sign(np.sin(2 * np.pi * np.cumsum(f0 * (1 + 3 * tt / d)) / S.SR)) * 0.4
        else:
            x = S.sos(S.noise(d, "white", int(t * 997)), "bandpass", [r.uniform(300, 2000), r.uniform(3000, 9000)])
        m.add(x, t, gain=r.uniform(0.15, 0.38), pan=r.uniform(-0.8, 0.8), send=0.08)
        t += d * r.uniform(0.6, 1.3)
    hum = np.sin(2 * np.pi * 60 * S.tt(T_LOCK)) * 0.2 + S.sos(S.noise(T_LOCK, "white", 61), "highpass", 5000) * 0.05
    m.add(hum, 0.0, gain=0.25, send=0.0)
    m.add(S.reverse_swell(0.25, seed=62, f=6000), T_LOCK - 0.25, gain=0.3, send=0.0)
    m.duck(T_LOCK - 0.06, T_LOCK, depth_db=-36, fade=0.02)
    m.add(S.impact(1.2, weight=0.8, bright=1.4, metal=0.2, seed=63, sub_f=(110, 45)), T_LOCK, gain=0.75, send=0.2)
    m.add(X.synth_stab([S.midi(57), S.midi(64), S.midi(69), S.midi(73), S.midi(76)], 1.0, seed=64, bright=0.7), T_LOCK, gain=0.35, send=0.3)
    tone = np.sin(2 * np.pi * 1760 * S.tt(0.9)) * S.env_exp(0.9, 0.005, 0.35) * 0.3
    m.add(tone, T_LOCK + 0.02, gain=0.25, pan=0.2, send=0.4)
    for k in range(3):
        m.add(X.beep(2400, 0.02) * 0.3, T_LOCK + 0.42 + k * 0.417, gain=0.12, pan=0.5, send=0.2)   # the cursor blinking
    mix = m.master(ir_seconds=1.2, wet=0.5, peak_db=-1.5, tail_fade=0.1)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [0, 5, 10, 16, 22, 28, 34, 40, 43, 45, 46, 47, 52, 71], tag="ident06")
