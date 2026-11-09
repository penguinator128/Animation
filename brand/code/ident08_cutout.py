"""
ASTRIS PRODUCTIONS - Ident 08: STOP-MOTION CUTOUT (4.0 s, fast and playful)

A green cutting mat, shot from above, animated on twos (12 fps) with a little stop-motion "boil" on every
piece. Coloured paper pieces slide in, pop and snap together to build the logo; then the letters hop in one by
one (squash and stretch) to spell ASTRIS PRODUCTIONS, and the whole thing does a happy little bounce.
Visible cut edges, paper thickness, soft shadows that grow as pieces lift off the mat.
Sound: paper slaps, pops and clacks, a flutter for every hop, and a cheerful xylophone-and-bells stinger.
"""
import math

import numpy as np

import common as C
import kit as K
import sfx as X
import sound as S

cv2 = C.cv2
NAME = "astris-ident-08"
DUR = 4.0
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=808, grain=0.018, vignette=0.32)
STEP = 2                                     # animate on twos
T_BOUNCE = 2.75

lock = K.Lockup2(LOGO, logo_h=700, lines=[("luckiest-guy-400", "ASTRIS", 170, 0.14, None),
                                            ("lilita-one-400", "PRODUCTIONS", 62, 0.0, 1.0)],
                 gaps=(130, 60), centre=(W / 2, H / 2 - 20))
PAL = [K.rgb(h) for h in ("#2ec4b6", "#ff6b6b", "#ffd23f", "#b388eb", "#4ea8de", "#80ed99", "#ff9f1c", "#f15bb5")]


# ---------------------------------------------------------------- the cutting mat
def build_mat():
    img = np.zeros((H, W, 3), np.float32) + K.rgb("#1f5e47")
    img *= (0.9 + 0.2 * cv2.resize(K.fbm(H // 6, W // 6, 81, 5), (W, H)))[..., None]
    g = np.zeros((H, W), np.float32)
    for x in range(0, W, 64):
        g[:, x:x + 2] = 0.25 if x % 320 else 0.55
    for y in range(0, H, 64):
        g[y:y + 2, :] = np.maximum(g[y:y + 2, :], 0.25 if y % 320 else 0.55)
    img = K.comp(img, g, K.rgb("#7fc4a2"))
    r = np.random.default_rng(82)
    cuts = np.zeros((H, W), np.float32)
    for _ in range(90):
        x, y = r.uniform(0, W), r.uniform(0, H)
        a = r.uniform(0, math.pi)
        L = r.uniform(40, 420)
        cv2.line(cuts, (int(x), int(y)), (int(x + math.cos(a) * L), int(y + math.sin(a) * L)), float(r.uniform(0.3, 0.8)), 1, cv2.LINE_AA)
    img = img * (1 - 0.18 * cuts[..., None]) + cuts[..., None] * K.rgb("#9ad8b8") * 0.06
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    img *= (1.08 - 0.22 * np.hypot((xx - W * 0.4) / W, (yy - H * 0.35) / H))[..., None]
    return img


MAT = build_mat()
PAPER_T = K.paper(H, W, (1, 1, 1), seed=83, fibres=0.03, grain=0.03, mottle=0.05)[..., 0]


def scissor(poly, seed, amp=1.6):
    """Hand-cut edges: tiny wobbles along each edge."""
    r = np.random.default_rng(seed)
    out = []
    for a, b in zip(poly, np.roll(poly, -1, 0)):
        L = np.linalg.norm(b - a)
        n = max(2, int(L / 30))
        for s in np.linspace(0, 1, n, endpoint=False):
            out.append(a + (b - a) * s + r.normal(0, amp, 2))
    return np.array(out)


# ---------------------------------------------------------------- pieces (design space, rest positions)
lc, lh = lock.logo_c, lock.logo_h
film_polys = LOGO.polys_px(lc[0], lc[1], lh, pieces=[0])
bar_polys = LOGO.polys_px(lc[0], lc[1], lh, pieces=[len(LOGO.pieces) - 1])
from shapely.geometry import Polygon, box

fp = Polygon(film_polys[0], film_polys[1:]).buffer(0)
cut_y = lc[1] + 40
upper = fp.intersection(box(0, 0, W, cut_y))
lower = fp.intersection(box(0, cut_y, W, H))


def to_polys(g):
    gs = g.geoms if hasattr(g, "geoms") else [g]
    out = []
    for p in gs:
        out.append(np.array(p.exterior.coords)[:-1])
        out += [np.array(h.coords)[:-1] for h in p.interiors]
    return out


PIECES = [  # polys, colour, arrival kind, t_start, t_land, from offset
    {"polys": bar_polys, "col": K.rgb("#ffd23f"), "kind": "slide", "t0": 0.25, "t1": 0.62, "off": (1500, -80)},
    {"polys": to_polys(lower), "col": K.rgb("#ff6b6b"), "kind": "pop", "t0": 0.62, "t1": 0.80, "off": (0, 0)},
    {"polys": to_polys(upper), "col": K.rgb("#ff8c69"), "kind": "slide", "t0": 0.85, "t1": 1.15, "off": (-900, -700)},
]
for k, p in enumerate(PIECES):
    p["polys"] = [scissor(q, 840 + k * 10 + j, 0.8 if j == 0 else 0.5) for j, q in enumerate(p["polys"])]
    allp = np.concatenate(p["polys"])
    p["c"] = allp.mean(0)

LETTERS = []
la, lp = lock.line(0), lock.line(1)
for k, L in enumerate(la):
    LETTERS.append({"L": L, "col": PAL[k % len(PAL)], "t0": 1.32 + k * 0.13, "dur": 0.30, "big": True})
for k, L in enumerate(lp):
    LETTERS.append({"L": L, "col": K.rgb("#fff3dc"), "t0": 2.12 + k * 0.045, "dur": 0.22, "big": False})
for k, L in enumerate(LETTERS):
    L["polys"] = [scissor(q, 900 + k * 7 + j, 1.1 if L["big"] else 0.6) for j, q in enumerate(L["L"]["polys"])]


def on_twos(t):
    return math.floor(t * C.FPS / STEP) * STEP / C.FPS


def boil(seed, ta):
    r = np.random.default_rng(int(seed * 1000 + ta * 97))
    return r.normal(0, 1.4, 2), r.normal(0, 0.003)


def piece_state(p, t):
    """(dx, dy, rot, scale, lift) for a logo piece at animation time t."""
    if t < p["t0"]:
        return None
    k = C.clamp((t - p["t0"]) / (p["t1"] - p["t0"]))
    if p["kind"] == "slide":
        e = 1 - (1 - k) ** 3
        over = 0.06 * math.sin(math.pi * C.clamp((t - p["t1"]) / 0.16)) if t > p["t1"] else 0
        dx, dy = p["off"][0] * (1 - e), p["off"][1] * (1 - e)
        dx -= p["off"][0] * over * 0.4
        return dx, dy, 0.25 * (1 - e) * np.sign(p["off"][0] + 1e-6), 1.0, 0.9 * (1 - e) + 0.2 * (1 - k)
    s = C.spring(t - p["t0"], 26, 0.42)
    return 0.0, 0.0, 0.0, max(0.001, s), 0.6 * (1 - k)


def letter_state(L, t):
    if t < L["t0"]:
        return None
    k = C.clamp((t - L["t0"]) / L["dur"])
    hop = 260 if L["big"] else 60
    dy = -hop * 4 * k * (1 - k) + (1 - k) * (180 if L["big"] else 120)
    after = t - (L["t0"] + L["dur"])
    sq = 0.0
    if after > 0:
        sq = 0.22 * math.exp(-after / 0.08) * math.cos(after * 40)
    sx, sy = 1 + sq, 1 - sq
    if k < 1:
        sx, sy = 1 - 0.1 * math.sin(math.pi * k), 1 + 0.14 * math.sin(math.pi * k)
    return 0.0, dy, (1 - k) * -0.3, (sx, sy), 0.7 * (1 - k) + 0.1


def bounce(t):
    tau = t - T_BOUNCE
    if tau < 0:
        return 1.0, 1.0, 0.0
    a = math.exp(-tau / 0.18)
    return 1 + 0.06 * a * math.cos(tau * 28), 1 - 0.07 * a * math.cos(tau * 28), -40 * a * max(0, math.sin(tau * 28))


def transform(polys, centre, dx, dy, rot, sx, sy, gsx, gsy, gdy, pivot):
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for q in polys:
        p = q - centre
        p = np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], 1) * [sx, sy] + centre + [dx, dy]
        p = (p - pivot) * [gsx, gsy] + pivot + [0, gdy]
        out.append(p)
    return out


def frame(i):
    t = i / C.FPS
    ta = on_twos(t)
    gsx, gsy, gdy = bounce(ta)
    pivot = np.array([W / 2, lock.baselines[1] + 20])
    items = []
    for k, p in enumerate(PIECES):
        st = piece_state(p, ta)
        if st is None:
            continue
        dx, dy, rot, sc, lift = st
        b, br = boil(k + 1, ta)
        items.append((transform(p["polys"], p["c"], dx + b[0], dy + b[1], rot + br, sc, sc, gsx, gsy, gdy, pivot), p["col"], lift))
    for k, L in enumerate(LETTERS):
        st = letter_state(L, ta)
        if st is None:
            continue
        dx, dy, rot, (sx, sy), lift = st
        b, br = boil(50 + k, ta)
        cen = L["L"]["centre"] + np.array([0, (170 if L["big"] else 62) / 2])
        items.append((transform(L["polys"], cen, dx + b[0], dy + b[1], rot + br, sx, sy, gsx, gsy, gdy, pivot), L["col"], lift))
    img = MAT.copy()
    # shadows: everything casts onto the mat, further and softer when lifted
    sh = np.zeros((H // 2, W // 2), np.float32)
    for polys, col, lift in items:
        off = np.array([10 + 34 * lift, 14 + 48 * lift])
        q = [(p + off) / 2 for p in polys]
        cv2.fillPoly(sh, [np.round(x * 16).astype(np.int32) for x in q], 1.0, cv2.LINE_AA, 4)
    sh = cv2.resize(cv2.GaussianBlur(sh, (0, 0), 7), (W, H))
    img = img * (1 - 0.45 * np.clip(sh, 0, 1))[..., None]
    for polys, col, lift in items:
        # paper thickness: a darker sliver along the bottom edge, then the sheet, then a crisp light cut edge
        edge = np.zeros((H, W), np.float32)
        C.draw_polys_max(edge, [p + [0, 5] for p in polys], 1.0)
        img = K.comp(img, edge, col * 0.62)
        m = np.zeros((H, W), np.float32)
        C.draw_polys_max(m, polys, 1.0)
        tex = (0.92 + 0.12 * (PAPER_T - 1) * 6)
        img = img * (1 - m[..., None]) + (col * (1.0 + 0.06 * lift))[None, None] * tex[..., None] * m[..., None]
        rim = np.zeros((H, W), np.float32)
        for p in polys:
            cv2.polylines(rim, [np.round(p * 16).astype(np.int32)], True, 1.0, 3, cv2.LINE_AA, 4)
        img = img + (rim * m * 0.18)[..., None]
    return POST.finish(img, i, bloom=0.1, threshold=0.95)


def audio():
    m = S.Mix(DUR)
    room = S.sos(S.noise(DUR, "pink", 801), "lowpass", 700)
    m.add(room / np.max(np.abs(room)), 0.0, gain=0.04, send=0.0)
    m.add(X.paper_rustle(0.35, seed=802, density=30), PIECES[0]["t0"], gain=0.22, pan=0.6, send=0.15)
    m.add(X.paper_slap(803, 1.2), PIECES[0]["t1"], gain=0.55, pan=0.3, send=0.2)
    m.add(X.paper_pop(804, 1.0), PIECES[1]["t0"] + 0.03, gain=0.5, pan=-0.2, send=0.2)
    m.add(X.paper_rustle(0.3, seed=805, density=30), PIECES[2]["t0"], gain=0.2, pan=-0.6, send=0.15)
    m.add(X.clack(760, 806, 0.06), PIECES[2]["t1"], gain=0.5, pan=-0.2, send=0.2)
    scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]
    for k, L in enumerate(LETTERS):
        land = L["t0"] + L["dur"]
        if L["big"]:
            m.add(X.paper_pop(810 + k, 1.2 + 0.08 * k), land, gain=0.38, pan=float((L["L"]["centre"][0] - W / 2) / W * 1.4), send=0.2)
            m.add(X.xylophone(S.midi(72 + scale[k % len(scale)]), 0.8), land + 0.005, gain=0.10, pan=float((L["L"]["centre"][0] - W / 2) / W), send=0.35)
        else:
            m.add(X.clack(1400 + 60 * k, 820 + k, 0.025), land, gain=0.16, pan=float((L["L"]["centre"][0] - W / 2) / W * 1.4), send=0.2)
    # cheerful stinger on the bounce
    for k, n in enumerate((72, 76, 79, 84)):
        m.add(X.xylophone(S.midi(n), 1.0), T_BOUNCE + k * 0.055, gain=0.22, pan=-0.3 + 0.2 * k, send=0.4)
    m.add(S.chime(S.midi(96), 1.6, decay=0.8), T_BOUNCE + 0.22, gain=0.10, pan=0.3, send=0.5)
    m.add(X.kalimba(S.midi(60), 1.4) + X.kalimba(S.midi(67), 1.4) * 0.6, T_BOUNCE + 0.22, gain=0.18, send=0.4)
    m.add(X.tambourine(0.6, 830), T_BOUNCE + 0.22, gain=0.10, pan=0.4, send=0.3)
    mix = m.master(ir_seconds=1.3, wet=0.6, peak_db=-1.5, tail_fade=0.1)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    K.run(NAME, DUR, frame, audio, [4, 10, 15, 18, 22, 26, 32, 38, 44, 52, 58, 64, 68, 95], tag="ident08")
