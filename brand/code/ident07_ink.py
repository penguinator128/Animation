"""
ASTRIS PRODUCTIONS - Ident 07: INK AND WATER (7.0 s, slow to medium)

Drops of rainbow ink - magenta, cyan, gold, ultramarine, tangerine, violet - fall into backlit water and bloom
into curling plumes (a real stable-fluids simulation with vorticity confinement, run once, frame-accurately).
Then the currents gently swirl them together and the ink condenses into the logo. ASTRIS PRODUCTIONS settles
in through the ink in an elegant serif, and the water calms under soft caustic light.
Colour is subtractive like real ink: light passes through the water and each ink absorbs its own wavelengths.
Sound: soft underwater drops, a low whoosh as it gathers, a gentle ambient pad and a quiet chime.
"""
import math

import numpy as np

import common as C
import kit as K
import sfx as X
import sound as S

cv2 = C.cv2
NAME = "astris-ident-07"
DUR = 7.0
N = int(DUR * C.FPS)
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=707, grain=0.016, vignette=0.34)
GH, GW = 288, 512                      # fluid grid
SUB = 2                                # sim steps per frame
DT = 1.0 / (C.FPS * SUB)
T_GATHER0, T_GATHER1, T_FORM, T_TEXT = 2.5, 4.4, 4.5, 4.9

INKS = {  # absorbance (R, G, B): what each ink takes out of the light
    "magenta": (0.08, 1.9, 0.45), "cyan": (1.9, 0.35, 0.08), "gold": (0.05, 0.35, 1.9),
    "ultramarine": (1.7, 1.25, 0.08), "tangerine": (0.05, 1.0, 1.9), "violet": (0.95, 1.75, 0.25)}
DROPS = [  # time, x (0..1), ink
    (0.15, 0.30, "magenta"), (0.45, 0.66, "cyan"), (0.80, 0.47, "gold"), (1.10, 0.20, "ultramarine"),
    (1.40, 0.80, "tangerine"), (1.75, 0.57, "violet")]
INDIGO = np.array([1.85, 1.55, 0.35], np.float32)

lock = K.Lockup2(LOGO, logo_h=740, lines=[("cormorant-garamond-600", "ASTRIS", 160, 0.38, None),
                                            ("cormorant-garamond-500", "PRODUCTIONS", 48, 0.0, 1.0)],
                 gaps=(140, 70), centre=(W / 2, H / 2 - 10))
LOGO_M = C.poly_mask_ss(lock.logo_polys(), ss=2)
TEXT_M = np.maximum(K.letters_mask(lock.line(0)), K.letters_mask(lock.line(1)))
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


# ================================================================================================
# the simulation (stable fluids: semi-Lagrangian advection, Jacobi pressure projection, vorticity)
# ================================================================================================
def simulate():
    gy, gx = np.mgrid[0:GH, 0:GW].astype(np.float32)
    u = np.zeros((GH, GW), np.float32)
    v = np.zeros((GH, GW), np.float32)
    dye = np.zeros((GH, GW, 3), np.float32)
    logo_small = cv2.resize(LOGO_M, (GW, GH), interpolation=cv2.INTER_AREA)
    lb = (logo_small > 0.5).astype(np.uint8)
    sdf = (cv2.distanceTransform(1 - lb, cv2.DIST_L2, 3) - cv2.distanceTransform(lb, cv2.DIST_L2, 3)).astype(np.float32)
    sdf = cv2.GaussianBlur(sdf, (0, 0), 2)
    ax = cv2.Sobel(sdf, cv2.CV_32F, 1, 0, ksize=3) / 8
    ay = cv2.Sobel(sdf, cv2.CV_32F, 0, 1, ksize=3) / 8
    an = np.sqrt(ax * ax + ay * ay) + 1e-6
    ax, ay = ax / an, ay / an
    target = cv2.GaussianBlur(logo_small, (0, 0), 1.2)[..., None] * INDIGO
    cx, cy = GW / 2, GH * 0.43
    frames = np.zeros((N, GH, GW, 3), np.float16)
    vel_frames = np.zeros((N, GH, GW, 2), np.float16)
    rng = np.random.default_rng(77)
    tr = np.random.default_rng(78)
    TURB_X = cv2.GaussianBlur(tr.standard_normal((GH, GW)).astype(np.float32), (0, 0), 14)
    TURB_Y = cv2.GaussianBlur(tr.standard_normal((GH, GW)).astype(np.float32), (0, 0), 14)
    TURB_X /= TURB_X.std()
    TURB_Y /= TURB_Y.std()

    def advect(f, u, v):
        return cv2.remap(f, gx - u * DT, gy - v * DT, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    for step in range(N * SUB):
        t = step * DT
        fx = np.zeros_like(u)
        fy = np.zeros_like(v)
        # ink drops: a falling source that injects dye and a downward jet (it rolls into a vortex ring)
        for (t0, x0, ink) in DROPS:
            tau = t - t0
            if 0 <= tau < 0.5:
                yd = 6 + 40 * (1 - math.exp(-tau / 0.12))
                xd = x0 * GW + 4 * math.sin(tau * 9 + x0 * 10)
                r2 = ((gx - xd) ** 2 + (gy - yd) ** 2) / (11.0 ** 2)
                blob = np.exp(-r2)
                amt = 9.0 * math.exp(-tau / 0.07) * DT * 24
                dye += blob[..., None] * np.array(INKS[ink], np.float32) * amt * 0.30
                fy += blob * 2600 * math.exp(-tau / 0.16)
                fx += blob * rng.normal(0, 160)
        # ink is a touch heavier than water; slow turbulence keeps the plumes billowing
        fy += dye.mean(axis=2) * 26
        ph = t * 0.6
        fx += TURB_X * (math.cos(ph) * 55) + TURB_Y * (math.sin(ph) * 30)
        fy += TURB_Y * (math.cos(ph * 1.3) * 45)
        g = C.smoothstep(T_GATHER0, T_GATHER1, t)
        u += fx * DT
        v += fy * DT
        # vorticity confinement keeps the curls alive
        w = (np.roll(v, -1, 1) - np.roll(v, 1, 1) - np.roll(u, -1, 0) + np.roll(u, 1, 0)) * 0.5
        aw = np.abs(w)
        nx = (np.roll(aw, -1, 1) - np.roll(aw, 1, 1)) * 0.5
        ny = (np.roll(aw, -1, 0) - np.roll(aw, 1, 0)) * 0.5
        nn = np.sqrt(nx * nx + ny * ny) + 1e-5
        eps = 9.0 * (1 - 0.7 * g)
        u += eps * (ny / nn) * w * DT
        v += -eps * (nx / nn) * w * DT
        u, v = advect(u, u, v), advect(v, u, v)
        # pressure projection (Jacobi, closed walls)
        div = (np.roll(u, -1, 1) - np.roll(u, 1, 1) + np.roll(v, -1, 0) - np.roll(v, 1, 0)) * 0.5
        p = np.zeros_like(u)
        for _ in range(40):
            pp = np.pad(p, 1, mode="edge")
            p = (pp[1:-1, :-2] + pp[1:-1, 2:] + pp[:-2, 1:-1] + pp[2:, 1:-1] - div) * 0.25
        pp = np.pad(p, 1, mode="edge")
        u -= (pp[1:-1, 2:] - pp[1:-1, :-2]) * 0.5
        v -= (pp[2:, 1:-1] - pp[:-2, 1:-1]) * 0.5
        np.clip(u, -70, 70, out=u)
        np.clip(v, -70, 70, out=v)
        u[:, 0] = u[:, -1] = 0
        v[0, :] = v[-1, :] = 0
        damp = 0.998 - 0.03 * C.smoothstep(T_GATHER1, DUR, t)
        u *= damp
        v *= damp
        if g > 0:
            # the ink is guided home: it rides the water's own currents plus a path down the logo's
            # distance field and a gentle swirl (guiding the dye only keeps the fluid itself stable)
            outside = np.clip(sdf / 5, 0, 1)
            dx, dy = gx - cx, gy - cy
            rr = np.sqrt(dx * dx + dy * dy) + 1e-3
            sw = 26 * g * (1 - C.smoothstep(T_GATHER1, T_FORM + 0.4, t))
            pu = -ax * outside * 95 * g - dy / rr * sw
            pv = -ay * outside * 95 * g + dx / rr * sw
            dye = advect(dye, u + pu, v + pv)
        else:
            dye = advect(dye, u, v)
        # condense into the logo, and let the water clear around it
        c = C.smoothstep(T_GATHER0 + 0.9, T_FORM + 0.4, t) ** 1.6
        if c > 0:
            dye = dye * (1 - 0.045 * c) + target * 0.045 * c
            dye *= (1 - 0.025 * c * (1 - logo_small[..., None]))
        if step % SUB == SUB - 1:
            frames[step // SUB] = dye
            vel_frames[step // SUB] = np.stack([u, v], -1)
    return frames, vel_frames


CACHE = C.ROOT / "cache" / "ident07_sim.npz"
if CACHE.exists():
    _z = np.load(CACHE)
    DYE, VEL = _z["dye"], _z["vel"]
else:
    CACHE.parent.mkdir(exist_ok=True)
    print("[ident07] simulating ink...")
    DYE, VEL = simulate()
    np.savez_compressed(CACHE, dye=DYE, vel=VEL)

# fine wisps: a high-frequency displacement that drags the upscaled dye into filaments
_wr = np.random.default_rng(71)
WISP_X = cv2.resize(cv2.GaussianBlur(_wr.standard_normal((H // 4, W // 4)).astype(np.float32), (0, 0), 3), (W, H)) * 14
WISP_Y = cv2.resize(cv2.GaussianBlur(_wr.standard_normal((H // 4, W // 4)).astype(np.float32), (0, 0), 3), (W, H)) * 14
CAUSTIC_A = K.fbm(H // 6, W // 6, 72, 5, base=6)
CAUSTIC_B = K.fbm(H // 6, W // 6, 73, 5, base=7)


def backlight(t):
    r = np.hypot((xx - W / 2) / W, (yy - H * 0.42) / H)
    base = np.array([0.97, 0.95, 0.90], np.float32) * (1.0 - 0.55 * r[..., None] ** 1.6)
    base += np.array([0.0, 0.04, 0.06], np.float32) * (yy / H)[..., None]
    a = cv2.warpAffine(CAUSTIC_A, np.float32([[1, 0, -t * 6], [0, 1, t * 3]]), (W // 6, H // 6), borderMode=cv2.BORDER_REFLECT101)
    b = cv2.warpAffine(CAUSTIC_B, np.float32([[1, 0, t * 4], [0, 1, -t * 5]]), (W // 6, H // 6), borderMode=cv2.BORDER_REFLECT101)
    caus = np.clip(1 - np.abs(a - b) * 4, 0, 1) ** 2
    calm = 0.5 + 0.5 * C.smoothstep(T_FORM, DUR, t)
    base += (C.up(cv2.GaussianBlur(cv2.resize(caus, (W // 4, H // 4)), (0, 0), 2)) * 0.035 * calm)[..., None]
    return base


def frame(i):
    t = i / C.FPS
    d = DYE[i].astype(np.float32)
    big = cv2.resize(d, (W, H), interpolation=cv2.INTER_CUBIC)
    s = 0.6 + 0.4 * math.sin(t * 0.7)
    big = cv2.remap(big, xx + WISP_X * s, yy + WISP_Y * s, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    big = np.clip(big, 0, None)
    # the formed logo sharpens up: crisp ink edges take over from the simulation
    f = C.smoothstep(T_FORM - 0.3, T_FORM + 0.9, t)
    if f > 0:
        crisp = LOGO_M[..., None] * INDIGO
        soft = cv2.GaussianBlur(LOGO_M, (0, 0), 6)[..., None] * INDIGO
        big = big * (1 - f * 0.8) + (crisp * 0.85 + soft * 0.15) * f * 1.05 + big * LOGO_M[..., None] * f * 0.25
    # the text settles in through the ink like a stain rising to the surface
    k = C.smoothstep(T_TEXT, T_TEXT + 1.1, t)
    if k > 0:
        bl = 8 * (1 - k) + 0.01
        tm = cv2.GaussianBlur(TEXT_M, (0, 0), bl) if bl > 0.3 else TEXT_M
        big = big + tm[..., None] * INDIGO * 0.95 * k
    img = backlight(t) * np.exp(-big * 1.15)
    rays = C.smoothstep(T_FORM, DUR, t)
    if rays > 0:
        img += (np.exp(-((xx - W * 0.42 - (yy * 0.25)) / 260) ** 2) * (1 - yy / H) * 0.05 * rays)[..., None]
    return POST.finish(img, i, bloom=0.2, threshold=0.92)


def audio():
    m = S.Mix(DUR)
    m.add(X.underwater(DUR, seed=701), 0.0, gain=0.35, send=0.2)
    for k, (t0, x0, ink) in enumerate(DROPS):
        m.add(X.bloop(380 + 60 * k, seed=710 + k, size=1.0), t0 + 0.02, gain=0.45, pan=float((x0 - 0.5) * 1.4), send=0.5)
        m.add(S.sos(S.noise(0.6, "pink", 720 + k), "lowpass", 900) * S.env_exp(0.6, 0.01, 0.25), t0 + 0.04, gain=0.12,
              pan=float((x0 - 0.5) * 1.4), send=0.5)
    m.add(S.whoosh(T_GATHER1 - T_GATHER0 + 0.6, peak=0.6, f_lo=90, f_hi=900, q=0.7, pan_from=-0.5, pan_to=0.5, seed=730),
          T_GATHER0, gain=0.35, send=0.4)
    amaj = [S.midi(45), S.midi(52), S.midi(57), S.midi(61), S.midi(64), S.midi(71)]
    m.add(S.pad(amaj, DUR - 0.6, attack=2.8, release=1.6, cutoff=(250, 1800), seed=731), 0.6, gain=0.30, send=0.6)
    m.add(X.glass_ping(S.midi(88), 2.4) * 0.8, T_FORM, gain=0.12, pan=-0.15, send=0.7)
    m.add(X.glass_ping(S.midi(93), 2.2) * 0.8, T_TEXT + 0.35, gain=0.08, pan=0.2, send=0.7)
    mix = m.master(ir_seconds=3.2, wet=1.0, peak_db=-1.5, tail_fade=0.2)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [4, 10, 18, 26, 36, 48, 60, 72, 84, 96, 108, 120, 132, 167], tag="ident07")
