"""
The shared look: flat colour fields, fine film grain, lettering with a touch of ink bleed, and two-ink risograph printing.

    art = Art(style, 2560, 1440)                 # a canvas in one of the three styles
    art.text("astris productions.", cx, y, size=310)
    art.logo(cx, cy, height=400)
    img = art.render()                           # float RGB 0..1, grain and all
    save_png(img, path)

Every style goes through the same code; only the settings in brand-config.json differ.
"""
import math

import cv2
import numpy as np
from PIL import Image

from . import type as T
from .logo import Logo, raster_polys

cv2.setNumThreads(1)  # OpenCV's own thread pool deadlocks in forked render workers; frames are parallelised instead
REF = 1440.0          # design reference: a 2560 x 1440 banner is "scale 1"


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def rgb_hex(c):
    return "#%02X%02X%02X" % tuple(int(round(float(v) * 255)) for v in c)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def rng_for(*keys):
    """A repeatable random generator for any combination of names/numbers (so re-renders are identical)."""
    h = 2166136261
    for k in keys:
        for ch in str(k):
            h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return np.random.default_rng(h)


# ----------------------------------------------------------------------------------------------------
# grain
# ----------------------------------------------------------------------------------------------------
def grain_field(h, w, seed, sigma=0.55):
    """Fine, even, monochrome grain: unit-variance noise with the faintest softening so it reads as film, not static.
    No low frequencies, so it can never look blotchy."""
    r = rng_for("grain", seed)
    g = r.standard_normal((h, w), dtype=np.float32)
    if sigma > 0.25:
        g = cv2.GaussianBlur(g, (0, 0), sigma)
        g *= 1.0 / max(1e-6, float(g[: min(h, 512), : min(w, 512)].std()))
    return g


def apply_grain(rgb, g, amount, lift=0.5):
    """amount ~ 0.07 = roughly 7% noise on a flat colour. Part of it scales with the colour (like ink density),
    part is added evenly (like film grain), so it shows on every colour without ever changing the hue much."""
    km, ka = amount * (1 - lift) * 1.15, amount * lift
    return rgb * (1.0 + km * g[..., None]) + ka * g[..., None]


# ----------------------------------------------------------------------------------------------------
# ink: soft, slightly irregular edges and the odd pinhole, as if printed
# ----------------------------------------------------------------------------------------------------
def soft_noise(h, w, r, cell):
    """Smooth noise with features about `cell` px across, unit variance."""
    gh, gw = max(2, int(h / cell) + 2), max(2, int(w / cell) + 2)
    n = r.standard_normal((gh, gw), dtype=np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
    return n / max(1e-6, float(n.std()))


def press(mask, size, s=1.0, seed=0, bleed=1.0, rough=1.0, wear=1.0):
    """Turn a crisp coverage mask into printed ink.
    size: the lettering's font size in px (big type gets a little more bleed; small type stays readable)."""
    h, w = mask.shape
    r = rng_for("press", seed, h, w)
    sig = float(np.clip(0.0042 * size, 0.38 * s, 1.25 * s)) * bleed
    m = cv2.GaussianBlur(mask, (0, 0), sig) if sig > 0.2 else mask
    if rough > 0:
        amp = float(np.clip(size / (260.0 * s), 0.25, 1.0)) * rough
        n = soft_noise(h, w, r, max(3.0, size / 16.0)) * 0.6 + soft_noise(h, w, r, max(1.6, size / 55.0)) * 0.4
        m = m + 0.085 * amp * n * (4.0 * m * (1.0 - m))            # only moves the edge, never the solid areas
    a = smoothstep(0.5 - 0.30, 0.5 + 0.30, m + 0.035)               # slightly soft edge, a hair of ink gain
    if wear > 0:
        # pinholes: tiny, sparse specks where the ink didn't quite take
        k = max(1.0, 1.15 * s)
        sp = r.random((int(h / k) + 1, int(w / k) + 1), dtype=np.float32)
        sp = (sp > 1.0 - 0.0009 * wear).astype(np.float32)
        sp = cv2.resize(cv2.GaussianBlur(sp, (0, 0), 0.6), (w, h), interpolation=cv2.INTER_LINEAR)
        a = a * (1.0 - np.clip(sp * 3.2, 0, 0.75))
    return np.clip(a, 0.0, 1.0)


# ----------------------------------------------------------------------------------------------------
# paper (for the risograph style)
# ----------------------------------------------------------------------------------------------------
def paper_texture(h, w, s, seed):
    """Multiplicative paper texture ~1.0: short fibres and a very soft mottle. (Grain is added separately.)"""
    r = rng_for("paper", seed, h, w)
    tex = np.ones((h, w), np.float32)
    # fibres, drawn small and anti-aliased on an 8-bit layer
    lay = np.zeros((h, w), np.uint8)
    lay2 = np.zeros((h, w), np.uint8)
    n = int(h * w / (5200.0 * s * s))
    xs, ys = r.uniform(0, w, n), r.uniform(0, h, n)
    ang, ln = r.uniform(0, math.pi, n), r.uniform(9, 34, n) * s
    bend = r.normal(0, 0.35, n)
    for k in range(n):
        pts = []
        for t in (-0.5, -0.17, 0.17, 0.5):
            a = ang[k] + bend[k] * t
            pts.append([(xs[k] + math.cos(a) * ln[k] * t) * 16, (ys[k] + math.sin(a) * ln[k] * t) * 16])
        cv2.polylines(lay if k % 3 else lay2, [np.asarray(pts, np.int32)], False, int(r.integers(90, 255)), max(1, int(round(0.9 * s))), cv2.LINE_AA, 4)
    tex -= cv2.GaussianBlur(lay, (0, 0), 0.45 * s).astype(np.float32) / 255.0 * 0.050
    tex += cv2.GaussianBlur(lay2, (0, 0), 0.45 * s).astype(np.float32) / 255.0 * 0.030
    tex *= 1.0 + 0.004 * soft_noise(h, w, r, 260 * s)
    return tex


# ----------------------------------------------------------------------------------------------------
# the canvas
# ----------------------------------------------------------------------------------------------------
class Art:
    """One piece of artwork in a style. Layers are kept as cropped masks, so even poster sizes stay light."""

    def __init__(self, style, w, h, scheme="main", seed=None, scale=None, grain=True):
        self.style, self.W, self.H = style, int(w), int(h)
        self.sch = style.scheme(scheme)
        self.scheme_name = scheme
        self.s = float(scale) if scale else max(1.0, min(w, h) / REF)
        self.seed = seed if seed is not None else f"{style.key}-{w}x{h}-{scheme}"
        self.layers = []                      # (kind, x0, y0, mask, size, opts)
        self.with_grain = grain
        self.logo_obj = style.logo
        self.tag = "main"                     # layers remember the tag that was current when they were added (for animation)

    # ---- adding ink ---------------------------------------------------------------------------------
    def add(self, mask, x0=0, y0=0, role="ink", size=None, colour=None, **opts):
        """Add a coverage mask (float 0..1) with its top-left at (x0, y0). role: 'ink' (lettering colour),
        'second' (the supporting colour), 'field' (knock back to the background) or 'colour' (+ colour=hex)."""
        x0, y0 = int(round(x0)), int(round(y0))
        h, w = mask.shape
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(self.W, x0 + w), min(self.H, y0 + h)
        if cx1 <= cx0 or cy1 <= cy0:
            return self
        m = np.ascontiguousarray(mask[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0], np.float32)
        size = size or 200.0 * self.s
        sch = self.sch
        if sch["mode"] == "riso":
            if sch.get("flood") and role == "ink":
                role = "field"                                      # reverse print: lettering is bare paper in a flood of ink
            elif role == "ink" and sch.get("shadow") and opts.pop("shadow", True):
                # the second ink, printed first and offset down-right, shows as a soft shadow behind the lettering
                off = max(2.5 * self.s, sch["shadow"] * size) * opts.get("shadow_scale", 1.0)
                self._push("second", cx0 + off, cy0 + off * 0.9, m, size, dict(opts, colour=None, tag=self.tag + "~"))
        opts.pop("shadow", None)
        self._push(role, cx0, cy0, m, size, dict(colour=colour, **opts))
        return self

    def _push(self, role, x0, y0, m, size, opts):
        x0, y0 = int(round(x0)), int(round(y0))
        h, w = m.shape
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(self.W, x0 + w), min(self.H, y0 + h)
        if cx1 > cx0 and cy1 > cy0:
            opts = dict(opts, tag=opts.get("tag") or self.tag)
            self.layers.append((role, cx0, cy0, np.ascontiguousarray(m[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]), size, opts))

    def text(self, string, x, y, size, face=None, tracking=0.0, anchor="mm", role="ink", colour=None, **opts):
        """One line of lettering. anchor: l/m/r + s (baseline) / m (middle of the x-height or cap height) / t (cap top).
        Returns the line's (x0, y_baseline, width)."""
        face = face or self.style.display
        m, (ox, oy) = T.text_mask(string, face, size, tracking)
        width = T.text_width(string, face, size, tracking)
        ref = face.cap if (string.upper() == string and any(c.isalpha() for c in string)) else face.xh
        x0 = x - {"l": 0.0, "m": width / 2, "r": width}[anchor[0]]
        yb = y + {"s": 0.0, "m": ref * size / 2, "t": face.cap * size, "b": -face.desc * size}[anchor[1]]
        self.add(m, x0 + ox, yb + oy, role=role, size=size, colour=colour, **opts)
        return x0, yb, width

    def logo(self, cx, cy, height, role="ink", parts=None, colour=None, size=None, solid=False, **opts):
        """solid=True draws the parts without their sprocket holes (so the holes can be punched in later)."""
        lg = self.logo_obj
        wpx = height * lg.aspect
        pad = 6
        x0, y0 = int(math.floor(cx - wpx / 2)) - pad, int(math.floor(cy - height / 2)) - pad
        shape = (int(math.ceil(height)) + 2 * pad + 2, int(math.ceil(wpx)) + 2 * pad + 2)
        ss = 4 if height < 2400 else 2
        m = lg.mask(shape, cx - wpx / 2 - x0, cy - height / 2 - y0, height, parts, ss=ss, holes=not solid)
        if self.sch["mode"] == "riso" and self.sch.get("shadow") and role == "ink" and opts.get("shadow", True) and not self.sch.get("flood"):
            # print the shadow, then clear it from under the whole silhouette (holes included) so the holes show paper
            sz = size or height * 0.55
            off = max(2.5 * self.s, self.sch["shadow"] * sz) * opts.get("shadow_scale", 1.0)
            self._push("second", x0 + off, y0 + off * 0.9, m, sz, {"colour": None, "tag": self.tag + "~"})
            solid_m = lg.mask(shape, cx - wpx / 2 - x0, cy - height / 2 - y0, height, parts, ss=ss, holes=False)
            self._push("clear_second", x0, y0, solid_m, sz, {"crisp": True, "tag": self.tag + "~"})
            opts = dict(opts, shadow=False)
        self.add(m, x0, y0, role=role, size=size or height * 0.55, colour=colour, **opts)
        return self

    def rect(self, x0, y0, x1, y1, role="ink", radius=0, colour=None, size=None, **opts):
        w, h = int(round(x1 - x0)), int(round(y1 - y0))
        m = rounded_mask(h, w, radius)
        self.add(m, x0, y0, role=role, size=size or min(w, h), colour=colour, **opts)
        return self

    def polygon(self, pts, role="ink", colour=None, size=None, **opts):
        pts = np.asarray(pts, np.float64)
        x0, y0 = np.floor(pts.min(0)).astype(int) - 3
        x1, y1 = np.ceil(pts.max(0)).astype(int) + 3
        m = raster_polys([("p", pts - [x0, y0], [])], (y1 - y0, x1 - x0), ss=4)
        self.add(m, x0, y0, role=role, size=size or float(min(x1 - x0, y1 - y0)), colour=colour, **opts)
        return self

    def circle(self, cx, cy, r, role="ink", colour=None, ring=None, **opts):
        pad = 3
        n = int(2 * r) + 2 * pad + 2
        x0, y0 = int(math.floor(cx - r)) - pad, int(math.floor(cy - r)) - pad
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
        d = np.hypot(xx - (cx - x0), yy - (cy - y0))
        m = np.clip(r - d + 0.5, 0, 1)
        if ring:
            m = m * np.clip(d - (r - ring) + 0.5, 0, 1)
        self.add(m, x0, y0, role=role, size=opts.pop("size", r), colour=colour, **opts)
        return self

    # ---- compositing --------------------------------------------------------------------------------
    def _pressed(self, k, layer):
        role, x0, y0, m, size, opts = layer
        st = self.style
        if opts.get("crisp"):
            return m
        return press(m, size, self.s, seed=f"{self.seed}-{k}", bleed=st.bleed * opts.get("bleed", 1.0),
                     rough=st.rough * opts.get("rough", 1.0), wear=st.wear * opts.get("wear", 1.0))

    def render(self, grain=None):
        st, sch = self.style, self.sch
        H, W = self.H, self.W
        if sch["mode"] == "riso":
            img = self._render_riso()
        else:
            img = np.empty((H, W, 3), np.float32)
            img[:] = sch["field"]
            for k, layer in enumerate(self.layers):
                role, x0, y0, m, size, opts = layer
                if role == "clear_second":
                    continue
                a = self._pressed(k, layer) * opts.get("alpha", 1.0)
                col = sch["field"] if role == "field" else hex_rgb(opts["colour"]) if role == "colour" else sch[role]
                reg = img[y0:y0 + m.shape[0], x0:x0 + m.shape[1]]
                reg[:] = reg * (1 - a[..., None]) + col * a[..., None]
        if self.with_grain if grain is None else grain:
            g = grain_field(H, W, self.seed, st.grain_sigma * self.s)
            img = apply_grain(img, g, st.grain_amount * sch.get("grain_gain", 1.0), st.grain_lift)
        return np.clip(img, 0.0, 1.0)

    def _render_riso(self):
        """Two inks on paper. Inks multiply (overprint), the second plate is slightly out of register,
        and each ink has its own density mottle and speckle."""
        st, sch = self.style, self.sch
        H, W, s = self.H, self.W, self.s
        plates = {"ink": np.zeros((H, W), np.float32), "second": np.zeros((H, W), np.float32)}
        flood = sch.get("flood")                                   # a plate printed solid edge to edge (reverse print)
        if flood:
            plates[flood][:] = 1.0
        extra = []
        for k, layer in enumerate(self.layers):
            role, x0, y0, m, size, opts = layer
            a = self._pressed(k, layer) * opts.get("alpha", 1.0)
            sl = (slice(y0, y0 + m.shape[0]), slice(x0, x0 + m.shape[1]))
            if role == "field":                                    # knock out of every plate: bare paper shows
                for p in plates.values():
                    p[sl] *= (1 - a)
            elif role == "clear_second":
                plates["second"][sl] *= (1 - a)
            elif role == "colour":
                extra.append((sl, a, hex_rgb(opts["colour"])))
            else:
                if opts.get("knockout", (role == "ink") != bool(flood)):   # lettering knocks the other ink out beneath it,
                    other = "second" if role == "ink" else "ink"           # leaving only a hairline of overprint (trap)
                    trap = opts.get("trap", 0.0)
                    ko = a if trap <= 0 else np.clip(cv2.erode(a, np.ones((3, 3), np.uint8), iterations=max(1, int(round(trap * s)))), 0, 1)
                    plates[other][sl] *= (1 - ko)
                plates[role][sl] = np.maximum(plates[role][sl], a)
        r = rng_for("riso", self.seed)
        paper = paper_texture(H, W, s, self.seed)
        img = sch["field"][None, None, :] * paper[..., None]
        dx, dy = sch.get("misregister", (2.0, 1.4))
        for name in ("second", "ink"):                             # the second colour is printed first
            a = plates[name]
            if not a.any():
                continue
            if name == "second" and (dx or dy):
                Mx = np.float32([[1, 0, dx * s], [0, 1, dy * s]])
                a = cv2.warpAffine(a, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            dens = 0.978 + 0.022 * np.clip(soft_noise(H, W, r, 420 * s), -2, 1)       # roller density: barely there
            fine = grain_field(H, W, f"{self.seed}-{name}", 0.7 * s)
            mott = 1.0 - 0.10 * st.wear * np.clip(fine - 0.4, 0, 2.5)                  # soy-ink speckle
            a = a * dens * mott
            ink = sch[name]
            img *= 1.0 - a[..., None] * (1.0 - ink[None, None, :])
        for sl, a, col in extra:
            reg = img[sl]
            reg[:] = reg * (1 - a[..., None]) + col * a[..., None]
        return img


def rounded_mask(h, w, radius, ss=4):
    if radius <= 0:
        return np.ones((h, w), np.float32)
    im = np.zeros((h * ss, w * ss), np.uint8)
    r = int(min(radius, min(h, w) / 2) * ss)
    cv2.rectangle(im, (r, 0), (w * ss - r - 1, h * ss - 1), 255, -1)
    cv2.rectangle(im, (0, r), (w * ss - 1, h * ss - r - 1), 255, -1)
    for cx, cy in ((r, r), (w * ss - r - 1, r), (r, h * ss - r - 1), (w * ss - r - 1, h * ss - r - 1)):
        cv2.circle(im, (cx, cy), r, 255, -1, cv2.LINE_AA)
    return cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


# ----------------------------------------------------------------------------------------------------
# saving
# ----------------------------------------------------------------------------------------------------
def to_u8(img):
    return np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)


def save_png(img, path, palette=True, dpi=None, max_err=1.6):
    """Flat-colour-plus-grain artwork is saved as an 8-bit indexed PNG (256 colours chosen for this image): it looks
    identical and is about a third of the size. Falls back to 24-bit if 256 colours can't hold it."""
    u8 = to_u8(img) if img.dtype != np.uint8 else img
    im = Image.fromarray(u8, "RGB")
    kw = {"optimize": True}
    if dpi:
        kw["dpi"] = (dpi, dpi)
    if palette:
        q = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        back = np.asarray(q.convert("RGB"), np.int16)
        step = max(1, u8.shape[0] // 700)
        err = float(np.abs(back[::step, ::step] - u8[::step, ::step].astype(np.int16)).mean())
        if err <= max_err:
            q.save(path, **kw)
            return path
    im.save(path, **kw)
    return path


def save_png_alpha(img, alpha, path, dpi=None, hard_palette=False):
    """RGBA PNG. hard_palette=True: indexed with one fully transparent colour (for grainy die-cut artwork with bleed)."""
    u8 = to_u8(img)
    kw = {"optimize": True}
    if dpi:
        kw["dpi"] = (dpi, dpi)
    if hard_palette:
        q = Image.fromarray(u8, "RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        idx = np.asarray(q).copy()
        idx[alpha < 0.5] = 255
        out = Image.fromarray(idx, "P")
        pal = (q.getpalette() or [])[: 255 * 3]
        out.putpalette(pal + [0] * (768 - len(pal)))
        out.save(path, transparency=255, **kw)
        return path
    a8 = to_u8(alpha)
    Image.fromarray(np.dstack([u8, a8]), "RGBA").save(path, **kw)
    return path


def save_jpg(img, path, quality=92, dpi=None):
    kw = {"quality": quality, "subsampling": 0, "optimize": True}
    if dpi:
        kw["dpi"] = (dpi, dpi)
    Image.fromarray(to_u8(img), "RGB").save(path, **kw)
    return path
