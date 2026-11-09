"""
ASTRIS PRODUCTIONS - Ident 02: SCRIBBLE (6.4 s, medium)

Close-up on cream sketchbook paper under warm window light. A yellow pencil sketches the logo in wobbly,
overshooting lines - two false starts get crossed out with angry zigzags - hatches the bar, then hand-prints
ASTRIS PRODUCTIONS letter by letter (real single-stroke lettering), finishes with an underline swoosh and a
doodled star, and taps the page. The camera follows the pencil, then eases back for the held lockup.
Sound: pencil scratch shaped by every stroke's speed, paper rustle, a soft tap and a tiny warm note.
"""
import math

import numpy as np
from HersheyFonts import HersheyFonts

import common as C
import kit as K
import sfx as X
import sound as S

cv2 = C.cv2
NAME = "astris-ident-02"
DUR = 6.4
W, H = C.W, C.H
LOGO = C.Logo()
POST = C.Post(seed=202, grain=0.016, vignette=0.40)
RNG = np.random.default_rng(2)

PAPER = K.paper(H, W, K.rgb("#f4ead4"), seed=21, fibres=0.022, grain=0.035, mottle=0.06)
TOOTH = K.tooth_map(H, W, 22)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
LIGHT = (1.07 - 0.16 * (xx / W) - 0.12 * (yy / H)).astype(np.float32)     # warm window light from top-left
PAPER = PAPER * LIGHT[..., None]
GRAPHITE = K.rgb("#2a2c33")

# ---------------------------------------------------------------- layout (design space = final frame)
LOGO_H, LOGO_C = 700.0, np.array([W / 2, 770.0])
A_CAP, P_CAP = 150.0, 54.0
A_BASE, P_BASE = LOGO_C[1] + LOGO_H / 2 + 90 + A_CAP, LOGO_C[1] + LOGO_H / 2 + 90 + A_CAP + 78 + P_CAP


def wobbly(p0, p1, seed, overshoot=(14, 20), amp=3.5, n=None):
    """A hand-drawn straight line: overshoots both ends, wobbles gently, never perfectly straight."""
    r = np.random.default_rng(seed)
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = np.linalg.norm(d) + 1e-9
    u, nrm = d / L, np.array([-d[1], d[0]]) / L
    a, b = r.uniform(*overshoot), r.uniform(*overshoot)
    n = n or max(8, int(L / 14))
    s = np.linspace(-a, L + b, n)
    k = s / L
    off = (amp * np.sin(k * math.pi * r.uniform(1.0, 2.2) + r.uniform(0, 6)) +
           amp * 0.5 * np.sin(k * math.pi * r.uniform(3, 6) + r.uniform(0, 6)) + r.uniform(-2, 2) * k)
    return p0 + np.outer(s, u) + np.outer(off, nrm)


def loop(pts, seed, amp=1.6):
    """A quick closed scribble loop through a small polygon's corners (a sprocket hole)."""
    r = np.random.default_rng(seed)
    p = np.concatenate([pts, pts[:1] + r.normal(0, 2, 2)])
    out = []
    for a, b in zip(p[:-1], p[1:]):
        for s in np.linspace(0, 1, 5, endpoint=False):
            out.append(a + (b - a) * s + r.normal(0, amp, 2))
    out.append(p[-1])
    return np.array(out)


def zigzag(p0, p1, width, n, seed):
    """A cross-out scribble along p0->p1."""
    r = np.random.default_rng(seed)
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = np.linalg.norm(d)
    u, nrm = d / L, np.array([-d[1], d[0]]) / L
    pts = [p0 + nrm * width * (1 if k % 2 else -1) * r.uniform(0.7, 1.2) + u * L * k / n + r.normal(0, 4, 2)
           for k in range(n + 1)]
    return np.array(pts)


# ---------------------------------------------------------------- the drawing, stroke by stroke
STROKES = []          # dicts: pts (design px), t0, t1, w (base width px), kind


def add(pts, t0, dur, w, kind):
    STROKES.append({"pts": np.asarray(pts, float), "t0": t0, "t1": t0 + dur, "w": w, "kind": kind})
    return t0 + dur


def logo_px(poly):
    return LOGO_C + poly * LOGO_H


pieces = [[logo_px(p) for p in LOGO.piece_polys(k)] for k in range(len(LOGO.pieces))]
film, bar = pieces[0], pieces[-1]
t = 0.14
# false start 1: the bar's left edge at the wrong angle... crossed out
bo = bar[0]
top_left = bo[np.argmin(bo[:, 0] + bo[:, 1])]
bot_left = bo[np.argmax(bo[:, 1] - bo[:, 0] * 0.3)]
wrong_end = bot_left + np.array([-210, -40])
t = add(wobbly(top_left, wrong_end, 1, amp=5), t, 0.18, 6, "line")
t = add(zigzag(top_left + (wrong_end - top_left) * 0.15, top_left + (wrong_end - top_left) * 0.92, 26, 13, 2), t + 0.03, 0.17, 6, "scribble")
t += 0.04
# the bar: four edges with overshoot
for k in range(len(bo)):
    a, b = bo[k], bo[(k + 1) % len(bo)]
    L = np.linalg.norm(b - a)
    t = add(wobbly(a, b, 10 + k), t, 0.035 + L / 6500, 7, "line") + 0.018
# false start 2: the film strip's left edge drawn too short and bent... crossed out
fo = film[0]
apex = fo[np.argmin(fo[:, 1])]
foot = fo[np.argmin(fo[:, 0])]
bent = apex + (foot - apex) * 0.55 + np.array([60, 30])
t = add(wobbly(apex, bent, 20, amp=7), t + 0.03, 0.12, 6, "line")
t = add(zigzag(apex + (bent - apex) * 0.1, bent, 22, 9, 21), t + 0.02, 0.12, 6, "scribble")
t += 0.03
for k in range(len(fo)):
    a, b = fo[k], fo[(k + 1) % len(fo)]
    L = np.linalg.norm(b - a)
    if L < 25:
        continue
    t = add(wobbly(a, b, 30 + k), t, 0.035 + L / 6500, 7, "line") + 0.018
# sprocket holes: quick loops
holes = film[1:]
holes = sorted(holes, key=lambda p: (p[:, 0].mean() > LOGO_C[0] - 120, -p[:, 1].mean()))
for k, hp in enumerate(holes):
    t = add(loop(hp, 50 + k), t, 0.021, 5, "hole")
t += 0.04
# shading: a dense zigzag hatch across the bar, lighter strokes along the film strip
from shapely.geometry import LineString, Polygon

bar_poly = Polygon(bo).buffer(-10)
ang = math.radians(52)
dirv = np.array([math.cos(ang), math.sin(ang)])
perp = np.array([-dirv[1], dirv[0]])
c0 = np.array(bar_poly.centroid.coords[0])
segs = []
for k, off in enumerate(np.arange(-420, 420, 22)):
    ln = LineString([c0 + perp * off - dirv * 900, c0 + perp * off + dirv * 900])
    g = ln.intersection(bar_poly)
    if g.is_empty or g.geom_type != "LineString":
        continue
    pts = np.array(g.coords)
    segs.append(pts if k % 2 == 0 else pts[::-1])
hatch = np.concatenate([s for s in segs]) if segs else np.zeros((0, 2))
hatch = hatch + RNG.normal(0, 3, hatch.shape)
t = add(hatch, t, 0.34, 4, "hatch")
film_poly = Polygon(fo, [h for h in film[1:]]).buffer(-14)
for k, off in enumerate(np.arange(-300, 300, 46)):
    c1 = np.array(film_poly.centroid.coords[0])
    ln = LineString([c1 + perp * off - dirv * 900, c1 + perp * off + dirv * 900])
    g = ln.intersection(film_poly)
    for part in (g.geoms if hasattr(g, "geoms") else [g]):
        if part.is_empty or part.geom_type != "LineString" or part.length < 30:
            continue
        t = add(np.array(part.coords) + RNG.normal(0, 2, (len(part.coords), 2)), t, 0.011, 3, "hatch2")
T_TEXT = t + 0.06

# ---------------------------------------------------------------- hand-printed type (single-stroke Hershey)
HF = HersheyFonts()
HF.load_default_font("futural")
HF.normalize_rendering(100)


def hershey_word(text, cap, cx, base, track):
    """Per letter: list of strokes (design px), and the word's total width."""
    letters, widths = [], []
    for ch in text:
        strokes = [np.array(s, float) for s in HF.strokes_for_text(ch)]
        allp = np.concatenate(strokes)
        x0, x1 = allp[:, 0].min(), allp[:, 0].max()
        sc = cap / 75.0
        letters.append([np.stack([(s[:, 0] - x0) * sc, base - (s[:, 1] - 25) * sc], 1) for s in strokes])
        widths.append((x1 - x0) * sc)
    total = sum(widths) + track * (len(text) - 1)
    x = cx - total / 2
    out = []
    for L, wd in zip(letters, widths):
        out.append([s + [x, 0] for s in L])
        x += wd + track
    return out, total


astris, aw = hershey_word("ASTRIS", A_CAP, W / 2, A_BASE, A_CAP * 0.42)
prod, pw = hershey_word("PRODUCTIONS", P_CAP, W / 2, P_BASE, 0)
# justify PRODUCTIONS under ASTRIS
track = (aw - pw) / 10
prod, pw = hershey_word("PRODUCTIONS", P_CAP, W / 2, P_BASE, track)
t = T_TEXT
for k, L in enumerate(astris):
    for j, s in enumerate(L):
        s = s + RNG.normal(0, 1.6, s.shape)
        seglen = np.sum(np.linalg.norm(np.diff(s, axis=0), axis=1))
        t = add(s, t, 0.02 + seglen / 6000, 10, "text") + 0.008
    t += 0.02
t += 0.03
for k, L in enumerate(prod):
    for s in L:
        s = s + RNG.normal(0, 0.8, s.shape)
        seglen = np.sum(np.linalg.norm(np.diff(s, axis=0), axis=1))
        t = add(s, t, 0.008 + seglen / 7000, 5, "text") + 0.004
    t += 0.008
T_PROD_END = t
# underline swoosh with a little flick at the end
x0, x1 = W / 2 - pw / 2 - 30, W / 2 + pw / 2 + 60
uu = np.linspace(0, 1, 40)
under = np.stack([x0 + (x1 - x0) * uu, P_BASE + 46 + 10 * np.sin(uu * math.pi) - 26 * np.clip((uu - 0.86) / 0.14, 0, 1) ** 2], 1)
t = add(under + RNG.normal(0, 1.2, under.shape), t + 0.06, 0.16, 6, "swoosh")
# doodle star (one stroke, five points) + two sparkle ticks, beside the logo's apex
sc_c = np.array([LOGO_C[0] + LOGO_H * 0.62, LOGO_C[1] - LOGO_H * 0.36])
star = np.array([sc_c + 58 * np.array([math.sin(a), -math.cos(a)]) for a in np.arange(0, 6) * 4 * math.pi / 5])
t = add(star + RNG.normal(0, 2.2, star.shape), t + 0.08, 0.22, 6, "star")
t = add(wobbly(sc_c + [80, -70], sc_c + [104, -94], 70, overshoot=(0, 2), amp=1), t + 0.03, 0.05, 5, "tick")
t = add(wobbly(sc_c + [92, -30], sc_c + [124, -30], 71, overshoot=(0, 2), amp=1), t + 0.02, 0.05, 5, "tick")
T_TAP = t + 0.12
T_DONE = T_TAP + 0.12
for s in STROKES:
    s["len"] = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(s["pts"], axis=0), axis=1))])


# ---------------------------------------------------------------- camera
def camera(t):
    keys = [(0.0, 1.34, (W / 2 - 60, 720)), (1.6, 1.32, (W / 2 + 40, 760)), (T_TEXT - 0.2, 1.30, (W / 2, 880)),
            (T_TEXT + 0.55, 1.24, (W / 2, 1180)), (T_PROD_END + 0.25, 1.0, (W / 2, H / 2)), (DUR, 1.0, (W / 2, H / 2))]
    for (ta, za, pa), (tb, zb, pb) in zip(keys[:-1], keys[1:]):
        if ta <= t <= tb:
            k = C.smoothstep(ta, tb, t)
            z = za + (zb - za) * k
            p = np.array(pa) + (np.array(pb) - np.array(pa)) * k
            break
    else:
        z, p = keys[-1][1], np.array(keys[-1][2])
    # keep the view inside the page
    hw, hh = W / 2 / z, H / 2 / z
    p = np.array([np.clip(p[0], hw, W - hw), np.clip(p[1], hh, H - hh)])
    return K.Cam(Z=z, P0=p, Q=(W / 2, H / 2))


def pencil_tip(t):
    """Where the pencil point is (design px) and how high it's lifted (0 = on the paper)."""
    prev = None
    for s in STROKES:
        if s["t0"] <= t <= s["t1"]:
            k = (t - s["t0"]) / (s["t1"] - s["t0"])
            L = s["len"]
            d = k * L[-1]
            j = min(len(L) - 2, int(np.searchsorted(L, d) - 1)) if L[-1] > 0 else 0
            j = max(j, 0)
            f = (d - L[j]) / max(L[j + 1] - L[j], 1e-6) if len(L) > 1 else 0
            return s["pts"][j] + (s["pts"][min(j + 1, len(s["pts"]) - 1)] - s["pts"][j]) * f, 0.0
        if s["t0"] > t:
            if prev is None:
                start = s["pts"][0] + np.array([500, -700])
                k = C.smoothstep(0, s["t0"], t)
                return start + (s["pts"][0] - start) * k, 1 - k
            k = C.smoothstep(prev["t1"], s["t0"], t)
            return prev["pts"][-1] + (s["pts"][0] - prev["pts"][-1]) * k, math.sin(math.pi * k) * 0.6
        prev = s
    last = STROKES[-1]["pts"][-1]
    if t < T_TAP:
        return last, 0.3 * C.smoothstep(STROKES[-1]["t1"], T_TAP, t)
    tap = T_TAP + 0.12
    if t < tap:                                   # the tap
        return last + np.array([40, 10]), 0.3 * (1 - C.smoothstep(T_TAP, tap, t))
    k = C.smoothstep(tap, tap + 0.8, t)
    return last + np.array([40, 10]) + np.array([900, -1200]) * k ** 1.6, 0.2 + 2 * k


def draw_pencil(img, tip, lift, cam):
    """A yellow hexagonal pencil, its shaved wood cone, graphite point, and a soft cast shadow."""
    z = cam.Z
    p = cam(tip)
    d = np.array([0.52, -0.855])                   # from the point toward the eraser end
    n = np.array([-d[1], d[0]])
    tipL, cone, body_w = 34 * z, 175 * z, 64 * z
    a0 = p
    a1 = p + d * tipL
    a2 = p + d * cone
    far = p + d * 4000
    shadow = np.zeros((H, W), np.float32)
    off = np.array([70, 95]) * (0.35 + lift) * z
    poly_body = np.array([a2 + n * body_w, far + n * body_w, far - n * body_w, a2 - n * body_w])
    poly_cone = np.array([a1 + n * 12 * z, a2 + n * body_w, a2 - n * body_w, a1 - n * 12 * z])
    for poly in (poly_body, poly_cone, np.array([a0, a1 + n * 12 * z, a1 - n * 12 * z])):
        cv2.fillPoly(shadow, [np.round((poly + off) * 4).astype(np.int32)], 1.0, cv2.LINE_AA, 2)
    shadow = cv2.GaussianBlur(shadow, (0, 0), 14 + 30 * lift)
    img *= (1 - 0.30 * shadow)[..., None]
    lay = np.zeros((H, W, 3), np.float32)
    msk = np.zeros((H, W), np.float32)

    def put(poly, col):
        pi = [np.round(np.asarray(poly) * 16).astype(np.int32)]
        cv2.fillPoly(lay, pi, tuple(float(c) for c in col), cv2.LINE_AA, 4)
        cv2.fillPoly(msk, pi, 1.0, cv2.LINE_AA, 4)

    # three visible facets of the hexagonal body
    for (s0, s1), col in (((-1, -0.34), K.rgb("#c98e12")), ((-0.34, 0.34), K.rgb("#f6c63b")), ((0.34, 1), K.rgb("#ffe28a"))):
        put([a2 + n * body_w * s0, far + n * body_w * s0, far + n * body_w * s1, a2 + n * body_w * s1], col)
    # shaved wood cone with a scalloped paint edge
    scal = [a2 + n * body_w * v + d * (12 * z * math.sin(v * math.pi * 3) ** 2) for v in np.linspace(-1, 1, 13)]
    put([a1 + n * 12 * z] + scal[::-1] + [a1 - n * 12 * z], K.rgb("#e9c9a0"))
    put([a1 + n * 12 * z, a1 + d * 40 * z + n * 22 * z, a1 + d * 40 * z - n * 3 * z, a1 - n * 12 * z], K.rgb("#d8b386"))
    put([a0, a1 + n * 12 * z, a1 - n * 12 * z], K.rgb("#3b3d44"))
    put([a0 + d * 3 * z, a1 + n * 3 * z, a1 + n * 10 * z], K.rgb("#7c7f89"))
    return img * (1 - msk[..., None]) + lay


def graphite(t, cam):
    """Every stroke drawn so far, rendered as graphite catching the paper's tooth."""
    cov = np.zeros((H, W), np.float32)
    for s in STROKES:
        if t < s["t0"]:
            break
        k = 1.0 if t >= s["t1"] else (t - s["t0"]) / (s["t1"] - s["t0"])
        L = s["len"]
        d = k * L[-1]
        m = int(np.searchsorted(L, d))
        pts = s["pts"][: max(2, m + 1)].copy()
        if m < len(L) and m > 0 and L[-1] > 0:
            f = (d - L[m - 1]) / max(L[m] - L[m - 1], 1e-6)
            pts[-1] = s["pts"][m - 1] + (s["pts"][min(m, len(s['pts']) - 1)] - s["pts"][m - 1]) * min(f, 1)
        sp = cam.polys([pts])[0]
        if len(sp) < 2:
            continue
        wpx = max(1, int(round(s["w"] * cam.Z)))
        pad = wpx + 3
        x0, y0 = np.floor(sp.min(0)).astype(int) - pad
        x1, y1 = np.ceil(sp.max(0)).astype(int) + pad
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1 <= x0 or y1 <= y0:
            continue
        lay = np.zeros((y1 - y0, x1 - x0), np.float32)
        cv2.polylines(lay, [np.round((sp - [x0, y0]) * 16).astype(np.int32)], False, 1.0, wpx, cv2.LINE_AA, 4)
        cov[y0:y1, x0:x1] += lay * (0.75 if s["kind"] in ("hatch", "hatch2") else 0.95)
    return cov


def frame(i):
    t = i / C.FPS
    cam = camera(t)
    M = np.float32([[cam.Z, 0, cam.Q[0] - cam.Z * cam.P0[0]], [0, cam.Z, cam.Q[1] - cam.Z * cam.P0[1]]])
    paper = cv2.warpAffine(PAPER, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    tooth = cv2.warpAffine(TOOTH, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
    cov = graphite(t, cam)
    g = (1 - np.exp(-cov * 1.6)) * (0.42 + 0.58 * tooth)
    img = paper * (1 - 0.9 * g[..., None]) + GRAPHITE * 0.9 * g[..., None] * 0.15
    tip, lift = pencil_tip(t)
    if not (t > T_TAP + 0.9):
        img = draw_pencil(img, tip, lift, cam)
    # macro depth of field: the top and bottom of the frame fall softly out of focus when we're close
    dof = (cam.Z - 1.0) / 0.34
    if dof > 0.02:
        small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        bl = C.up(cv2.GaussianBlur(small, (0, 0), 3.5))
        m = (np.clip((np.abs(yy[:, :1] - H / 2) / (H / 2) - 0.5) / 0.45, 0, 1) ** 1.5 * dof)[..., None]
        img = img * (1 - m) + bl * m
    return POST.finish(img, i, bloom=0.06, threshold=0.95)


# ---------------------------------------------------------------- sound
def audio():
    m = S.Mix(DUR)
    m.add(X.paper_rustle(0.7, seed=201, density=14), 0.0, gain=0.22, pan=0.2, send=0.2)
    m.add(S.sos(S.noise(DUR, "pink", 202), "lowpass", 900) * 0.6, 0.0, gain=0.05, send=0.0)      # quiet room tone
    for k, s in enumerate(STROKES):
        dur = s["t1"] - s["t0"]
        L = s["len"][-1]
        speed = min(1.0, L / dur / 3000)
        kind = s["kind"]
        n = max(4, int(dur * 60))
        sp = np.clip(np.sin(np.linspace(0.15, math.pi - 0.15, n)) ** 0.5 * (0.5 + 0.5 * speed), 0, 1)
        if kind in ("scribble", "hatch"):
            sp = sp * (0.6 + 0.4 * np.abs(np.sin(np.linspace(0, 40 if kind == "hatch" else 14, n))))
        x = X.pencil(dur + 0.03, sp, seed=300 + k, bright=1.0 if kind != "text" else 0.9)
        gain = {"line": 0.30, "scribble": 0.42, "hole": 0.14, "hatch": 0.34, "hatch2": 0.12, "text": 0.22,
                "swoosh": 0.36, "star": 0.30, "tick": 0.16}[kind]
        pan = float(np.clip((s["pts"][:, 0].mean() - W / 2) / (W / 2) * 0.6, -0.6, 0.6))
        m.add(x, s["t0"], gain=gain, pan=pan, send=0.12)
    m.add(X.tap(203, 0.8), T_TAP + 0.11, gain=0.5, pan=0.2, send=0.25)
    m.add(X.paper_rustle(0.9, seed=204, density=10), T_TAP + 0.3, gain=0.10, pan=-0.2, send=0.25)
    for k, f in enumerate((S.midi(72), S.midi(79), S.midi(84))):
        m.add(X.kalimba(f, 2.2), T_TAP + 0.12 + k * 0.05, gain=0.10, pan=-0.2 + 0.2 * k, send=0.5)
    mix = m.master(ir_seconds=1.4, wet=0.6, peak_db=-1.5, tail_fade=0.12)
    S.report(mix, NAME)
    return mix


if __name__ == "__main__":
    print(f"[{NAME}] {len(STROKES)} strokes, text starts {T_TEXT:.2f}s, tap {T_TAP:.2f}s")
    K.run(NAME, DUR, frame, audio, [6, 12, 20, 30, 42, 55, 66, 78, 90, 104, 118, 143], tag="ident02")
