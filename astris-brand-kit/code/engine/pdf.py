"""
PDF pages with real (selectable, vector) text in the brand fonts, vector logos, and artwork from the engine.
Coordinates are in millimetres from the TOP-LEFT of the page.

    doc = Doc(path, 210, 297, title="...")
    doc.fill("#F4E3DA"); doc.logo(20, 20, 18, "#C23A3A"); doc.text(20, 60, "Hello", "anton-400", 28, "#1A1210")
    doc.page(); ...; doc.save()
"""
from pathlib import Path

import numpy as np
from PIL import Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas

from .core import to_u8
from .paths import FONTS, WORK

MM = 72 / 25.4
_registered = set()


def font(key):
    if key not in _registered:
        pdfmetrics.registerFont(TTFont(key, str(FONTS / f"{key}.ttf")))
        _registered.add(key)
    return key


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


class Doc:
    def __init__(self, path, w_mm, h_mm, title="", author="ASTRIS PRODUCTIONS"):
        self.path, self.w, self.h = Path(path), w_mm, h_mm
        self.c = pdfcanvas.Canvas(str(path), pagesize=(w_mm * MM, h_mm * MM))
        self.c.setTitle(title)
        self.c.setAuthor(author)
        self._tmp = []
        self.pages = 1

    def _y(self, y):
        return (self.h - y) * MM

    def page(self):
        self.c.showPage()
        self.pages += 1

    def save(self):
        self.c.showPage()
        self.c.save()
        for t in self._tmp:
            Path(t).unlink(missing_ok=True)

    # ---- shapes -----------------------------------------------------------------------------------------
    def fill(self, colour):
        self.rect(0, 0, self.w, self.h, colour)

    def rect(self, x, y, w, h, colour=None, stroke=None, width=0.5, radius=0, dash=None):
        c = self.c
        if colour:
            c.setFillColorRGB(*rgb(colour))
        if stroke:
            c.setStrokeColorRGB(*rgb(stroke))
            c.setLineWidth(width)
            c.setDash(*(dash or ([], 0)))
        if radius:
            c.roundRect(x * MM, self._y(y + h), w * MM, h * MM, radius * MM, stroke=1 if stroke else 0, fill=1 if colour else 0)
        else:
            c.rect(x * MM, self._y(y + h), w * MM, h * MM, stroke=1 if stroke else 0, fill=1 if colour else 0)
        if dash:
            c.setDash([], 0)

    def line(self, x0, y0, x1, y1, colour, width=0.5, dash=None):
        c = self.c
        c.setStrokeColorRGB(*rgb(colour))
        c.setLineWidth(width)
        if dash:
            c.setDash(*dash)
        c.line(x0 * MM, self._y(y0), x1 * MM, self._y(y1))
        if dash:
            c.setDash([], 0)

    def circle(self, cx, cy, r, colour=None, stroke=None, width=0.5):
        c = self.c
        if colour:
            c.setFillColorRGB(*rgb(colour))
        if stroke:
            c.setStrokeColorRGB(*rgb(stroke))
            c.setLineWidth(width)
        c.circle(cx * MM, self._y(cy), r * MM, stroke=1 if stroke else 0, fill=1 if colour else 0)

    def logo(self, logo, x, y, h, colour, parts=None):
        """The logo as vector paths, top-left at (x, y), h mm tall."""
        c = self.c
        c.setFillColorRGB(*rgb(colour))
        for name, o, hs in logo.polys(x, y, h, parts):
            p = c.beginPath()
            for poly in [o] + hs:
                p.moveTo(poly[0][0] * MM, self._y(poly[0][1]))
                for q in poly[1:]:
                    p.lineTo(q[0] * MM, self._y(q[1]))
                p.close()
            c.drawPath(p, stroke=0, fill=1, fillMode=0)

    # ---- images -----------------------------------------------------------------------------------------
    def image(self, img, x, y, w, h=None, quality=90, key=None):
        """img: a float/uint8 array, a PIL image or a path. Arrays are embedded as JPEG; the same key is embedded once."""
        if isinstance(img, (str, Path)):
            src = str(img)
            iw, ih = Image.open(src).size
        else:
            pil = img if isinstance(img, Image.Image) else Image.fromarray(to_u8(img) if img.dtype != np.uint8 else img)
            iw, ih = pil.size
            WORK.mkdir(parents=True, exist_ok=True)
            src = str(WORK / f"_pdf_{key or id(img)}_{self.path.stem}.jpg")
            if pil.mode == "RGBA":
                src = src[:-4] + ".png"
                pil.save(src)
            else:
                pil.convert("RGB").save(src, quality=quality, subsampling=0)
            self._tmp.append(src)
        h = h if h is not None else w * ih / iw
        self.c.drawImage(src, x * MM, self._y(y + h), w * MM, h * MM, mask="auto")
        return h

    # ---- text -------------------------------------------------------------------------------------------
    def text(self, x, y, string, face, size, colour, anchor="l", tracking=0.0):
        """One line; y is the baseline. size in pt, tracking in em. Returns the width in mm."""
        c = self.c
        f = font(face)
        cs = tracking * size
        w = pdfmetrics.stringWidth(string, f, size) + cs * max(0, len(string) - 1)
        x0 = x * MM - {"l": 0, "m": w / 2, "r": w}[anchor]
        t = c.beginText(x0, self._y(y))
        t.setFont(f, size)
        t.setFillColorRGB(*rgb(colour))
        t.setCharSpace(cs)          # always set it: character spacing otherwise carries over from the previous line
        t.textOut(string)
        c.drawText(t)
        return w / MM

    def width(self, string, face, size, tracking=0.0):
        return (pdfmetrics.stringWidth(string, font(face), size) + tracking * size * max(0, len(string) - 1)) / MM

    def para(self, x, y, string, face, size, colour, width, leading=1.45, tracking=0.0, anchor="l", max_lines=None):
        """Wrapped text; y is the first baseline. Returns the y of the line after the last one."""
        f = font(face)
        lines = []
        for block in string.split("\n"):
            words, cur = block.split(), ""
            for wd in words:
                trial = (cur + " " + wd).strip()
                if self.width(trial, f, size, tracking) <= width or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = wd
            lines.append(cur)
        if max_lines:
            lines = lines[:max_lines]
        lh = size * leading / MM
        for i, l in enumerate(lines):
            xx = x + {"l": 0, "m": width / 2, "r": width}[anchor]
            self.text(xx, y + i * lh, l, f, size, colour, anchor=anchor, tracking=tracking)
        return y + len(lines) * lh

    def placeholder(self, x, y, w, h, label, colour, face, size=8, radius=2):
        self.rect(x, y, w, h, stroke=colour, width=0.6, radius=radius, dash=([3, 2.2], 0))
        lines = label.split("\n")
        lh = size * 1.4 / MM
        y0 = y + h / 2 - lh * (len(lines) - 1) / 2 + size * 0.35 / MM
        for i, l in enumerate(lines):
            self.text(x + w / 2, y0 + i * lh, l, face, size, colour, anchor="m", tracking=0.04)

    def crop_marks(self, x, y, w, h, length=4.0, gap=1.5, colour="#000000"):
        """Trim marks around the box (x, y, w, h)."""
        for cx, sx in ((x, -1), (x + w, 1)):
            for cy, sy in ((y, -1), (y + h, 1)):
                self.line(cx + sx * gap, cy, cx + sx * (gap + length), cy, colour, 0.25)
                self.line(cx, cy + sy * gap, cx, cy + sy * (gap + length), colour, 0.25)


def to_png_pages(pdf_path, out_prefix, width_px):
    """Rasterise every page with poppler: out_prefix-01.png, -02.png ... Returns the list of files."""
    import subprocess
    pdf_path = Path(pdf_path)
    subprocess.run(["pdftoppm", "-png", "-scale-to-x", str(width_px), "-scale-to-y", "-1", str(pdf_path), str(out_prefix)], check=True)
    return sorted(Path(out_prefix).parent.glob(Path(out_prefix).name + "-*.png"))
