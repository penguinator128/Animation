"""
ASTRIS PRODUCTIONS - Ident 10: RETRO 70s SUNBURST (5.0 s, medium and groovy)

A warm 1970s poster: a big sunburst spinning out behind everything, and five stacked stripes - orange,
mustard, brown, cream and a pop of teal - that sweep across the screen on a curve, swirl in and become the
stripes inside the logo. The logo pops in with a bounce; ASTRIS slides in letter by letter in chunky
Shrikhand with a stacked-stripe outline, PRODUCTIONS in Righteous. Printed on cream poster stock with slight
ink misregistration, halftone in the shadows and a little paper wear.
Sound: a funky bass slide, wah-guitar scratches, a cheerful brass hit, finger snaps and a tambourine shimmer.
"""
import math

import numpy as np

import common as C
import kit as K
import sfx as X
import sound as S

cv2 = C.cv2
NAME = "astris-ident-10"
DUR = 5.0
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=1010, grain=0.03, vignette=0.36, grain_size=1.2)
STRIPES = [K.rgb(h) for h in ("#e8641e", "#f2a922", "#7a3e1d", "#f6e7c8", "#1f9e98")]   # orange, mustard, brown, cream, teal
PAPER = K.paper(H, W, K.rgb("#f3e3c4"), seed=101, fibres=0.02, grain=0.03, mottle=0.08)
BROWN = K.rgb("#4a2412")
T_SWEEP0, T_SWEEP1, T_POP, T_TXT0, T_PROD = 0.15, 1.45, 1.55, 2.05, 2.95

lock = K.Lockup2(LOGO, logo_h=700, lines=[("shrikhand-400", "ASTRIS", 180, 0.06, None),
                                            ("righteous-400", "PRODUCTIONS", 60, 0.0, 1.0)],
                 gaps=(140, 70), centre=(W / 2, H / 2 - 10))
LC = lock.logo_c
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
ANG = np.arctan2(yy - LC[1], xx - LC[0])
RAD = np.hypot(xx - LC[0], yy - LC[1])
WEAR = np.clip((K.fbm(H // 4, W // 4, 102, 6) - 0.62) * 6, 0, 1)
WEAR = cv2.resize(WEAR, (W, H))


def sunburst(t):
    spin = 0.12 * t + 0.25 * C.expo_out(t / 1.5, 4)
    rays = (np.sin((ANG + spin) * 16) > 0).astype(np.float32)
    rays = cv2.GaussianBlur(rays, (0, 0), 1.0)
    grow = C.expo_out((t - 0.0) / 1.2, 5)
    reach = np.clip((grow * 3600 - RAD) / 80, 0, 1)
    return rays * reach


def stripe_band(t):
    """Five stripes swept along a curve that swirls into the logo's centre. Returns (index map, mask)."""
    k = C.clamp((t - T_SWEEP0) / (T_SWEEP1 - T_SWEEP0))
    e = C.expo_in_out(k, 3.5)
    # the band's centreline: enters from the left, arcs up over the frame, spirals down into the logo
    th = np.linspace(0, 1, 160)
    path = np.stack([np.interp(th, [0, 0.35, 0.65, 1.0], [-900, W * 0.35, W * 0.72, LC[0]]),
                     np.interp(th, [0, 0.35, 0.65, 1.0], [H * 0.78, H * 0.18, H * 0.30, LC[1]])], 1)
    path = cv2.GaussianBlur(path.astype(np.float32).reshape(-1, 1, 2), (1, 41), 12).reshape(-1, 2)
    head = int(1 + e * (len(path) - 1))
    tail = max(0, int(head - 70))
    seg = path[tail:head + 1]
    width = 860 * (1 - 0.6 * e)
    lab = np.full((H // 2, W // 2), -1, np.int32)
    if len(seg) >= 2:
        for j in range(5):
            off = (j - 2) * width / 5
            pts = []
            for a, b in zip(seg[:-1], seg[1:]):
                d = b - a
                n = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-6)
                pts.append(a + n * off)
            pts.append(seg[-1] + n * off)
            cv2.polylines(lab, [np.round(np.array(pts) / 2 * 16).astype(np.int32)], False, j, int(width / 5 / 2 + 1), cv2.LINE_8, 4)
    lab = cv2.resize(lab.astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST).astype(np.int32)
    return lab


def ink(img, mask, col, dx=0.0, dy=0.0, wear=True):
    """Lay down one ink, slightly misregistered like an old print run."""
    if dx or dy:
        mask = cv2.warpAffine(mask, np.float32([[1, 0, dx], [0, 1, dy]]), (W, H), borderValue=0)
    if wear:
        mask = mask * (1 - 0.45 * WEAR)
    return img * (1 - mask[..., None]) + np.asarray(col, np.float32) * mask[..., None]


def frame(i):
    t = i / C.FPS
    img = PAPER.copy()
    sb = sunburst(t)
    rcol = (K.rgb("#f6b23c")[None, None] * (1 - np.clip(RAD / 2400, 0, 1))[..., None] +
            K.rgb("#e8641e")[None, None] * np.clip(RAD / 2400, 0, 1)[..., None])
    img = img * (1 - (sb * 0.78)[..., None]) + rcol * (sb * 0.78)[..., None]
    # a warm sun disc behind the logo, ringed in brown
    disc = np.clip((820 - RAD) / 3, 0, 1) * C.expo_out((t - 0.1) / 0.9, 4)
    img = ink(img, np.clip((838 - RAD) / 3, 0, 1) * (disc > 0), BROWN)
    img = ink(img, disc, K.rgb("#fbe6bd"), 3, -2, wear=False)
    # the sweeping stripes
    if T_SWEEP0 <= t < T_POP + 0.1:
        lab = stripe_band(t)
        fade = 1 - C.smoothstep(T_POP - 0.1, T_POP + 0.1, t)
        for j, col in enumerate(STRIPES):
            m = (lab == j).astype(np.float32) * fade
            if m.max() > 0:
                img = ink(img, cv2.GaussianBlur(m, (0, 0), 1.2), col, 4 * (j % 2), -3 * (j % 2))
    # the logo pops in with a bounce, filled with the same five stripes
    if t >= T_POP:
        s = C.spring(t - T_POP, 18, 0.38)
        polys = lock.logo_polys(scale=max(s, 0.01))
        m = C.poly_mask_ss(polys, ss=2)
        allp = np.concatenate(polys)
        y0, y1 = allp[:, 1].min(), allp[:, 1].max()
        band = np.clip(((yy - y0) / (y1 - y0) * 5).astype(np.int32), 0, 4)
        fillc = np.zeros((H, W, 3), np.float32)
        for j, col in enumerate(STRIPES):
            fillc[band == j] = col
        # chunky brown outline + offset shadow, then the stripes (misregistered a hair)
        outline = cv2.dilate((m > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))).astype(np.float32)
        outline = cv2.GaussianBlur(outline, (0, 0), 1.0)
        img = ink(img, outline, BROWN, 14, 14)
        img = ink(img, outline, BROWN)
        mm = m * (1 - 0.45 * WEAR)
        mm = cv2.warpAffine(mm, np.float32([[1, 0, -4], [0, 1, 3]]), (W, H), borderValue=0)
        img = img * (1 - mm[..., None]) + fillc * mm[..., None]
    # ASTRIS slides in letter by letter with a stacked-stripe outline; PRODUCTIONS follows
    if t >= T_TXT0:
        def per(k, n):
            kk = C.clamp((t - T_TXT0 - k * 0.09) / 0.42)
            e = 1 - (1 - kk) ** 3
            return {"dx": -380 * (1 - e), "rot": -0.25 * (1 - e), "s": 0.6 + 0.4 * C.spring(t - T_TXT0 - k * 0.09, 20, 0.45)}
        letters = lock.line(0, per)
        alpha = [C.clamp((t - T_TXT0 - k * 0.09) / 0.12) for k in range(len(letters))]
        base = K.letters_mask(letters, alpha=alpha)
        bb = (base > 0.5).astype(np.uint8)
        for j, (rad, col) in enumerate(((30, STRIPES[4]), (22, STRIPES[0]), (14, STRIPES[1]))):
            ring = cv2.dilate(bb, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (rad * 2 + 1, rad * 2 + 1))).astype(np.float32)
            img = ink(img, cv2.GaussianBlur(ring, (0, 0), 1.0), col, 2 * j, 2 * j)
        img = ink(img, base, K.rgb("#fbf1dc"))
    if t >= T_PROD:
        def perp(k, n):
            kk = C.clamp((t - T_PROD - k * 0.035) / 0.3)
            return {"dy": 60 * (1 - (1 - (1 - kk) ** 3))}
        pl = lock.line(1, perp)
        alpha = [C.clamp((t - T_PROD - k * 0.035) / 0.15) for k in range(len(pl))]
        img = ink(img, K.letters_mask(pl, alpha=alpha), BROWN)
    # print finish: halftone in the shadows, paper grain showing through
    lum = img.mean(axis=2)
    dots = K.halftone(np.clip(0.55 - lum, 0, 1) * 0.6, cell=22, angle=0.26)
    img = img * (1 - 0.25 * dots[..., None])
    img = img * (0.94 + 0.06 * (PAPER.mean(axis=2, keepdims=True) / PAPER.mean()))
    return POST.finish(img, i, bloom=0.08, threshold=0.95)


def audio():
    m = S.Mix(DUR)
    m.add(X.vinyl_crackle(DUR, seed=1001), 0.0, gain=0.06, send=0.0)
    # funky bass: a slide up through the sweep, landing on the pop
    bass = X.funk_bass([(0.15, 0.25, 33, None), (0.45, 0.2, 36, None), (0.7, 0.55, 38, 45), (T_POP, 0.35, 45, None),
                        (T_POP + 0.4, 0.2, 43, None), (T_POP + 0.65, 0.2, 45, None), (2.6, 0.3, 40, 45), (3.0, 0.6, 45, None)], DUR, seed=1002)
    m.add(bass, 0.0, gain=0.42, send=0.1)
    for k, tw in enumerate((0.33, 0.83, 1.08, 2.33, 2.58)):
        m.add(X.wah_scratch(0.3, seed=1003 + k, up=k % 2 == 0), tw, gain=0.25, pan=0.45, send=0.2)
    for k, ts in enumerate((0.5, 1.0, 2.5, 3.0)):
        m.add(X.snap(1010 + k), ts, gain=0.25, pan=-0.35, send=0.25)
    m.add(S.whoosh(1.2, peak=0.85, f_lo=200, f_hi=3000, q=0.9, pan_from=-0.8, pan_to=0.2, seed=1020), T_SWEEP0 + 0.1, gain=0.22, send=0.2)
    m.add(X.paper_pop(1021, 0.9), T_POP, gain=0.5, send=0.2)
    brass_ch = [S.midi(57), S.midi(61), S.midi(64), S.midi(69), S.midi(73)]
    m.add(X.brass(brass_ch, 1.4, seed=1022, bright=1.0), T_POP, gain=0.45, send=0.3)
    for k in range(6):
        m.add(X.clack(1300 + 90 * k, 1030 + k, 0.03), T_TXT0 + k * 0.09 + 0.1, gain=0.14, pan=-0.4 + 0.16 * k, send=0.2)
    m.add(X.brass(brass_ch, 1.6, seed=1023, bright=0.8, swell=0.06), T_PROD, gain=0.3, send=0.35)
    m.add(X.tambourine(0.8, 1024), T_PROD + 0.05, gain=0.25, pan=0.4, send=0.3)
    m.add(X.tambourine(0.6, 1025), T_PROD + 0.55, gain=0.15, pan=0.4, send=0.3)
    mix = m.master(ir_seconds=1.4, wet=0.6, peak_db=-1.5, tail_fade=0.12)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [4, 10, 16, 22, 28, 34, 38, 42, 50, 56, 64, 72, 84, 119], tag="ident10")
