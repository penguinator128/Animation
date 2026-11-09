"""
ASTRIS PRODUCTIONS - Ident 01: MINI SWITCHER (5.75 s, fast -> slow)

A pocket version of the style-switcher with eight new art directions, each held a little longer than the
last (2, 3, 4, 5, 6, 7, 9, 11 frames): comic halftone, sumi ink on rice paper, lava, circuit board,
foil balloon, carved wood, marble with gold leaf, holographic foil. Then a flowing full rainbow (14 frames),
a hard landing on clean white, the rainbow paint drains and drips away, the camera pulls out, type arrives.
Sound: a tick per switch rising in pitch (each with a flavour of its material), then a big landing hit.
"""
import math

import numpy as np

import common as C
import hero3_style_switcher as H3      # reuses the tested landing / drain / drip / pull-out machinery
import kit as K
import sfx as X
import sound as S

cv2 = C.cv2
NAME = "astris-ident-01"
W, H = C.W, C.H
SEQ = [("comic", 2), ("ink", 3), ("lava", 4), ("circuit", 5), ("balloon", 6), ("wood", 7), ("marble", 9),
       ("holo", 11), ("rainbow", 14)]
STARTS = np.cumsum([0] + [d for _, d in SEQ]).tolist()
LAND_F = STARTS[-1]                                  # 61
T_LAND = LAND_F / C.FPS                              # 2.54 s
DUR = 5.75

# point the hero 3 landing machinery at this ident's timeline
H3.STARTS = STARTS
H3.T_LAND, H3.DRAIN = T_LAND, 1.25
H3.T_PULL0, H3.T_PULL1 = T_LAND + 0.45, T_LAND + 1.75
H3.T_ASTRIS, H3.T_PROD = T_LAND + 1.36, T_LAND + 1.58
H3.DUR = DUR
H3.DRIP_T0 = H3._dr.uniform(0.05, 0.4, H3.ND)
POST = C.Post(seed=101, grain=0.02, vignette=0.28)
MASK, SDF, DI, U, V = H3.MASK, H3.SDF, H3.DI, H3.U, H3.V
XX, YY = H3.XX, H3.YY
blur, shift, grow, comp, rgb = H3.blur, H3.shift, H3.grow, H3.comp, H3.rgb
POLYS, REF_C, REF_H = H3.POLYS, H3.REF_C, H3.REF_H
HOLES = C.poly_mask([POLYS[j] for j in H3.HOLE_IDX]) if H3.HOLE_IDX else np.zeros((H, W), np.float32)


def outline(width):
    return np.clip((width / 2 - np.abs(SDF)) / 1.2 + 0.5, 0, 1)


# ================================================================================================
# eight new art directions
# ================================================================================================
def style_comic():
    img = np.zeros((H, W, 3), np.float32) + rgb("#ffd21f")
    ang = np.arctan2(YY - REF_C[1], XX - REF_C[0])
    rays = (np.sin(ang * 22) > 0.35).astype(np.float32)
    img = comp(img, blur(rays, 1.0) * 0.55, rgb("#fff3a6"))
    dots = K.halftone(np.clip(np.hypot(U, V) * 0.9, 0, 1) * 0.55, cell=34, angle=0.785)
    img = comp(img, dots * 0.5, rgb("#ff8a1f"))
    # the logo: red with Ben-Day shading, heavy black keyline, a hard drop shadow
    sh = shift(grow(16), 26, 26)
    img = comp(img, sh, rgb("#111111"))
    img = comp(img, grow(16), rgb("#111111"))
    img = comp(img, MASK, rgb("#e8262b"))
    shade = K.halftone(np.clip(0.15 + (U * 0.6 + V * 0.9), 0, 1) * 0.65, cell=26, angle=0.3) * MASK
    img = comp(img, shade, rgb("#9a0f16"))
    hl = np.clip(MASK - shift(MASK, 18, 18), 0, 1) * (V < 0.15)
    return comp(img, hl * 0.95, rgb("#ffffff"))


def style_ink():
    img = K.paper(H, W, rgb("#efe6d2"), seed=11, fibres=0.09, grain=0.035, mottle=0.08)
    # dry-brush edge: the mask edge is broken up by fibrous noise, ink density streaks along the strokes
    n = K.fbm(H // 4, W // 4, 12, 6)
    n = cv2.resize(n, (W, H))
    streak = cv2.GaussianBlur(np.random.default_rng(3).standard_normal((H // 2, W // 2)).astype(np.float32), (0, 0),
                              sigmaX=1.0, sigmaY=14)
    streak = cv2.resize(streak / streak.std(), (W, H))
    rough = np.clip((-SDF + 10 * (n - 0.5) * 2 + 4 * streak) / 2.0 + 0.5, 0, 1)
    dens = np.clip(0.82 + 0.12 * streak - 0.25 * np.clip((DI - 6) / 40, 0, 1) * (n > 0.62), 0.45, 1)
    ink = rough * dens
    img = img * (1 - ink[..., None] * 0.94)
    # splatter
    r = np.random.default_rng(5)
    sp = np.zeros((H, W), np.float32)
    for _ in range(60):
        x, y = r.normal(REF_C[0] + 650, 260), r.normal(REF_C[1] + 520, 200)
        cv2.circle(sp, (int(x), int(y)), int(abs(r.normal(4, 4)) + 1), 1.0, -1, cv2.LINE_AA)
    img = img * (1 - blur(sp, 0.8)[..., None] * 0.85)
    # a red seal stamp
    seal = np.zeros((H, W), np.float32)
    x0, y0 = int(REF_C[0] + 900), int(REF_C[1] + 520)
    cv2.rectangle(seal, (x0, y0), (x0 + 150, y0 + 150), 1.0, -1, cv2.LINE_AA)
    inner = C.poly_mask(C.Logo.polys_px(H3.LOGO, x0 + 75, y0 + 75, 110))
    seal = np.clip(seal - inner, 0, 1) * (0.75 + 0.25 * cv2.resize(K.fbm(60, 60, 9), (W, H))[..., None][..., 0])
    return comp(img, seal * 0.9, rgb("#c0262c"))


def style_lava():
    img = np.zeros((H, W, 3), np.float32) + rgb("#120806")
    rock = cv2.resize(K.fbm(H // 6, W // 6, 21, 6), (W, H))
    img *= (0.6 + 0.8 * rock)[..., None]
    # cracks: ridged noise inside the logo, plus a glowing rim
    a = cv2.resize(K.fbm(H // 3, W // 3, 22, 6, base=4), (W, H))
    b = cv2.resize(K.fbm(H // 3, W // 3, 23, 6, base=7), (W, H))
    ridge = np.minimum(np.abs(a - 0.5), np.abs(b - 0.5) * 1.3)
    cracks = np.clip(1 - ridge / 0.045, 0, 1) ** 2
    rim = np.exp(-np.clip(DI, 0, None) / 18)
    heat = np.clip(cracks + rim * 0.8, 0, 1) * MASK
    crust = rgb("#2a1208") * (0.7 + 0.6 * rock[..., None])
    lava = rgb("#ff4a00") * (1 - heat[..., None]) + rgb("#ffd36b") * heat[..., None]
    logo = crust * (1 - heat[..., None]) + lava * heat[..., None] * 1.6
    img = comp(img, MASK, [0, 0, 0]) + logo * MASK[..., None]
    glow = blur(heat, 12) * 0.8 + blur(MASK, 60) * 0.35
    return img + glow[..., None] * rgb("#ff5a10") * 0.9


def style_circuit():
    r = np.random.default_rng(31)
    img = np.zeros((H, W, 3), np.float32) + rgb("#0b3a22")
    img *= (0.85 + 0.3 * cv2.resize(K.fbm(H // 8, W // 8, 32, 5), (W, H)))[..., None]
    tr = np.zeros((H, W), np.float32)
    # background traces: orthogonal runs with 45-degree joggles and pads
    for _ in range(150):
        x, y = r.uniform(0, W), r.uniform(0, H)
        pts = [(x, y)]
        for seg in range(r.integers(2, 5)):
            d = r.choice([(1, 0), (0, 1), (1, 1), (-1, 1)])
            L = r.uniform(60, 420)
            x, y = x + d[0] * L, y + d[1] * L
            pts.append((x, y))
        cv2.polylines(tr, [np.round(np.array(pts)).astype(np.int32)], False, 1.0, 6, cv2.LINE_AA)
        cv2.circle(tr, (int(x), int(y)), 13, 1.0, -1, cv2.LINE_AA)
    tr *= (1 - grow(60))
    img = comp(img, tr * 0.55, rgb("#2f8a52"))
    # the logo as copper: three parallel traces following the outline, vias in the sprocket holes
    copper = np.zeros((H, W), np.float32)
    for off in (-10, -38, -66):
        copper = np.maximum(copper, np.clip((5.5 - np.abs(SDF - off)) / 1.2 + 0.5, 0, 1))
    fill = MASK * 0.18
    img = comp(img, fill, rgb("#d79a3c"))
    img = comp(img, copper, rgb("#e3a44a"))
    # each sprocket hole becomes a plated via: a gold ring around a dark drill hole
    dh = cv2.distanceTransform((1 - (HOLES > 0.5)).astype(np.uint8), cv2.DIST_L2, 5)
    vias = np.clip((4.5 - np.abs(dh - 8)) / 1.2 + 0.5, 0, 1) * (HOLES < 0.5)
    img = comp(img, vias, rgb("#f6d27a"))
    return img


def circuit_live(img, tl):
    """Data pulses racing along the copper outline."""
    ang = (np.arctan2(V, U) + math.pi) / (2 * math.pi)
    band = np.clip((6 - np.abs(SDF + 38)) / 1.5 + 0.5, 0, 1)
    pulse = np.exp(-((np.mod(ang * 3 - tl * 2.2, 1.0) - 0.5) / 0.04) ** 2)
    return img + (band * pulse)[..., None] * rgb("#7dffcf") * 1.6


def style_balloon():
    img = np.zeros((H, W, 3), np.float32) + rgb("#9fd7ff")
    img = img * (1 - 0.35 * np.clip((YY / H)[..., None], 0, 1)) + rgb("#ffd9f2") * 0.25 * (YY / H)[..., None]
    n = K.bevel_normals(MASK, 140, 120, blur=2.0)                    # very puffy
    foil = K.env_metal(n, [(0.0, "#5a0636"), (0.3, "#b0125f"), (0.5, "#ff3d9a"), (0.62, "#ffc2e2"), (0.75, "#ff5aa8"),
                           (1.0, "#ffe6f4")], U, V, bend=1.4, light=(-0.5, -0.7, 0.55), spec_pow=24, spec=1.6)
    crinkle = 1 + 0.06 * np.sin((U * 40 + V * 13)) * np.exp(-DI / 60)
    foil *= crinkle[..., None]
    seam = np.clip((3.5 - np.abs(SDF + 6)) / 1.2 + 0.5, 0, 1)
    shadow = blur(shift(MASK, 40, 70), 40)
    img = img * (1 - 0.35 * shadow[..., None])
    img = comp(img, MASK, [0, 0, 0]) + foil * MASK[..., None]
    return comp(img, seam * 0.5, rgb("#ffb3d9"))


def wood_tex(seed, base, dark, scale=1.0, angle=0.0):
    n = cv2.resize(K.fbm(H // 6, W // 6, seed, 5), (W, H))
    c, s = math.cos(angle), math.sin(angle)
    u = (XX * c + YY * s) / W
    v = (-XX * s + YY * c) / H
    rings = np.sin((v * 60 * scale + n * 9 + np.sin(u * 7) * 0.8) * 2.0)
    fine = cv2.resize(cv2.GaussianBlur(np.random.default_rng(seed).standard_normal((H // 2, W // 2)).astype(np.float32),
                                       (0, 0), sigmaX=30, sigmaY=0.8), (W, H))
    k = np.clip(0.5 + 0.35 * rings + 0.2 * fine / (fine.std() + 1e-6), 0, 1)
    return rgb(base) * (1 - k[..., None]) + rgb(dark) * k[..., None]


def style_wood():
    img = wood_tex(41, "#5a3a22", "#2c1a0e", 1.2, 0.0) * 0.9
    maple = wood_tex(42, "#e9c48d", "#b98a52", 0.8, 0.12)
    n = K.bevel_normals(MASK, 22, 40)
    light = np.clip(0.75 + 0.5 * (n[..., 0] * -0.5 + n[..., 1] * -0.7), 0.4, 1.3)
    inset = blur(shift(MASK, 10, 14), 6)
    img = img * (1 - 0.55 * inset[..., None])
    return comp(img, MASK, [0, 0, 0]) + maple * light[..., None] * MASK[..., None]


def style_marble():
    img = np.zeros((H, W, 3), np.float32) + rgb("#0d1a16")
    img *= (0.8 + 0.5 * cv2.resize(K.fbm(H // 6, W // 6, 51, 5), (W, H)))[..., None]
    n1 = cv2.resize(K.fbm(H // 3, W // 3, 52, 7, base=3), (W, H))
    veins = np.abs(np.sin((U * 3.0 + V * 5.0 + n1 * 6.0) * math.pi))
    fine = np.abs(np.sin((U * 9.0 - V * 4.0 + n1 * 11.0) * math.pi))
    v = np.clip(1 - veins / 0.06, 0, 1) * 0.55 + np.clip(1 - fine / 0.03, 0, 1) * 0.25
    marble = rgb("#f4f1ea") * (1 - v[..., None]) + rgb("#7d8088") * v[..., None]
    marble *= (0.92 + 0.1 * n1)[..., None]
    gold_edge = np.clip((5 - np.abs(SDF + 4)) / 1.2 + 0.5, 0, 1)
    shadow = blur(shift(MASK, 0, 30), 28)
    img = img * (1 - 0.6 * shadow[..., None])
    img = comp(img, MASK, [0, 0, 0]) + marble * MASK[..., None]
    gold = rgb("#e7b85a") * (0.8 + 0.4 * np.clip(-V * 2, 0, 1))[..., None]
    return comp(img, gold_edge, gold)


HOLO_N = None


def style_holo():
    global HOLO_N
    img = np.zeros((H, W, 3), np.float32) + rgb("#1b1d22")
    img *= (0.85 + 0.3 * np.clip(1 - np.hypot(U, V) * 0.5, 0, 1))[..., None]
    HOLO_N = K.bevel_normals(MASK, 30, 50)
    return img


def holo_live(img, tl):
    n = HOLO_N
    ph = U * 2.2 - V * 1.4 + n[..., 0] * 0.8 + n[..., 1] * 0.6 - tl * 1.8
    spec = C.hue_wheel(ph * 1.3)
    sparkle = (np.sin(U * 260) * np.sin(V * 260) > 0.92).astype(np.float32) * 0.25
    silver = 0.62 + 0.25 * np.clip(-n[..., 1] - n[..., 0] * 0.5, -1, 1)
    foil = silver[..., None] * 0.55 + spec * 0.6 + sparkle[..., None]
    sweep_band = np.exp(-(((U * 0.8 - V * 0.5) - (-0.9 + 2.0 * tl / 0.45)) / 0.08) ** 2) * 0.5
    return comp(img, MASK, [0, 0, 0]) + (foil + sweep_band[..., None]) * MASK[..., None]


STYLE_FUNCS = {"comic": style_comic, "ink": style_ink, "lava": style_lava, "circuit": style_circuit,
               "balloon": style_balloon, "wood": style_wood, "marble": style_marble, "holo": style_holo}
BLOOM = {"comic": (0.12, 0.92), "ink": (0.1, 0.95), "lava": (0.75, 0.55), "circuit": (0.45, 0.6),
         "balloon": (0.3, 0.8), "wood": (0.15, 0.9), "marble": (0.25, 0.8), "holo": (0.45, 0.7), "rainbow": (0.35, 0.8)}
BASES = {}


def build_bases(names=None):
    for nm in names or STYLE_FUNCS:
        if nm not in BASES:
            BASES[nm] = STYLE_FUNCS[nm]().astype(np.float16)


def style_at(i):
    for k, (nm, d) in enumerate(SEQ):
        if STARTS[k] <= i < STARTS[k + 1]:
            return k, nm, STARTS[k], d
    return None


def frame(i):
    t = i / C.FPS
    if i < LAND_F:
        k, nm, k0, d = style_at(i)
        tl = (i - k0) / C.FPS
        if nm == "rainbow":
            img = np.zeros((H, W, 3), np.float32) + rgb("#030304")
            img = H3.rainbow(img, tl)
        else:
            if nm not in BASES:
                build_bases([nm])
            img = BASES[nm].astype(np.float32)
            if nm == "circuit":
                img = circuit_live(img, tl)
            elif nm == "holo":
                img = holo_live(img, tl)
            elif nm == "lava":
                img = img * (1 + 0.06 * math.sin(tl * 25))
        zoom = 1.0 + 0.03 * (i / LAND_F) + 0.035 * math.exp(-(i - k0) / 1.3)
        img = C.warp(img, zoom=zoom, center=REF_C, border=cv2.BORDER_REPLICATE)
        bl, th = BLOOM[nm]
        return POST.finish(img, i, bloom=bl, threshold=th)
    img, bloom = H3.landing(t, i)
    return POST.finish(img, i, bloom=bloom, threshold=0.75)


# ================================================================================================
# sound: a tick per switch, each with a little of its material, pitch climbing as it slows
# ================================================================================================
def flavour(nm, f):
    if nm == "comic":
        return X.paper_pop(3, 1.4) * 0.8
    if nm == "ink":
        return X.pencil(0.18, np.linspace(1, 0, 20), seed=4) * 0.5
    if nm == "lava":
        return S.sos(S.noise(0.3, "white", 5), "bandpass", [2000, 8000]) * S.env_exp(0.3, 0.005, 0.08) * 0.5
    if nm == "circuit":
        return np.concatenate([X.beep(f * 4, 0.04), X.beep(f * 6, 0.04)])
    if nm == "balloon":
        t = S.tt(0.2)
        return np.sin(2 * np.pi * np.cumsum(f * 3 * (1 + 0.6 * t / 0.2)) / S.SR) * np.exp(-t / 0.06) * 0.5
    if nm == "wood":
        return X.clack(f * 2.2, 6, 0.04)
    if nm == "marble":
        return X.clack(f * 5, 7, 0.09) * 0.7
    if nm == "holo":
        return X.glass_ping(f * 4, 1.2) * 0.6
    return S.chime(f * 2, 1.5, 1.0, 0.8)


def audio():
    m = S.Mix(DUR)
    m.add(S.sub_build(T_LAND, 34, 60, curve=1.6), 0.0, gain=0.32, send=0.0)
    m.add(S.riser(T_LAND, 400, 6000, seed=111), 0.0, gain=0.14, send=0.2)
    for k, (nm, d) in enumerate(SEQ):
        tk = STARTS[k] / C.FPS
        f = 233.0 * 2 ** (k * 1.9 / len(SEQ))
        m.add(S.tick(f, 0.28, level=1.0, seed=120 + k), tk, gain=0.42, pan=(-1) ** k * 0.15, send=0.18)
        m.add(flavour(nm, f), tk, gain=0.32, pan=(-1) ** k * 0.3, send=0.35)
    m.add(S.whoosh(0.3, peak=0.9, f_lo=600, f_hi=7000, q=1.0, pan_from=0, pan_to=0, seed=131), T_LAND - 0.27, gain=0.4, send=0.15)
    m.add(S.impact(3.0, weight=1.3, bright=1.0, metal=0.7, seed=133, sub_f=(92, 33)), T_LAND, gain=0.95, send=0.3)
    chord = [S.midi(48), S.midi(55), S.midi(60), S.midi(64), S.midi(67), S.midi(72)]
    m.add(S.sting(chord, 3.2, bright=0.85, seed=135), T_LAND, gain=0.45, send=0.45)
    m.add(S.shimmer(2.6, root=S.midi(84), density=30, seed=137, rise=0.35), T_LAND + 0.04, gain=0.26, send=0.6)
    for k in range(H3.ND):
        tk = T_LAND + H3.DRIP_T0[k] + 0.3 + 0.2 * H3.DRIP_G[k]
        if tk < DUR - 0.8:
            f0 = 1000 + 900 * H3.DRIP_W[k] / 0.032
            x = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 0.8 * np.exp(-S.tt(0.12) / 0.02))) / S.SR) * np.exp(-S.tt(0.12) / 0.03)
            m.add(x, tk, gain=0.045, pan=float(np.clip(H3.DRIPS[k][0] * 1.4, -0.8, 0.8)), send=0.5)
    m.add(S.whoosh(0.45, peak=0.8, f_lo=300, f_hi=4500, q=1.0, pan_from=-0.5, pan_to=0.2, seed=139), H3.T_ASTRIS - 0.35,
          gain=0.2, send=0.3)
    m.add(S.chime(S.midi(91), 1.6, decay=0.9), H3.T_ASTRIS + 0.3, gain=0.08, pan=0.3, send=0.6)
    mix = m.master(ir_seconds=2.2, wet=0.9, peak_db=-1.5, tail_fade=0.12)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    build_bases()
    K.run(NAME, DUR, frame, audio, [0, 2, 5, 9, 14, 20, 27, 36, 47, 52, 61, 66, 75, 90, 105, 137], tag="ident01",
          sheet_cols=4)
