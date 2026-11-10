"""
Lettering: shaping (kerning via HarfBuzz), tracking, crisp masks and vector outlines.

    face = Face("anton-400")
    m, (ox, oy) = text_mask("astris productions.", face, size=300, tracking=0.01)     # mask + offset from the text origin
    d = text_svg(...)                                                                 # the same text as SVG path data

Sizes are font sizes in pixels (like CSS). Tracking is in ems (0.1 = 10% of the font size added after every letter).
"""
from functools import lru_cache

import cv2
import numpy as np
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

from .paths import FONTS


class Face:
    _cache = {}

    def __new__(cls, key):
        if key not in cls._cache:
            self = super().__new__(cls)
            self.key = key
            self.path = FONTS / f"{key}.ttf"
            if not self.path.exists():
                raise FileNotFoundError(f"font file missing: {self.path} (see fonts.md)")
            self.tt = TTFont(str(self.path))
            self.upm = self.tt["head"].unitsPerEm
            os2 = self.tt["OS/2"]
            self.cap = getattr(os2, "sCapHeight", 0) / self.upm or 0.7
            self.xh = getattr(os2, "sxHeight", 0) / self.upm or 0.5
            self.asc = self.tt["hhea"].ascent / self.upm
            self.desc = -self.tt["hhea"].descent / self.upm
            self.hbfont = hb.Font(hb.Face(self.path.read_bytes()))
            self.glyphs = self.tt.getGlyphSet()
            self.order = self.tt.getGlyphOrder()
            cls._cache[key] = self
        return cls._cache[key]

    @lru_cache(maxsize=64)
    def pil(self, px):
        return ImageFont.truetype(str(self.path), px, layout_engine=ImageFont.Layout.BASIC)


def shape(text, face, size, tracking=0.0):
    """-> [(char, glyph name, x)], total advance width (px). Kerning on, ligatures off (one glyph per letter)."""
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(face.hbfont, buf, {"kern": True, "liga": False, "clig": False, "calt": False})
    s = size / face.upm
    x = 0.0
    out = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        out.append((text[info.cluster], face.order[info.codepoint], x + pos.x_offset * s))
        x += pos.x_advance * s + tracking * size
    return out, x - tracking * size


def text_width(text, face, size, tracking=0.0):
    return shape(text, face, size, tracking)[1]


def fit_size(text, face, width, tracking=0.0, max_size=None):
    """Font size at which `text` is exactly `width` px wide."""
    w1 = text_width(text, face, 1000.0, tracking)
    size = 1000.0 * width / w1
    return min(size, max_size) if max_size else size


def text_mask(text, face, size, tracking=0.0, ss=None):
    """Anti-aliased coverage mask of one line. Returns (mask float32, (ox, oy)): paste the mask's top-left at
    (x + ox, baseline_y + oy) to put the text's left edge at x and its baseline at baseline_y."""
    glyphs, width = shape(text, face, size, tracking)
    ss = ss or (4 if size < 120 else 3 if size < 500 else 2)
    pad = int(size * 0.25) + 4
    W = int(width + 2 * pad) + 2
    asc, desc = int(face.asc * size) + pad, int(face.desc * size) + pad
    H = asc + desc
    im = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    f = face.pil(int(round(size * ss)))
    for ch, _, x in glyphs:
        if ch.strip():
            d.text(((pad + x) * ss, asc * ss), ch, font=f, fill=255, anchor="ls")
    m = np.asarray(im, np.float32) / 255.0
    if ss > 1:
        m = cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA)
    return m, (-pad, -asc)


def text_svg(text, face, size, tracking=0.0, x=0.0, y=0.0, nd=2):
    """SVG path data for the line with its left edge at x and baseline at y (true outlines, no font needed)."""
    glyphs, width = shape(text, face, size, tracking)
    s = size / face.upm
    pen = SVGPathPen(face.glyphs, ntos=lambda v: f"{v:.{nd}f}".rstrip("0").rstrip(".") or "0")
    for ch, gname, gx in glyphs:
        if ch.strip():
            face.glyphs[gname].draw(TransformPen(pen, (s, 0, 0, -s, x + gx, y)))
    return pen.getCommands(), width


def ink_bounds(mask, thr=0.5):
    """Bounding box (x0, y0, x1, y1) of the inked pixels of a mask, or None."""
    ys, xs = np.nonzero(mask > thr)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
