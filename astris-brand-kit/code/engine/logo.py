"""
The logo, as clean vector geometry.

LOGO_SOURCE is the one place the original artwork is named. code/logo_pack/analyse_logo.py measures it and writes
logo-geometry.json (the FAITHFUL and GEOMETRIC versions); everything in the kit draws from that file.
If the logo or its geometry is missing, a simple five-point star is used instead and a warning is printed.
"""
import json
import math
import sys

import cv2
import numpy as np

from .paths import CODE, ORIGINALS

# ------------------------------------------------------------------------------------------------
LOGO_SOURCE = ORIGINALS / "astris-logo-original.jpg"        # <- swap the logo here, then re-run analyse_logo.py
# ------------------------------------------------------------------------------------------------
GEOMETRY_FILE = CODE / "logo_pack" / "logo-geometry.json"


def _star():
    pts = []
    for k in range(10):
        r = 8.0 if k % 2 == 0 else 3.2
        a = -math.pi / 2 + k * math.pi / 5
        pts.append([8.0 + r * math.cos(a), 8.0 + r * math.sin(a)])
    return {"version": "placeholder-star", "width": 16.0, "height": 16.0,
            "parts": [{"name": "star", "outer": pts, "holes": []}], "tones": {"star": 1.0}}


def load_geometry(version="geometric"):
    if not LOGO_SOURCE.exists() or not GEOMETRY_FILE.exists():
        print(f"WARNING: logo not found ({LOGO_SOURCE.name}); using a star placeholder", file=sys.stderr)
        return _star()
    return json.loads(GEOMETRY_FILE.read_text())[version]


class Logo:
    """The mark in 'logo units' (19 wide x 16 high for the real logo), with helpers to place and rasterise it."""

    def __init__(self, version="geometric"):
        self.geo = load_geometry(version)
        self.version = self.geo["version"]
        self.w, self.h = float(self.geo["width"]), float(self.geo["height"])
        self.aspect = self.w / self.h
        self.parts = self.geo["parts"]
        self.part_names = [p["name"] for p in self.parts]

    # ---- geometry ---------------------------------------------------------------------------
    def polys(self, x=0.0, y=0.0, height=1.0, parts=None):
        """[(name, outer Nx2, [hole Nx2...])] placed with its top-left at (x, y) and the given height (any units)."""
        s = height / self.h
        out = []
        for p in self.parts:
            if parts is not None and p["name"] not in parts:
                continue
            o = np.asarray(p["outer"], np.float64) * s + [x, y]
            hs = [np.asarray(h["pts"], np.float64) * s + [x, y] for h in p["holes"]]
            out.append((p["name"], o, hs))
        return out

    def centred(self, cx, cy, height, parts=None):
        return self.polys(cx - height * self.aspect / 2, cy - height / 2, height, parts)

    def hole_names(self):
        return [h["name"] for p in self.parts for h in p["holes"]]

    # ---- raster -----------------------------------------------------------------------------
    def mask(self, shape, x, y, height, parts=None, ss=4, holes=True, only_holes=None):
        """Anti-aliased coverage mask (float32 0..1) on a canvas of `shape` (H, W)."""
        return raster_polys(self.polys(x, y, height, parts), shape, ss=ss, holes=holes, only_holes=only_holes)

    def mask_centred(self, shape, cx, cy, height, parts=None, ss=4):
        return self.mask(shape, cx - height * self.aspect / 2, cy - height / 2, height, parts, ss)

    def tight(self, width_px, parts=None, ss=None, pad=0):
        """Tightly cropped mask of the whole mark at a given pixel width (+ optional transparent padding)."""
        hpx = int(round(width_px / self.aspect))
        ss = ss or (4 if width_px <= 4096 else 2)
        return self.mask((hpx + 2 * pad, int(width_px) + 2 * pad), pad, pad, width_px / self.aspect, parts, ss)


def raster_polys(polys, shape, ss=4, holes=True, only_holes=None):
    """Even-odd rasterise [(name, outer, holes)] with ss x ss supersampling. Memory-friendly: works in bands."""
    H, W = shape
    out = np.zeros((H, W), np.float32)
    band = max(64, int(40_000_000 // max(1, W * ss * ss)))          # rows per band so the big buffer stays < ~40 MB
    SH = 4
    for y0 in range(0, H, band):
        y1 = min(H, y0 + band)
        buf = np.zeros(((y1 - y0) * ss, W * ss), np.uint8)
        off = np.array([0.0, -y0])

        def P(a):
            return np.round(((a + off) * ss + (ss - 1) / 2.0) * (1 << SH)).astype(np.int32)
        for name, o, hs in polys:
            if only_holes is None:
                cv2.fillPoly(buf, [P(o)], 255, cv2.LINE_AA, SH)
            if holes or only_holes is not None:
                for k, h in enumerate(hs):
                    if only_holes is not None:
                        if only_holes is True or k in only_holes:
                            cv2.fillPoly(buf, [P(h)], 255, cv2.LINE_AA, SH)
                    else:
                        cv2.fillPoly(buf, [P(h)], 0, cv2.LINE_AA, SH)
        if ss > 1:
            buf = cv2.resize(buf, (W, y1 - y0), interpolation=cv2.INTER_AREA)
        out[y0:y1] = buf.astype(np.float32) / 255.0
    return out


# ---- vector export helpers -----------------------------------------------------------------------
def fmt(v, nd=3):
    s = f"{v:.{nd}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def path_d(pts, nd=3):
    return "M" + " L".join(f"{fmt(p[0], nd)} {fmt(p[1], nd)}" for p in pts) + " Z"


def svg_paths(logo, scale=100.0, nd=3, parts=None):
    """{part name: path data (outer + holes, for fill-rule evenodd)} with 1 logo unit = `scale` SVG units."""
    out = {}
    for name, o, hs in logo.polys(0, 0, logo.h * scale, parts):
        out[name] = " ".join([path_d(o, nd)] + [path_d(h, nd) for h in hs])
    return out
