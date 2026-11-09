"""
ASTRIS PRODUCTIONS - Ident 05: RAINBOW PRISM (4.2 s, medium)

A dark, hazy room. A single beam of white light cuts in from the left and strikes a glass logo. Out of the
far side a full spectrum fans across the screen through the haze. Then the colours fold back into the glass,
which floods with white light. ASTRIS PRODUCTIONS arrives on a light sweep, in thin luminous Italiana.
Sound: a rising glassy tone with the beam, a crystalline shimmer at the split, a bright chord at the glow.
"""
import math

import numpy as np

import common as C
import kit as K
import sfx as X
import sound as S

cv2 = C.cv2
NAME = "astris-ident-05"
DUR = 4.2
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=505, grain=0.018, vignette=0.42)

T_HIT, T_FAN1, T_FOLD0, T_GLOW, T_TXT = 0.85, 1.55, 1.75, 2.55, 2.75
LOGO_H, LOGO_C = 760.0, np.array([W / 2, 850.0])
POLYS = LOGO.polys_px(LOGO_C[0], LOGO_C[1], LOGO_H)
MASK = C.poly_mask_ss(POLYS, ss=2)
NRM = K.bevel_normals(MASK, 40, 70)
BIN = (MASK > 0.5).astype(np.uint8)
DI = cv2.distanceTransform(BIN, cv2.DIST_L2, 5)
RIM = np.clip(1 - NRM[..., 2], 0, 1) ** 1.2
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
HAZE_A = K.fbm(H // 8, W // 8, 51, 6, base=3)
HAZE_B = K.fbm(H // 8, W // 8, 52, 6, base=5)

film = LOGO.polys_px(LOGO_C[0], LOGO_C[1], LOGO_H, pieces=[0])[0]
bar = LOGO.polys_px(LOGO_C[0], LOGO_C[1], LOGO_H, pieces=[len(LOGO.pieces) - 1])[0]
ENTRY = np.array([film[:, 0].min() + 120, LOGO_C[1] + 140])        # where the beam strikes the film strip
EXIT = np.array([bar[:, 0].max() - 160, LOGO_C[1] + 120])          # where the spectrum leaves the bar
BEAM_Y0 = ENTRY[1] - 260
THETA0, SPREAD = math.radians(4), math.radians(38)

lock = K.Lockup2(LOGO, logo_h=LOGO_H, lines=[("italiana-400", "ASTRIS", 150, 0.45, None),
                                               ("italiana-400", "PRODUCTIONS", 44, 0.0, 1.0)],
                 gaps=(130, 70), centre=(W / 2, H / 2 + 10))
TXT_A = K.letters_mask(lock.line(0))
TXT_P = K.letters_mask(lock.line(1))
assert abs(lock.logo_c[1] - LOGO_C[1]) < 60


def haze(t):
    a = cv2.warpAffine(HAZE_A, np.float32([[1, 0, -t * 9], [0, 1, -t * 3]]), (W // 8, H // 8), borderMode=cv2.BORDER_REFLECT101)
    b = cv2.warpAffine(HAZE_B, np.float32([[1, 0, t * 5], [0, 1, -t * 4]]), (W // 8, H // 8), borderMode=cv2.BORDER_REFLECT101)
    return cv2.resize(0.35 + 0.65 * a * b * 1.6, (W, H), interpolation=cv2.INTER_LINEAR)


def beam_layer(t, hz):
    """The white beam: travels in from the left to the entry point, fades as the colours fold back."""
    if t < 0.05:
        return np.zeros((H, W), np.float32)
    front = -200 + (ENTRY[0] + 200) * C.expo_out((t - 0.05) / (T_HIT - 0.05), 4)
    p0, p1 = np.array([-200.0, BEAM_Y0]), ENTRY
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    n = np.array([-d[1], d[0]])
    dist = (xx - p0[0]) * n[0] + (yy - p0[1]) * n[1]
    along = (xx - p0[0]) * d[0] + (yy - p0[1]) * d[1]
    L = (front - p0[0]) / d[0]
    core = np.exp(-(dist / 7) ** 2) * 2.4 + np.exp(-(dist / 34) ** 2) * 0.55 * hz + np.exp(-(dist / 120) ** 2) * 0.18 * hz
    cut = np.clip((L - along) / 40, 0, 1) * (along > -10)
    fade = 1 - C.smoothstep(T_FOLD0, T_GLOW, t)
    return core * cut * fade


def fan_layer(t, hz):
    """The spectrum fanning out of the bar, then folding back into it."""
    if t < T_HIT:
        return np.zeros((H, W, 3), np.float32)
    open_k = C.expo_out((t - T_HIT) / (T_FAN1 - T_HIT), 4)
    fold = C.smoothstep(T_FOLD0, T_GLOW, t)
    spread = SPREAD * open_k * (1 - fold)
    reach = 4200 * open_k * (1 - fold ** 0.6)
    if spread < 1e-3 or reach < 5:
        return np.zeros((H, W, 3), np.float32)
    dx, dy = xx - EXIT[0], yy - EXIT[1]
    r = np.hypot(dx, dy)
    ph = np.arctan2(dy, dx) - THETA0
    u = (ph + spread / 2) / spread                                   # 0 (top, red) .. 1 (bottom, violet)
    inside = np.clip(u * 30, 0, 1) * np.clip((1 - u) * 30, 0, 1) * (dx > 0)
    col = C.spectrum(np.clip(u, 0, 1))
    reachm = np.clip((reach - r) / 300, 0, 1)
    fall = 1 / (1 + (r / 2600) ** 2)
    inten = inside * reachm * fall * (0.55 + 0.75 * hz) * (1.0 + 0.25 * np.exp(-r / 300))
    return col * inten[..., None] * 1.15


def glass(t, bg):
    """Glass logo: refracts the room, rim catches light; fills with spectrum light, then pure white."""
    k = 60.0
    mx = xx - NRM[..., 0] * k
    my = yy - NRM[..., 1] * k
    refr = cv2.remap(bg, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    lit = C.smoothstep(T_HIT - 0.05, T_HIT + 0.3, t) * (1 - C.smoothstep(T_FOLD0, T_GLOW, t))
    caust = C.hue_wheel((xx - EXIT[0]) / 700 + (yy - LOGO_C[1]) / 900 - t * 0.6)
    inner = caust * (0.25 + 0.5 * np.clip(DI / 60, 0, 1))[..., None] * lit * 0.9
    glow = C.smoothstep(T_FOLD0 + 0.2, T_GLOW, t)
    settle = 1.0 + 0.22 * math.exp(-max(0.0, t - T_GLOW) / 0.25) if t >= T_GLOW else 1.0
    white = np.array([0.97, 0.97, 1.0], np.float32) * glow * settle
    rim = (RIM * (0.6 + 1.6 * lit + 0.8 * glow))[..., None] * np.array([0.95, 0.97, 1.0], np.float32)
    g = refr * 0.85 * (1 - glow) + 0.04 + inner + rim + white
    return g


def frame(i):
    t = i / C.FPS
    hz = haze(t)
    bg = np.zeros((H, W, 3), np.float32) + K.rgb("#07080c")
    bg += (hz * 0.035)[..., None] * K.rgb("#8090b0")
    beam = beam_layer(t, hz)
    bg += beam[..., None] * np.array([1.0, 0.98, 0.95], np.float32)
    bg += fan_layer(t, hz)
    hit = C.pulse(t, T_HIT, 0.02, 0.18)
    if hit > 0.01:
        r = np.hypot(xx - ENTRY[0], yy - ENTRY[1])
        bg += (np.exp(-r / 90) * 2.0 * hit)[..., None]
    img = bg * (1 - MASK[..., None]) + glass(t, bg) * MASK[..., None]
    # the text arrives on a light sweep
    if t >= T_TXT:
        k = C.clamp((t - T_TXT) / 0.6)
        sx = (W / 2 - lock.widths[0] / 2 - 200) + (lock.widths[0] + 400) * C.expo_in_out(k, 4)
        rev = np.clip((sx - xx) / 60, 0, 1)
        band = np.exp(-((xx - sx) / 70) ** 2) * (k < 1)
        tm = np.maximum(TXT_A, TXT_P)
        img = img * (1 - (tm * rev)[..., None]) + np.array([0.95, 0.95, 1.0], np.float32) * (tm * rev)[..., None]
        img += (tm * band * 1.8)[..., None]
    bloom = 0.5 + 0.25 * C.pulse(t, T_GLOW, 0.1, 0.4) + 0.4 * hit
    return POST.finish(img, i, bloom=bloom, threshold=0.62)


def audio():
    m = S.Mix(DUR)
    room = S.sos(S.noise(DUR, "pink", 501), "lowpass", 600)
    m.add(room / np.max(np.abs(room)), 0.0, gain=0.05, send=0.1)
    t = S.tt(T_GLOW)
    f = 220 * 2 ** (2.0 * (t / T_GLOW) ** 1.4)
    tone = (np.sin(2 * np.pi * np.cumsum(f) / S.SR) + 0.3 * np.sin(2 * np.pi * np.cumsum(f * 2.01) / S.SR)) * (t / T_GLOW) ** 1.5
    m.add(tone, 0.0, gain=0.12, send=0.45)
    m.add(S.whoosh(0.9, peak=0.85, f_lo=600, f_hi=9000, q=1.2, pan_from=-0.9, pan_to=-0.2, seed=502), 0.0, gain=0.3, send=0.2)
    for k, fr in enumerate((S.midi(88), S.midi(95), S.midi(91), S.midi(100))):
        m.add(X.glass_ping(fr, 2.0), T_HIT + k * 0.04, gain=0.12, pan=-0.3 + 0.25 * k, send=0.6)
    m.add(S.shimmer(2.0, root=S.midi(84), density=40, seed=503, rise=0.5), T_HIT + 0.05, gain=0.26, pan=0.3, send=0.6)
    m.add(S.reverse_swell(T_GLOW - T_FOLD0, seed=504, f=4000), T_FOLD0, gain=0.25, send=0.2)
    chord = [S.midi(52), S.midi(59), S.midi(64), S.midi(68), S.midi(71), S.midi(76)]
    m.add(S.sting(chord, DUR - T_GLOW, bright=1.0, seed=505), T_GLOW, gain=0.5, send=0.5)
    m.add(S.impact(1.6, weight=0.5, bright=0.6, metal=0.3, seed=506, sub_f=(80, 40)), T_GLOW, gain=0.45, send=0.3)
    m.add(S.whoosh(0.7, peak=0.6, f_lo=1500, f_hi=9000, q=1.0, pan_from=-0.6, pan_to=0.6, seed=507), T_TXT, gain=0.16, send=0.4)
    mix = m.master(ir_seconds=2.4, wet=1.0, peak_db=-1.5, tail_fade=0.12)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [6, 14, 20, 24, 30, 37, 42, 50, 58, 64, 72, 100], tag="ident05")
