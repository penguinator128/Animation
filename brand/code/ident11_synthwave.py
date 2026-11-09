"""
ASTRIS PRODUCTIONS - Ident 11: RETRO 80s VHS SYNTHWAVE (5.0 s, fast then medium)

We race over a glowing neon grid toward a sunset sun cut by horizontal bars, past purple mountains with hot
pink ridgelines under a starry gradient sky. A chrome 80s emblem of the logo sweeps in and flares with a star
glint; ASTRIS appears in bevelled chrome, "Productions" writes itself in hot-pink neon script.
All of it played back off a worn VHS tape: chroma bleed, a rolling tracking band, head-switching noise at the
bottom, scanlines, tape specks, an on-screen PLAY display, on a curved, glowing CRT.
Sound: a pulsing analogue arpeggio, tape hiss and wow, a gated-reverb snare and a big synth stab.
"""
import math

import numpy as np

import common as C
import kit as K
import sfx as X
import sound as S

cv2 = C.cv2
NAME = "astris-ident-11"
DUR = 5.0
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=1111, grain=0.03, vignette=0.30)
HZ = 1180                                  # horizon line
T_LOGO0, T_GLINT, T_ASTRIS, T_PROD = 1.55, 2.08, 2.35, 2.85
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

# ---------------------------------------------------------------- static pieces of the world
SKY_KEYS = [(0.0, "#0b0326"), (0.35, "#2a0b4d"), (0.62, "#7a1a7a"), (0.82, "#ff3d8b"), (1.0, "#ff9a3d")]
v = np.clip(yy / HZ, 0, 1)
SKY = np.stack([np.interp(v, [k for k, _ in SKY_KEYS], [K.rgb(h)[c] for _, h in SKY_KEYS]) for c in range(3)], -1).astype(np.float32)
_sr = np.random.default_rng(111)
STARS = np.zeros((H, W), np.float32)
STAR_PTS = np.stack([_sr.uniform(0, W, 500), _sr.uniform(0, HZ * 0.8, 500)], 1)
STAR_B = _sr.uniform(0.3, 1.0, 500)
STAR_PH = _sr.uniform(0, 6.28, 500)
SUN_C, SUN_R = np.array([W / 2, HZ - 330.0]), 600.0
SUN_D = np.hypot(xx - SUN_C[0], yy - SUN_C[1])
SUN_V = np.clip((yy - (SUN_C[1] - SUN_R)) / (2 * SUN_R), 0, 1)
SUN_COL = np.stack([np.interp(SUN_V, [0, 0.45, 1], [K.rgb(h)[c] for h in ("#fff36b", "#ff9a3d", "#ff2d8f")]) for c in range(3)], -1)


def mountains():
    r = np.random.default_rng(112)
    m = np.zeros((H, W), np.float32)
    ridge = np.zeros((H, W), np.float32)
    for layer, (base, amp, col) in enumerate(((HZ, 260, 0.6), (HZ, 170, 1.0))):
        xs = np.linspace(-100, W + 100, 40)
        ys = base - np.abs(r.normal(0, amp, len(xs))) * (0.35 + 0.65 * np.abs(np.sin(xs / W * 3 + layer)))
        ys[(xs > W * 0.36) & (xs < W * 0.64)] = base - 20            # keep the sun clear
        pts = np.concatenate([np.stack([xs, ys], 1), [[W + 100, base + 5], [-100, base + 5]]])
        cv2.fillPoly(m, [np.round(pts).astype(np.int32)], col, cv2.LINE_AA)
        cv2.polylines(ridge, [np.round(np.stack([xs, ys], 1)).astype(np.int32)], False, 1.0, 5, cv2.LINE_AA)
    return m, ridge


MTN, RIDGE = mountains()
# chrome logo (built once at its final place, swept in by warping)
LOCK_LOGO_H, LOGO_C = 600.0, np.array([W / 2, 690.0])
LMASK = C.poly_mask_ss(LOGO.polys_px(LOGO_C[0], LOGO_C[1], LOCK_LOGO_H), ss=2)
CHROME = [(0.0, "#12052a"), (0.30, "#3b1a6e"), (0.45, "#9a6ad8"), (0.49, "#ff8ad8"), (0.51, "#ffffff"), (0.54, "#ffb347"),
          (0.62, "#4ad0ff"), (0.82, "#d4f4ff"), (1.0, "#ffffff")]
_n = K.bevel_normals(LMASK, 34, 70)
UU, VV = (xx - LOGO_C[0]) / LOCK_LOGO_H, (yy - LOGO_C[1]) / LOCK_LOGO_H
LCHROME = K.env_metal(_n, CHROME, UU, VV, bend=1.1, light=(-0.4, -0.85, 0.5), spec_pow=50, spec=1.4)
LOGO_RIM = np.clip((4 - np.abs(cv2.distanceTransform((LMASK > 0.5).astype(np.uint8), cv2.DIST_L2, 5) - 3)) / 2, 0, 1) * (LMASK > 0.5)
A_BASE = HZ + 290
LKEY = np.clip((16 - cv2.distanceTransform((LMASK < 0.5).astype(np.uint8), cv2.DIST_L2, 5)) / 1.5, 0, 1)
a_letters, a_w = K.line_letters("orbitron-900", "ASTRIS", 170, W / 2, A_BASE, 0.22)
AMASK = K.letters_mask(a_letters)
AKEY = np.clip((12 - cv2.distanceTransform((AMASK < 0.5).astype(np.uint8), cv2.DIST_L2, 5)) / 1.5, 0, 1)
_an = K.bevel_normals(AMASK, 10, 30)
TCHROME = [(0.0, "#2a1260"), (0.32, "#7a4ad0"), (0.46, "#ffb0e8"), (0.5, "#ffffff"), (0.54, "#ffc070"),
           (0.62, "#7adfff"), (0.82, "#e8f8ff"), (1.0, "#ffffff")]
ACHROME = K.env_metal(_an, TCHROME, (xx - W / 2) / 900, (yy - (A_BASE - 85)) / 170 * 0.5, bend=1.6, light=(-0.3, -0.9, 0.4), spec_pow=40)
P_ROT = -0.09
p_letters, p_w = K.line_letters("mr-dafoe-400", "Productions", 150, W / 2 + 330, A_BASE + 150, 0.02,
                                per_letter=lambda k, n: {"dy": (k - n / 2) * -10})
PMASK = K.letters_mask(p_letters)
PMASK = cv2.warpAffine(PMASK, cv2.getRotationMatrix2D((W / 2 + 330, A_BASE + 120), math.degrees(-P_ROT), 1.0), (W, H))
P_X0, P_X1 = W / 2 + 330 - p_w / 2 - 40, W / 2 + 330 + p_w / 2 + 40


def world(t):
    img = SKY.copy()
    st = np.zeros((H // 2, W // 2), np.float32)
    for p, b, ph in zip(STAR_PTS, STAR_B, STAR_PH):
        tw = b * (0.6 + 0.4 * math.sin(t * 6 + ph))
        cv2.circle(st, (int(p[0] / 2 * 16), int(p[1] / 2 * 16)), int(16 * 1.2), tw, -1, cv2.LINE_AA, 4)
    img += C.up(cv2.resize(st, (W // 4, H // 4), interpolation=cv2.INTER_AREA))[..., None] * 0 + cv2.resize(st, (W, H))[..., None] * 0.9
    # the sun, sliced by bars that slide upward
    sun = np.clip((SUN_R - SUN_D) / 2, 0, 1)
    rel = (yy - SUN_C[1]) / SUN_R
    phase = (rel * 7 + t * 0.6) % 1.0
    gap = np.clip(0.12 + 0.35 * np.clip(rel, 0, 1), 0, 0.6)
    gap = np.clip(0.10 + 0.45 * np.clip((rel + 0.45) / 1.0, 0, 1), 0, 0.6)
    bars = np.where(rel > -0.45, (phase > gap).astype(np.float32), 1.0)
    sun = sun * bars
    img = img * (1 - sun[..., None]) + SUN_COL * 0.86 * sun[..., None]
    img += (np.exp(-np.clip(SUN_D - SUN_R, 0, None) / 260) * 0.35)[..., None] * K.rgb("#ff4a8a") * (SUN_D > SUN_R)[..., None]
    img = img * (1 - MTN[..., None]) + K.rgb("#170730") * MTN[..., None]
    img += RIDGE[..., None] * K.rgb("#ff2bd6") * 1.2
    # the floor and the racing grid
    floor = (yy > HZ).astype(np.float32)
    img = img * (1 - floor[..., None]) + (K.rgb("#14052a") * (1 + 0.4 * np.clip((yy - HZ) / (H - HZ), 0, 1))[..., None]) * floor[..., None]
    g = np.zeros((H, W), np.float32)
    speed = 9.0 * math.exp(-t / 0.9) + 1.1
    travel = 9.0 * 0.9 * (1 - math.exp(-t / 0.9)) + 1.1 * t
    for k in range(-60, 61):
        x_far = W / 2 + k * 60
        x_near = W / 2 + k * 60 * 14
        cv2.line(g, (int(x_far * 16), int(HZ * 16)), (int(x_near * 16), int((H + 600) * 16)), 1.0, 3, cv2.LINE_AA, 4)
    for j in range(1, 40):
        z = (j - (travel % 1.0)) * 1.0
        if z <= 0.15:
            continue
        y = HZ + 520 / z
        if y > H + 10:
            continue
        thick = max(2, int(5 / z ** 0.5))
        cv2.line(g, (0, int(y * 16)), (W * 16, int(y * 16)), float(min(1.0, 2.5 / z ** 0.3)), thick, cv2.LINE_AA, 4)
    g *= floor
    fade = np.clip((yy - HZ) / 400, 0, 1) ** 0.5
    img += (g * fade)[..., None] * K.rgb("#ff2bd6") * 1.15 + (g * (1 - fade))[..., None] * K.rgb("#2bd6ff") * 0.9
    img += (np.exp(-np.abs(yy - HZ) / 30) * 0.5)[..., None] * K.rgb("#ff7ad9")
    return img, speed


def vhs(img, t, i):
    r = np.random.default_rng(11000 + i)
    # chroma bleed: luma stays sharp, colour smears sideways and lags a little
    Y = img @ np.array([0.299, 0.587, 0.114], np.float32)
    chroma = img - Y[..., None]
    chroma = cv2.blur(chroma, (41, 1))
    chroma = np.roll(chroma, 9, axis=1)
    img = Y[..., None] + chroma * 1.15
    # rolling tracking band
    by = (H * 1.3) * ((t * 0.32 + 0.15) % 1.0) - H * 0.15
    band = np.exp(-((np.arange(H) - by) / 70) ** 2) * (1 - 0.8 * C.smoothstep(3.3, 3.8, t))   # calmer once the lockup holds
    rows = np.where(band > 0.05)[0]
    for y in rows[::2]:
        off = int(r.normal(0, 40 * band[y]))
        img[y:y + 2] = np.roll(img[y:y + 2], off, axis=1)
    img += (band[:, None] * r.random((H, 1)) * 0.25)[..., None]
    # head-switching noise along the bottom
    for y in range(H - 46, H, 2):
        img[y:y + 2] = np.roll(img[y:y + 2], int(r.normal(30 + (y - H + 46) * 2, 8)), axis=1)
    # tape specks and the odd dropout line
    sp = (r.random((H // 4, W // 4)) > 0.9993).astype(np.float32)
    img += C.up(cv2.GaussianBlur(sp, (0, 0), 0.6))[..., None] * 0.9
    if r.uniform() < 0.25:
        y = int(r.uniform(0, H))
        img[y:y + 3] = img[y:y + 3] * 0.3 + 0.7
    img = K.scanlines(img, period=6, depth=0.20, phase=(i % 2) * 3)
    img = np.roll(img, int(r.normal(0, 1.2)), axis=0)
    return img


def frame(i):
    t = i / C.FPS
    img, speed = world(t)
    # the chrome emblem sweeps in from above with a spin, then sits
    if t >= T_LOGO0:
        k = C.clamp((t - T_LOGO0) / (T_GLINT - T_LOGO0))
        e = 1 - (1 - k) ** 3
        sc = 0.25 + 0.75 * e
        ang = 35 * (1 - e)
        dy = -900 * (1 - e)
        M = cv2.getRotationMatrix2D((LOGO_C[0], LOGO_C[1]), ang, sc)
        M[1, 2] += dy
        m = cv2.warpAffine(LMASK, M, (W, H))
        col = cv2.warpAffine(LCHROME, M, (W, H))
        rim = cv2.warpAffine(LOGO_RIM, M, (W, H))
        glow = cv2.GaussianBlur(cv2.resize(m, (W // 4, H // 4)), (0, 0), 10)
        img += C.up(glow)[..., None] * K.rgb("#ff2bd6") * 0.6
        keyline = cv2.warpAffine(LKEY, M, (W, H))
        img = img * (1 - keyline[..., None]) + K.rgb("#14052a") * keyline[..., None]
        img = img * (1 - m[..., None]) + col * m[..., None]
        img += rim[..., None] * K.rgb("#ff9ae6") * 0.8
    # the glint: a four-point star flaring on the emblem's apex
    gl = C.pulse(t, T_GLINT, 0.03, 0.22)
    if gl > 0.01:
        gp = np.array([LOGO_C[0] + 70, LOGO_C[1] - LOCK_LOGO_H / 2 + 30])
        dx, dy = np.abs(xx - gp[0]), np.abs(yy - gp[1])
        star = (np.exp(-dy / 6) * np.exp(-dx / 700) + np.exp(-dx / 6) * np.exp(-dy / 380) + np.exp(-np.hypot(dx, dy) / 40) * 2)
        img += (star * gl * 1.4)[..., None] * np.array([1.0, 0.95, 1.0], np.float32)
    # ASTRIS in chrome: wiped on by a bright sweep
    if t >= T_ASTRIS:
        k = C.clamp((t - T_ASTRIS) / 0.45)
        sx = W / 2 - a_w / 2 - 100 + (a_w + 200) * C.expo_in_out(k, 4)
        rev = np.clip((sx - xx) / 30, 0, 1)
        am = AMASK * rev
        img += C.up(cv2.GaussianBlur(cv2.resize(am, (W // 4, H // 4)), (0, 0), 6))[..., None] * K.rgb("#4ad0ff") * 0.6
        ak = AKEY * rev
        img = img * (1 - ak[..., None]) + K.rgb("#14052a") * ak[..., None]
        img = img * (1 - am[..., None]) + ACHROME * am[..., None]
        img += (AMASK * np.exp(-((xx - sx) / 40) ** 2) * (k < 1) * 1.5)[..., None]
    # Productions: hot-pink neon script, written left to right with a flicker as it ignites
    if t >= T_PROD:
        k = C.clamp((t - T_PROD) / 0.5)
        sx = P_X0 + (P_X1 - P_X0) * k
        pm = PMASK * np.clip((sx - xx) / 25, 0, 1)
        fl = 1.0 if (t - T_PROD) > 0.65 else (0.55 + 0.45 * (math.sin(t * 90) > -0.2))
        glow = C.up(cv2.GaussianBlur(cv2.resize(pm, (W // 4, H // 4)), (0, 0), 7))
        img += glow[..., None] * K.rgb("#ff2bd6") * 1.1 * fl
        img = img * (1 - pm[..., None]) + (K.rgb("#ffd1f3") * fl)[None, None] * pm[..., None]
    img = vhs(img, t, i)
    # the ▶ PLAY display for the first second
    if t < 1.25:
        osd = np.zeros((H, W), np.float32)
        from PIL import Image, ImageDraw, ImageFont
        im = Image.new("L", (900, 160), 0)
        dr = ImageDraw.Draw(im)
        dr.polygon([(14, 30), (14, 130), (94, 80)], fill=255)
        dr.text((130, 10), "PLAY", font=ImageFont.truetype(str(C.FONT_DIR / "vt323-400.ttf"), 130), fill=255)
        osd[180:340, 260:1160] = np.asarray(im, np.float32) / 255
        img = K.comp(img, osd * (0.9 if (int(t * 4) % 2 == 0 or t < 0.6) else 0.0), [0.85, 1.0, 0.85])
    img = K.crt_curve(img, 0.05)
    return POST.finish(img, i, bloom=0.5, threshold=0.68, radii=(1.0, 1.2, 1.0))


def audio():
    m = S.Mix(DUR)
    m.add(X.tape_hiss(DUR, seed=1101), 0.0, gain=0.07, send=0.0)
    # a little tape wow as it starts, then the pulsing arp (A minor, 16ths at 128 bpm)
    step = 60 / 128 / 4
    notes = [S.midi(n) for n in (57, 64, 69, 72, 76, 72, 69, 64)]
    arp = X.synth_arp(notes, step, DUR, seed=1102, wave="saw", cutoff=2800, res=3.0)
    arp[:, : int(0.3 * S.SR)] *= np.linspace(0, 1, int(0.3 * S.SR))
    m.add(arp, 0.0, gain=0.30, send=0.25)
    bass_notes = [(k * step * 4, step * 3, 33 if (k // 4) % 2 == 0 else 31, None) for k in range(int(DUR / (step * 4)))]
    m.add(X.funk_bass(bass_notes, DUR, seed=1103), 0.0, gain=0.25, send=0.05)
    m.add(S.whoosh(T_GLINT - T_LOGO0 + 0.1, peak=0.9, f_lo=400, f_hi=8000, q=1.0, pan_from=0, pan_to=0, seed=1104), T_LOGO0, gain=0.35, send=0.2)
    m.add(X.gated_snare(1105, 0.3), T_GLINT, gain=0.55, send=0.15)
    am = [S.midi(45), S.midi(57), S.midi(60), S.midi(64), S.midi(67), S.midi(72)]
    m.add(X.synth_stab(am, 2.2, seed=1106, bright=1.0), T_GLINT, gain=0.55, send=0.35)
    m.add(S.sub_drop(1.6, 90, 40, 0.3, 0.8), T_GLINT, gain=0.45, send=0.0)
    m.add(S.chime(S.midi(93), 1.2, decay=0.6), T_GLINT + 0.02, gain=0.12, pan=0.3, send=0.5)
    m.add(S.whoosh(0.5, peak=0.7, f_lo=1500, f_hi=9000, q=1.0, pan_from=-0.6, pan_to=0.6, seed=1107), T_ASTRIS, gain=0.18, send=0.3)
    buzz = S.sos(np.sign(np.sin(2 * np.pi * 120 * S.tt(0.7))) * 0.3, "lowpass", 2500) * S.env_exp(0.7, 0.01, 0.5)
    m.add(buzz, T_PROD, gain=0.15, pan=0.4, send=0.2)
    m.add(X.synth_stab([S.midi(64), S.midi(69), S.midi(72), S.midi(76)], 1.6, seed=1108, bright=0.6), T_PROD + 0.5, gain=0.25, send=0.4)
    mix = m.master(ir_seconds=1.8, wet=0.7, peak_db=-1.5, tail_fade=0.12)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [2, 12, 24, 36, 40, 46, 50, 54, 58, 62, 70, 80, 95, 119], tag="ident11")
