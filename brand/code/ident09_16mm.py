"""
ASTRIS PRODUCTIONS - Ident 09: RETRO 16MM FILM (6.0 s, slow to medium)

An old 16mm print going through a projector: heavy clumpy grain, gate weave, flicker, dust, hair and
scratches, faded warm colour (cream highlights, burnt orange, teal-tinted shadows), red halation round the
highlights and a rounded projector gate. A countdown leader sweeps through 3 - 2 - 1 with a beep, a white
pop, then the logo BURNS into the emulsion from its centre with a vintage flare. ASTRIS PRODUCTIONS fades up
in fat-face and slab lettering inside an art-deco frame, and a light leak washes over the end.
Sound: projector whirr and claw clicks, optical crackle, the countdown beep, and a warm brass-and-strings
stinger played through a worn optical soundtrack.
"""
import math

import numpy as np

import common as C
import kit as K
import sfx as X
import sound as S

cv2 = C.cv2
NAME = "astris-ident-09"
DUR = 6.0
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=909, grain=0.075, vignette=0.55, grain_size=1.5, grain_floor=0.35)
NUMS = [("3", 0.15), ("2", 0.75), ("1", 1.35)]
T_POP, T_BURN, T_TXT, T_LEAK = 1.95, 2.30, 3.25, 4.55
CREAM, ORANGE, BROWN = K.rgb("#f2e2bf"), K.rgb("#d9692a"), K.rgb("#1b130d")
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

lock = K.Lockup2(LOGO, logo_h=700, lines=[("abril-fatface-400", "ASTRIS", 170, 0.16, None),
                                            ("rokkitt-700", "PRODUCTIONS", 56, 0.0, 1.0)],
                 gaps=(120, 64), centre=(W / 2, H / 2))
LOGO_M = C.poly_mask_ss(lock.logo_polys(), ss=2)
A_M = K.letters_mask(lock.line(0))
P_M = K.letters_mask(lock.line(1))

# art-deco double frame around the title card, with small corner diamonds
FRAME = np.zeros((H, W), np.float32)
fx0, fy0, fx1, fy1 = 760, 250, W - 760, H - 250
for inset, th in ((0, 6), (26, 3)):
    cv2.rectangle(FRAME, (fx0 + inset, fy0 + inset), (fx1 - inset, fy1 - inset), 1.0, th, cv2.LINE_AA)
for (cx, cy) in ((fx0, fy0), (fx1, fy0), (fx0, fy1), (fx1, fy1)):
    d = np.array([[cx, cy - 40], [cx + 40, cy], [cx, cy + 40], [cx - 40, cy]], np.int32)
    cv2.fillPoly(FRAME, [d], 1.0, cv2.LINE_AA)
GATE = np.zeros((H, W), np.float32)
cv2.rectangle(GATE, (150, 70), (W - 150, H - 70), 1.0, -1)
GATE = cv2.GaussianBlur(GATE, (0, 0), 3)
_g = np.zeros((H // 4, W // 4), np.float32)
r_corner = 34
cv2.rectangle(_g, (40 + r_corner, 18), (W // 4 - 40 - r_corner, H // 4 - 18), 1.0, -1)
cv2.rectangle(_g, (40, 18 + r_corner), (W // 4 - 40, H // 4 - 18 - r_corner), 1.0, -1)
for cx, cy in ((40 + r_corner, 18 + r_corner), (W // 4 - 40 - r_corner, 18 + r_corner),
               (40 + r_corner, H // 4 - 18 - r_corner), (W // 4 - 40 - r_corner, H // 4 - 18 - r_corner)):
    cv2.circle(_g, (cx, cy), r_corner, 1.0, -1, cv2.LINE_AA)
GATE = C.up(cv2.GaussianBlur(_g, (0, 0), 1.5))


def leader(t):
    """Academy-style countdown: circles, crosshair, a sweeping clock hand, the number."""
    img = np.zeros((H, W, 3), np.float32) + 0.62
    cx, cy = W / 2, H / 2
    num, t0 = NUMS[0]
    for n, tn in NUMS:
        if t >= tn:
            num, t0 = n, tn
    k = C.clamp((t - t0) / 0.6)
    ang = np.arctan2(xx - cx, -(yy - cy))
    ang = np.mod(ang, 2 * math.pi)
    swept = (ang < k * 2 * math.pi).astype(np.float32)
    img = img * (1 - 0.35 * swept[..., None])
    lines = np.zeros((H, W), np.float32)
    for rad in (640, 700):
        cv2.circle(lines, (int(cx), int(cy)), rad, 1.0, 7, cv2.LINE_AA)
    cv2.line(lines, (0, int(cy)), (W, int(cy)), 1.0, 5, cv2.LINE_AA)
    cv2.line(lines, (int(cx), 0), (int(cx), H), 1.0, 5, cv2.LINE_AA)
    img = K.comp(img, lines, [0.12, 0.12, 0.12])
    L, _ = K.line_letters("abril-fatface-400", num, 760, cx, cy + 380)
    img = K.comp(img, K.letters_mask(L), [0.08, 0.08, 0.08])
    return img


def title(t):
    img = np.zeros((H, W, 3), np.float32) + BROWN
    img *= (1.15 - 0.4 * np.hypot((xx - W / 2) / W, (yy - H / 2) / H))[..., None]
    tb = t - T_BURN
    # the burn: a glowing front spreads out from the logo's centre through the emulsion
    rad = 1300 * C.expo_out(tb / 0.55, 4)
    d = np.hypot(xx - lock.logo_c[0], yy - lock.logo_c[1])
    revealed = np.clip((rad - d) / 30, 0, 1) * LOGO_M
    edge = np.exp(-((d - rad) / 26) ** 2) * LOGO_M * (1 - C.smoothstep(0.5, 0.9, tb))
    heat = math.exp(-max(tb, 0) / 0.45)
    logo_col = CREAM * (1 + 1.6 * heat) + np.array([0.6, 0.2, 0.0], np.float32) * heat
    img = img * (1 - revealed[..., None]) + logo_col * revealed[..., None]
    img += edge[..., None] * np.array([1.6, 0.8, 0.25], np.float32) * 1.4
    # vintage flare: a soft bloom on the logo and a few ghost rings along a diagonal
    fl = C.pulse(t, T_BURN + 0.12, 0.08, 0.5)
    if fl > 0.01:
        c0 = np.array([lock.logo_c[0] - 150, lock.logo_c[1] - 200])
        r0 = np.hypot(xx - c0[0], yy - c0[1])
        img += (np.exp(-r0 / 260) * 1.2 * fl)[..., None] * np.array([1.0, 0.75, 0.45], np.float32)
        cen = np.array([W / 2, H / 2])
        for k, (f, rr, col) in enumerate(((0.6, 90, (0.5, 0.35, 0.2)), (1.3, 160, (0.3, 0.35, 0.3)), (1.9, 60, (0.6, 0.4, 0.2)))):
            p = cen + (cen - c0) * f
            rg = np.hypot(xx - p[0], yy - p[1])
            ring = np.clip((rr - rg) / 6, 0, 1) * 0.18 * fl
            img += ring[..., None] * np.array(col, np.float32)
    # the title card: deco frame and type dissolve up
    k = C.smoothstep(T_TXT - 0.2, T_TXT + 0.9, t)
    img = K.comp(img, FRAME * k * 0.75, ORANGE * 0.9)
    img = K.comp(img, A_M * C.smoothstep(T_TXT, T_TXT + 0.8, t), CREAM)
    img = K.comp(img, P_M * C.smoothstep(T_TXT + 0.25, T_TXT + 1.0, t), ORANGE * 1.1)
    if t > T_LEAK:
        # the light leak bleeds in from the edges of the film (mostly the right), screen-blended
        lk = C.smoothstep(T_LEAK, T_LEAK + 0.7, t) * (1 - 0.4 * C.smoothstep(T_LEAK + 0.8, DUR, t))
        wob = 0.85 + 0.15 * math.sin(t * 5.3) * math.sin(t * 2.1)
        right = np.exp(-(W - xx) / (950 + 300 * math.sin(t * 1.7) ** 2)) * (0.8 + 0.2 * np.sin(yy / 260 + t * 2)) * 1.7
        left = np.exp(-xx / 300) * 0.35 * (0.5 + 0.5 * np.cos(yy / 340 - t * 1.5))
        a = np.clip((right + left) * lk * wob, 0, 1)[..., None]
        col = np.array([1.0, 0.42, 0.12], np.float32) * (1 - a) + np.array([1.0, 0.78, 0.45], np.float32) * a
        img = 1 - (1 - np.clip(img, 0, 1)) * (1 - a * col * 0.95)
    return img


def grade(img):
    """Faded print: lifted blacks, teal-ish shadows, warm cream highlights, gentle desaturation."""
    lum = img.mean(axis=2, keepdims=True)
    img = img * 0.86 + lum * 0.14
    sh = np.clip(1 - lum * 2.2, 0, 1)
    img = img + sh * np.array([-0.01, 0.025, 0.035], np.float32)
    img = img * np.array([1.04, 0.98, 0.88], np.float32)
    return 0.07 + img * 0.9


def frame(i):
    t = i / C.FPS
    r = np.random.default_rng(9000 + i)
    if t < T_POP:
        img = leader(t)
    elif t < T_POP + 2 / C.FPS:
        img = np.zeros((H, W, 3), np.float32) + 1.3                  # the white pop
    elif t < T_BURN:
        img = np.zeros((H, W, 3), np.float32) + 0.02
    else:
        img = title(t)
    # gate weave + per-frame jitter
    wx = 5 * math.sin(t * 1.7) + 3 * math.sin(t * 4.3 + 1) + r.normal(0, 0.9)
    wy = 4 * math.sin(t * 1.3 + 2) + 2 * math.sin(t * 5.1) + r.normal(0, 0.9)
    img = C.warp(img, wx, wy, 0.06 * math.sin(t * 0.9), 1.01, border=cv2.BORDER_REPLICATE)
    img = grade(img)
    img = K.halation(img, 0.62, 20, (1.0, 0.32, 0.12), 0.55)
    img *= 1 + r.normal(0, 0.035)                                    # flicker
    dark, light = K.dust_layer(i, 909, density=1.4)
    img = img * (1 - 0.85 * dark[..., None]) + light[..., None] * 0.7
    cg = cv2.resize(r.standard_normal((H // 3, W // 3, 3)).astype(np.float32), (W, H)) * 0.018
    img = img + cg
    img = img * GATE[..., None]
    return POST.finish(img, i, bloom=0.15, threshold=0.85)


def audio():
    m = S.Mix(DUR)
    tt = S.tt(DUR)
    rundown = np.clip((DUR - tt) / 0.8, 0, 1) ** 1.5                 # the projector winds down at the end
    m.add(X.projector(DUR, 24, seed=901) * rundown, 0.0, gain=0.32, pan=-0.2, send=0.1)
    m.add(X.optical_crackle(DUR, seed=902) * rundown, 0.0, gain=0.22, send=0.05)
    # leader: a tick per sweep and the classic beep on the '2'
    for n, tn in NUMS:
        m.add(X.clack(1100, 903, 0.02), tn, gain=0.25, send=0.1)
    beep = np.sin(2 * np.pi * 1000 * S.tt(1 / 24)) * 0.8
    m.add(X.old_film(beep), NUMS[1][1] + 0.3, gain=0.5, send=0.05)
    m.add(X.old_film(S.sos(S.noise(0.08, "white", 904), "lowpass", 3000) * S.env_exp(0.08, 0.001, 0.02)), T_POP, gain=0.5)
    # the burn-in: brass and strings, aged through an optical soundtrack
    t = DUR - T_BURN
    ch = [S.midi(48), S.midi(55), S.midi(60), S.midi(64), S.midi(67)]
    music = X.brass(ch, t, seed=905, bright=0.7, swell=0.05) * 0.6 + X.strings(ch + [S.midi(72)], t, 0.08, 1.2, seed=906) * 0.55
    music += S.pan2(np.sin(2 * np.pi * S.midi(36) * S.tt(t)) * S.env_exp(t, 0.01, 1.4) * 0.5, 0)
    tl = S.tt(t)
    music = music * np.clip((t - tl) / 1.3, 0, 1) ** 1.6                 # the stinger rings out before the end
    m.add(X.old_film(music, seed=907, wow=0.005), T_BURN, gain=0.75, send=0.35)
    m.add(X.old_film(S.sos(S.noise(1.2, "pink", 908), "lowpass", 2500) * S.env_exp(1.2, 0.05, 0.4)), T_BURN, gain=0.25, send=0.3)
    mix = m.master(ir_seconds=2.0, wet=0.6, peak_db=-1.5, tail_fade=0.12)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [4, 14, 22, 34, 46, 48, 52, 56, 60, 66, 80, 92, 110, 125, 143], tag="ident09")
