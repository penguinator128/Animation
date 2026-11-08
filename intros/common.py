"""
ASTRIS PRODUCTIONS - shared toolkit for the four 4K studio intros.

Everything a frame needs is a pure function of its time t, so frames can be rendered in any order,
in parallel, and nothing is ever dropped. Frames are piped as raw RGB into ffmpeg.
"""

# -- Your logo ---------------------------------------------------------------------------------
# Leave empty to auto-detect: logo.svg / logo.png / logo.jpg next to these scripts or in the repo
# root, then assets/astris-logo-source.jpg. Set a path here to force a specific file. If nothing
# is found, a simple five-point star placeholder is used (and a warning is printed).
LOGO_PATH = ""

import math
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import cv2
import numpy as np

# One OpenCV thread per process: frames are rendered by parallel worker processes instead, and a
# forked copy of a live OpenCV thread pool deadlocks.
cv2.setNumThreads(1)

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
OUT_DIR = ROOT / "output"
TEST_DIR = ROOT / "test-frames"
FONT_DIR = ROOT / "fonts"
W, H, FPS = 3840, 2160, 24

# ============================================================================================
# small maths
# ============================================================================================
def clamp(x, a=0.0, b=1.0):
    return np.minimum(b, np.maximum(a, x)) if isinstance(x, np.ndarray) else min(b, max(a, x))


def lerp(a, b, k):
    return a + (b - a) * k


def smoothstep(a, b, x):
    k = clamp((x - a) / (b - a)) if b != a else (1.0 if x >= b else 0.0)
    return k * k * (3 - 2 * k)


def expo_out(x, k=8.0):
    """1 - e^-kx, normalised so it lands exactly on 1 at x=1."""
    x = clamp(x)
    return (1 - math.exp(-k * x)) / (1 - math.exp(-k))


def expo_in(x, k=8.0):
    x = clamp(x)
    return (math.exp(k * x) - 1) / (math.exp(k) - 1)


def expo_in_out(x, k=8.0):
    x = clamp(x)
    return expo_in(2 * x, k) / 2 if x < 0.5 else 0.5 + expo_out(2 * x - 1, k) / 2


def spring(tau, w=14.0, zeta=0.55):
    """Damped spring step response (0 -> 1) as a function of time since release."""
    if tau <= 0:
        return 0.0
    if zeta >= 1:
        return 1 - (1 + w * tau) * math.exp(-w * tau)
    wd = w * math.sqrt(1 - zeta * zeta)
    return 1 - math.exp(-zeta * w * tau) * (math.cos(wd * tau) + zeta * w / wd * math.sin(wd * tau))


def pulse(t, t0, attack, decay):
    """Fast attack, exponential decay envelope centred on an event."""
    if t < t0 - attack:
        return 0.0
    if t < t0:
        return smoothstep(t0 - attack, t0, t)
    return math.exp(-(t - t0) / decay)


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def spectrum(u):
    """Smooth, saturated rainbow for u in [0,1] (red -> orange -> yellow -> green -> blue -> violet).
    Vectorised: u can be any array; returns (..., 3)."""
    u = np.asarray(u, np.float32)
    keys = np.array([0.0, 0.17, 0.33, 0.5, 0.67, 0.83, 1.0], np.float32)
    cols = np.array([[1.00, 0.10, 0.18], [1.00, 0.50, 0.05], [1.00, 0.88, 0.10], [0.15, 0.85, 0.35],
                     [0.10, 0.55, 1.00], [0.45, 0.25, 1.00], [0.85, 0.20, 0.95]], np.float32)
    uu = np.clip(u, 0, 1)
    out = np.stack([np.interp(uu, keys, cols[:, c]) for c in range(3)], -1).astype(np.float32)
    return out


def hue_wheel(u):
    """Cyclic rainbow (u wraps every 1.0)."""
    u = np.mod(np.asarray(u, np.float32), 1.0)
    keys = np.linspace(0, 1, 7).astype(np.float32)
    cols = np.array([[1.00, 0.12, 0.20], [1.00, 0.60, 0.05], [0.95, 0.95, 0.15], [0.15, 0.90, 0.40],
                     [0.10, 0.60, 1.00], [0.60, 0.25, 1.00], [1.00, 0.12, 0.20]], np.float32)
    return np.stack([np.interp(u, keys, cols[:, c]) for c in range(3)], -1).astype(np.float32)


# ============================================================================================
# logo: find it, trace it into exact polygons, draw it at any transform
# ============================================================================================
def find_logo():
    if LOGO_PATH:
        p = Path(LOGO_PATH)
        p = p if p.is_absolute() else (ROOT / p)
        if p.exists():
            return p
        print(f"[logo] LOGO_PATH {p} not found, auto-detecting", file=sys.stderr)
    for d in (ROOT, REPO):
        for n in ("logo.svg", "logo.png", "logo.jpg", "logo.jpeg", "logo.webp"):
            if (d / n).exists():
                return d / n
    p = REPO / "assets" / "astris-logo-source.jpg"
    return p if p.exists() else None


def _rasterize_svg(svg_path, out_png, height=2400):
    js = r"""
const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const [svg, out, h] = [process.argv[1], process.argv[2], +process.argv[3]];
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 64, height: 64 } });
  const src = 'data:image/svg+xml;base64,' + fs.readFileSync(svg).toString('base64');
  const [w] = await p.evaluate(async ([src, h]) => { const im = new Image(); im.src = src; await im.decode();
    return [Math.round(h * (im.naturalWidth || 1) / (im.naturalHeight || 1))]; }, [src, h]);
  await p.setViewportSize({ width: w + 64, height: h + 64 });
  await p.setContent(`<body style="margin:0;background:transparent"><img src="${src}" style="position:absolute;left:32px;top:32px;width:${w}px;height:${h}px"></body>`);
  await p.screenshot({ path: out, omitBackground: true }); await b.close();
})();"""
    subprocess.run(["node", "-e", js, str(svg_path), str(out_png), str(height)], check=True)


def _star_polys():
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        r = 0.5 if k % 2 == 0 else 0.2
        pts.append([r * math.cos(a), r * math.sin(a) + 0.04])
    return [np.array(pts, np.float64)], [0]


def trace_logo(path):
    """Returns (polys, depths) in logo units: centred on the logo's bounding box, height = 1.0."""
    from PIL import Image
    if path.suffix.lower() == ".svg":
        png = TEST_DIR / "_logo_svg_raster.png"
        png.parent.mkdir(parents=True, exist_ok=True)
        _rasterize_svg(path, png)
        path = png
    im = Image.open(path)
    mask = None
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        a = np.asarray(im.convert("RGBA"))[..., 3]
        if a.min() < 250:
            mask = (a > 127).astype(np.uint8) * 255
    if mask is None:
        g = np.asarray(im.convert("L"))
        border = np.concatenate([g[0], g[-1], g[:, 0], g[:, -1]])
        if np.median(border) > 127:      # dark logo on a light background
            g = 255 - g
        _, mask = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    up = max(1.0, 1800 / max(mask.shape))
    if up > 1:
        mask = cv2.resize(mask, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    contours, hier = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    hier = hier[0]
    depth = []
    for i in range(len(contours)):
        d, p = 0, hier[i][3]
        while p >= 0:
            d, p = d + 1, hier[p][3]
        depth.append(d)
    min_area = 2e-5 * mask.shape[0] * mask.shape[1]
    eps = 0.0008 * max(mask.shape)
    polys, depths = [], []
    for c, d in zip(contours, depth):
        if cv2.contourArea(c) < min_area:
            continue
        p = cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(np.float64)
        if len(p) >= 3:
            polys.append(p)
            depths.append(d)
    outer = np.concatenate([p for p, d in zip(polys, depths) if d == 0])
    x0, y0 = outer.min(0)
    x1, y1 = outer.max(0)
    c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
    s = 1.0 / (y1 - y0)
    return [(p - c) * s for p in polys], depths


class Logo:
    def __init__(self):
        path = find_logo()
        if path is None:
            print("[logo] No logo file found - using a star placeholder. Put logo.png/logo.svg next to "
                  "these scripts (or set LOGO_PATH in common.py) and re-run.", file=sys.stderr)
            self.polys, self.depths = _star_polys()
            self.source = None
        else:
            self.polys, self.depths = trace_logo(path)
            self.source = path
        allp = np.concatenate(self.polys)
        self.aspect = float(allp[:, 0].max() - allp[:, 0].min())   # width / height
        # group into pieces: each outer contour with the holes directly inside it
        self.pieces = []
        for i, d in enumerate(self.depths):
            if d % 2 == 0:
                holes = [j for j, dj in enumerate(self.depths) if dj == d + 1 and
                         cv2.pointPolygonTest(self.polys[i].astype(np.float32),
                                              tuple(map(float, self.polys[j][0])), False) > 0]
                self.pieces.append({"outer": i, "holes": holes})
        self.pieces.sort(key=lambda pc: self.polys[pc["outer"]][:, 0].mean())

    def piece_polys(self, k):
        pc = self.pieces[k]
        return [self.polys[pc["outer"]]] + [self.polys[j] for j in pc["holes"]]

    def transform(self, polys, cx, cy, h, rot=0.0, sx=1.0):
        c, s = math.cos(rot), math.sin(rot)
        out = []
        for p in polys:
            x, y = p[:, 0] * h * sx, p[:, 1] * h
            out.append(np.stack([cx + c * x - s * y, cy + s * x + c * y], 1))
        return out

    def polys_px(self, cx, cy, h, rot=0.0, pieces=None, sx=1.0):
        src = self.polys if pieces is None else [q for k in pieces for q in self.piece_polys(k)]
        return self.transform(src, cx, cy, h, rot, sx)

    def mask(self, cx, cy, h, rot=0.0, pieces=None, shape=(H, W), sx=1.0):
        return poly_mask(self.polys_px(cx, cy, h, rot, pieces, sx), shape)


def poly_mask(polys_px, shape=(H, W)):
    """Anti-aliased even-odd fill of polygons (pixel coords, subpixel precise) -> float32 [0,1]."""
    m = np.zeros(shape, np.uint8)
    pts = [np.round(p * 256).astype(np.int32) for p in polys_px if len(p) >= 3]
    if pts:
        cv2.fillPoly(m, pts, 255, cv2.LINE_AA, shift=8)
    return m.astype(np.float32) * (1 / 255)


def poly_mask_ss(polys_px, shape=(H, W), ss=2):
    """Supersampled version for very crisp edges on hero shapes."""
    big = poly_mask([p * ss for p in polys_px], (shape[0] * ss, shape[1] * ss))
    return cv2.resize(big, (shape[1], shape[0]), interpolation=cv2.INTER_AREA)


# ============================================================================================
# vector type: glyph outlines from the font files, drawn exactly like the logo
# ============================================================================================
class Font:
    def __init__(self, path):
        from fontTools.ttLib import TTFont
        f = TTFont(str(path))
        self.upm = f["head"].unitsPerEm
        self.cap = getattr(f["OS/2"], "sCapHeight", 0) or int(self.upm * 0.7)
        self.gs = f.getGlyphSet()
        self.cmap = f.getBestCmap()
        self.hmtx = f["hmtx"]
        self._cache = {}

    def glyph(self, ch):
        if ch in self._cache:
            return self._cache[ch]
        from fontTools.pens.basePen import BasePen

        class Flatten(BasePen):
            def __init__(s, gs):
                super().__init__(gs)
                s.contours, s.cur = [], []

            def _moveTo(s, p):
                s.cur = [p]

            def _lineTo(s, p):
                s.cur.append(p)

            def _curveToOne(s, p1, p2, p3):
                p0 = s.cur[-1]
                for i in range(1, 17):
                    t = i / 16
                    m = 1 - t
                    s.cur.append((m ** 3 * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t ** 3 * p3[0],
                                  m ** 3 * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t ** 3 * p3[1]))

            def _qCurveToOne(s, p1, p2):
                p0 = s.cur[-1]
                for i in range(1, 13):
                    t = i / 12
                    m = 1 - t
                    s.cur.append((m * m * p0[0] + 2 * m * t * p1[0] + t * t * p2[0],
                                  m * m * p0[1] + 2 * m * t * p1[1] + t * t * p2[1]))

            def _closePath(s):
                if len(s.cur) > 2:
                    s.contours.append(np.array(s.cur, np.float64))
                s.cur = []

            _endPath = _closePath

        name = self.cmap.get(ord(ch))
        pen = Flatten(self.gs)
        if name and ch != " ":
            self.gs[name].draw(pen)
        adv = self.hmtx[name][0] if name else self.upm * 0.3
        # font units (y up) -> em units (y down)
        cont = [np.stack([c[:, 0] / self.upm, -c[:, 1] / self.upm], 1) for c in pen.contours]
        self._cache[ch] = (cont, adv / self.upm)
        return self._cache[ch]


def layout_word(font, text, cap_px, tracking_em=0.0, width_px=None):
    """Lays out a word on a baseline at x=0..width, returns list of (contours_px, x_left, ink_x0, ink_x1),
    plus the ink width. If width_px is given, tracking is solved so the ink spans exactly that width."""
    size = cap_px * font.upm / font.cap
    glyphs = [font.glyph(ch) for ch in text]
    advs = [g[1] * size for g in glyphs]
    inks = []
    for cont, _ in glyphs:
        if cont:
            xs = np.concatenate([c[:, 0] for c in cont]) * size
            inks.append((xs.min(), xs.max()))
        else:
            inks.append((0.0, 0.0))

    def place(track_px):
        x, out = 0.0, []
        for (cont, _), a, (i0, i1) in zip(glyphs, advs, inks):
            out.append(([c * size + [x, 0] for c in cont], x, x + i0, x + i1))
            x += a + track_px
        return out

    track = tracking_em * size
    if width_px is not None and len(text) > 1:
        base = place(0.0)
        natural = base[-1][3] - base[0][2]
        track = (width_px - natural) / (len(text) - 1)
    placed = place(track)
    x0 = placed[0][2]
    placed = [([c - [x0, 0] for c in cont], xl - x0, i0 - x0, i1 - x0) for cont, xl, i0, i1 in placed]
    return placed, placed[-1][3]


# ============================================================================================
# the shared lockup: logo on top, ASTRIS large, PRODUCTIONS justified underneath
# ============================================================================================
ASTRIS_FONT = FONT_DIR / "syncopate-700.ttf"
PROD_FONT = FONT_DIR / "montserrat-500.ttf"


class Lockup:
    LOGO_H, GAP1, ASTRIS_CAP, GAP2, PROD_CAP = 800.0, 170.0, 150.0, 80.0, 46.0
    ASTRIS_TRACK = 0.30

    def __init__(self, logo):
        self.logo = logo
        fa, fp = Font(ASTRIS_FONT), Font(PROD_FONT)
        self.astris, aw = layout_word(fa, "ASTRIS", self.ASTRIS_CAP, self.ASTRIS_TRACK)
        self.prod, pw = layout_word(fp, "PRODUCTIONS", self.PROD_CAP, width_px=aw * 0.985)
        self.astris_w, self.prod_w = aw, pw
        total = self.LOGO_H + self.GAP1 + self.ASTRIS_CAP + self.GAP2 + self.PROD_CAP
        self.anchor = np.array([W / 2, H / 2 - 22.0])   # optical centre, a touch above the middle
        top = -total / 2
        self.logo_c = np.array([0.0, top + self.LOGO_H / 2])            # relative to anchor
        self.astris_base = top + self.LOGO_H + self.GAP1 + self.ASTRIS_CAP
        self.prod_base = self.astris_base + self.GAP2 + self.PROD_CAP

    def logo_xy(self, S=1.0, off=(0, 0)):
        p = self.anchor + np.asarray(off) + S * self.logo_c
        return float(p[0]), float(p[1]), self.LOGO_H * S

    def logo_polys(self, S=1.0, off=(0, 0), rot=0.0, pieces=None):
        cx, cy, h = self.logo_xy(S, off)
        return self.logo.polys_px(cx, cy, h, rot, pieces)

    def word_polys(self, which, S=1.0, off=(0, 0), track_mul=1.0, letter_dy=None, letter_dx=None,
                   letter_scale=None):
        """Per-letter polygon lists for 'astris' or 'prod' in screen pixels."""
        placed, width, base = ((self.astris, self.astris_w, self.astris_base) if which == "astris"
                               else (self.prod, self.prod_w, self.prod_base))
        n = len(placed)
        out = []
        for k, (cont, xl, i0, i1) in enumerate(placed):
            mid = (i0 + i1) / 2
            gx = (mid - width / 2) * track_mul           # letter centre relative to word centre
            ls = 1.0 if letter_scale is None else letter_scale[k]
            dy = 0.0 if letter_dy is None else letter_dy[k]
            dx = 0.0 if letter_dx is None else letter_dx[k]
            polys = []
            for c in cont:
                lx = (c[:, 0] - mid) * ls + gx + dx
                ly = c[:, 1] * ls + base + dy
                px = self.anchor[0] + off[0] + S * lx
                py = self.anchor[1] + off[1] + S * ly
                polys.append(np.stack([px, py], 1))
            out.append(polys)
        return out

    def word_mask(self, which, S=1.0, off=(0, 0), alpha=None, shape=(H, W), **kw):
        letters = self.word_polys(which, S, off, **kw)
        m = np.zeros(shape, np.float32)
        for k, polys in enumerate(letters):
            a = 1.0 if alpha is None else float(alpha[k])
            if a <= 0.002:
                continue
            draw_polys_max(m, polys, a)
        return m


def draw_polys_max(target, polys, value=1.0, pad=3):
    """Fills polygons into a float32 mask in their bounding box only: target = max(target, value*cov)."""
    allp = np.concatenate(polys)
    x0 = int(max(0, math.floor(allp[:, 0].min()) - pad))
    y0 = int(max(0, math.floor(allp[:, 1].min()) - pad))
    x1 = int(min(target.shape[1], math.ceil(allp[:, 0].max()) + pad))
    y1 = int(min(target.shape[0], math.ceil(allp[:, 1].max()) + pad))
    if x1 <= x0 or y1 <= y0:
        return
    roi = poly_mask([p - [x0, y0] for p in polys], (y1 - y0, x1 - x0))
    np.maximum(target[y0:y1, x0:x1], roi * value, out=target[y0:y1, x0:x1])


# ============================================================================================
# finishing: bloom, highlight roll-off, vignette, film grain
# ============================================================================================
class Post:
    def __init__(self, seed=1, grain=0.028, vignette=0.30, vig_inner=0.30, grain_size=1.0, grain_floor=0.12):
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2 * 0.85)
        self.vig = (1 - vignette * np.clip((r - vig_inner) / (1.35 - vig_inner), 0, 1) ** 1.6).astype(np.float32)
        self.grain_amt = grain
        self.grain_floor = grain_floor
        tiles = []
        for size in (1031, 997):
            g = rng.standard_normal((size, size)).astype(np.float32)
            g = cv2.GaussianBlur(g, (0, 0), grain_size)       # soft 1-2 px clumps, like a 4K film scan
            tiles.append(g / g.std())
        self.tiles = tiles
        self.rng_seed = seed

    def grain(self, frame):
        r = np.random.default_rng(self.rng_seed * 1000 + frame)
        out = np.zeros((H, W), np.float32)
        for t in self.tiles:
            n = t.shape[0]
            oy, ox = r.integers(0, n, 2)
            rolled = np.roll(np.roll(t, oy, 0), ox, 1)
            reps = (H // n + 2, W // n + 2)
            out += np.tile(rolled, reps)[:H, :W]
        return out * (1 / math.sqrt(len(self.tiles)))

    @staticmethod
    def bloom(img, strength=0.6, threshold=0.75, radii=(1.0, 1.0, 1.0)):
        small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        lum = small.max(axis=2, keepdims=True)
        knee = np.clip((lum - threshold) / max(1e-4, 1.0 - threshold), 0, None)
        bright = small * (knee / (1 + knee))
        b1 = cv2.GaussianBlur(bright, (0, 0), 3.0)
        s2 = cv2.resize(bright, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        b2 = cv2.GaussianBlur(s2, (0, 0), 6.0)
        s3 = cv2.resize(s2, (W // 32, H // 32), interpolation=cv2.INTER_AREA)
        b3 = cv2.GaussianBlur(s3, (0, 0), 6.0)
        acc = b1 * radii[0] + cv2.resize(b2, (W // 4, H // 4)) * radii[1] * 1.3 + \
            cv2.resize(b3, (W // 4, H // 4), interpolation=cv2.INTER_CUBIC) * radii[2] * 1.6
        return cv2.resize(acc * strength, (W, H), interpolation=cv2.INTER_LINEAR)

    def finish(self, img, frame, bloom=0.6, threshold=0.75, radii=(1.0, 1.0, 1.0), grain=None,
               exposure=1.0, vignette=True, extra_bloom=None):
        if exposure != 1.0:
            img = img * exposure
        if bloom > 0:
            b = self.bloom(img, bloom, threshold, radii)
            img = img + b
        if extra_bloom is not None:
            img = img + extra_bloom
        # highlights bleed toward white, then roll off smoothly instead of clipping
        hot = np.clip(img.max(axis=2, keepdims=True) - 1.0, 0, None)
        img = img + hot * 0.6
        knee = 0.82
        over = np.clip(img - knee, 0, None)
        img = np.where(img > knee, knee + (1 - knee) * (1 - np.exp(-over / (1 - knee))), img)
        if vignette:
            img = img * self.vig[..., None]
        g = self.grain_amt if grain is None else grain
        if g > 0:
            lum = img.mean(axis=2)
            amp = g * (self.grain_floor + 2.8 * lum * np.clip(1 - lum, 0, 1))   # quietest in deep blacks
            img = img + (self.grain(frame) * amp)[..., None]
        return np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8)


# ============================================================================================
# camera helpers
# ============================================================================================
def warp(img, dx=0.0, dy=0.0, rot_deg=0.0, zoom=1.0, center=(W / 2, H / 2), border=cv2.BORDER_REFLECT101):
    M = cv2.getRotationMatrix2D(center, rot_deg, zoom)
    M[0, 2] += dx
    M[1, 2] += dy
    return cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=border)


def chromatic(img, amount, center=(W / 2, H / 2)):
    """Radial chromatic aberration: red scaled out, blue scaled in."""
    if amount <= 0:
        return img
    out = img.copy()
    for ch, s in ((0, 1 + amount), (2, 1 - amount)):
        M = cv2.getRotationMatrix2D(center, 0, s)
        out[..., ch] = cv2.warpAffine(img[..., ch], M, (W, H), flags=cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_REFLECT101)
    return out


def shake_offsets(t, seed, freqs=(6.3, 11.7, 17.1, 23.9)):
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 2 * math.pi, (3, len(freqs)))
    w = np.array([1.0, 0.6, 0.35, 0.2])
    v = [float(np.sum(w * np.sin(2 * math.pi * np.array(freqs) * t + ph[i]))) / 1.4 for i in range(3)]
    return v  # dx, dy, rot (unit amplitude)


def small_grid(scale=4):
    h, w = H // scale, W // scale
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx * scale + scale / 2, yy * scale + scale / 2


def up(img_small):
    return cv2.resize(img_small, (W, H), interpolation=cv2.INTER_LINEAR)


def add_glow_mask(img, mask, color, sigmas=(6, 24, 80), weights=(0.6, 0.35, 0.25), scale=4):
    """Adds a soft coloured glow around a mask (computed at low resolution)."""
    sm = cv2.resize(mask, (W // scale, H // scale), interpolation=cv2.INTER_AREA)
    acc = np.zeros_like(sm)
    for s, wgt in zip(sigmas, weights):
        acc += cv2.GaussianBlur(sm, (0, 0), s / scale) * wgt
    img += up(acc)[..., None] * np.asarray(color, np.float32)
    return img


# ============================================================================================
# output: parallel frame rendering piped into ffmpeg
# ============================================================================================
def ffmpeg_cmd(out_path, wav_path, crf=15, preset="slow"):
    return ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-i", str(wav_path), "-map", "0:v:0", "-map", "1:a:0",
            "-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p",
            "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-profile:v", "high",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", "-shortest", str(out_path)]


def _worker_init():
    cv2.setNumThreads(1)


def render_video(name, n_frames, frame_fn, wav_path, workers=3, crf=15, preset="slow"):
    """frame_fn(i) -> HxWx3 uint8 RGB. Frames are rendered in parallel but written strictly in order."""
    import multiprocessing as mp
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{name}.mp4"
    proc = subprocess.Popen(ffmpeg_cmd(out, wav_path, crf, preset), stdin=subprocess.PIPE)
    t0 = time.time()
    ctx = mp.get_context("fork")
    with ctx.Pool(workers, initializer=_worker_init) as pool:
        for i, fr in enumerate(pool.imap(_as_bytes, [(frame_fn, k) for k in range(n_frames)], chunksize=1)):
            proc.stdin.write(fr)
            if i % 24 == 0 or i == n_frames - 1:
                el = time.time() - t0
                print(f"[{name}] frame {i + 1}/{n_frames}  {el:6.1f}s elapsed  "
                      f"eta {el / (i + 1) * (n_frames - i - 1):6.1f}s", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    print(f"[{name}] wrote {out}")
    return out


def _as_bytes(args):
    fn, k = args
    fr = fn(k)
    assert fr.shape == (H, W, 3) and fr.dtype == np.uint8
    return fr.tobytes()


def save_test_frames(name, frame_fn, frames, sheet_cols=4, rendered=None):
    """Renders chosen frames at full 4K (or takes already-rendered ones), saves PNGs and a contact sheet."""
    import multiprocessing as mp
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    thumbs = []
    if rendered is None:
        with mp.get_context("fork").Pool(min(4, len(frames))) as pool:
            rendered = pool.map(frame_fn, list(frames), chunksize=1)
    for k, fr in zip(frames, rendered):
        p = TEST_DIR / f"{name}_f{k:03d}.png"
        cv2.imwrite(str(p), cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))
        th = cv2.resize(fr, (960, 540), interpolation=cv2.INTER_AREA)
        cv2.putText(th, f"f{k} t={k / FPS:.2f}s", (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2,
                    cv2.LINE_AA)
        thumbs.append(th)
    while len(thumbs) % sheet_cols:
        thumbs.append(np.zeros_like(thumbs[0]))
    rows = [np.concatenate(thumbs[i:i + sheet_cols], 1) for i in range(0, len(thumbs), sheet_cols)]
    sheet = np.concatenate(rows, 0)
    sp = TEST_DIR / f"{name}_sheet.jpg"
    cv2.imwrite(str(sp), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    return sp


def crop_png(src, x, y, w, h, out):
    im = cv2.imread(str(src))
    cv2.imwrite(str(out), im[y:y + h, x:x + w])
    return out
