"""
Artwork for printing on things (shirts, caps, bags): flat spot colours on a transparent background, described once in
millimetres and saved three ways: PNG at 300 dpi (with the brand's slightly soft printed edge), SVG and PDF (clean vector).

    p = Print(style, 260, 90)
    p.logo(100, 0, 40, "#F4E3DA")                 # x, y of the top-left corner, height, colour (all in mm)
    p.text("astris productions.", 130, 80, 30, "#F4E3DA")   # x, baseline, size
    p.save(folder / "astris-red-tshirt-front")    # -> .png .svg .pdf
"""
import numpy as np
from shapely.affinity import translate
from shapely.geometry import Polygon
from shapely.ops import unary_union

from . import type as T
from .core import hex_rgb, press, save_png_alpha
from .logo import fmt, path_d, raster_polys
from .pdf import MM, Doc, rgb as pdf_rgb


def shadow_shapes(polys, dx, dy):
    """The part of an offset copy of the logo that shows from behind it -> [(outer, [holes])]."""
    shapes = [Polygon(o, hs) for _, o, hs in polys]
    solid = unary_union([Polygon(o) for _, o, hs in polys])
    sh = unary_union([translate(s, dx, dy) for s in shapes]).difference(solid)
    geoms = list(sh.geoms) if hasattr(sh, "geoms") else [sh]
    return [(np.array(g.exterior.coords)[:-1], [np.array(r.coords)[:-1] for r in g.interiors]) for g in geoms if not g.is_empty and g.area > 1e-6]


class Print:
    def __init__(self, style, w_mm, h_mm, title=""):
        self.st, self.w, self.h, self.title = style, float(w_mm), float(h_mm), title
        self.ops = []

    # ---- describing the artwork ---------------------------------------------------------------------
    def logo(self, x, y, h, colour, strip=None, holes=True, shadow=None, parts=None):
        """strip: a second colour for the film strip. shadow: a colour for an offset copy behind (the risograph look)."""
        self.ops.append(dict(kind="logo", x=x, y=y, h=h, colour=colour, strip=strip, holes=holes, shadow=shadow, parts=parts))
        return self

    def logo_centred(self, cx, cy, h, colour, **kw):
        return self.logo(cx - h * self.st.logo.aspect / 2, cy - h / 2, h, colour, **kw)

    def text(self, s, x, y, size, colour, face=None, tracking=0.0, anchor="m", shadow=None):
        """One line: x is the anchor point (l / m / r), y the baseline, size the font size, all in mm."""
        face = face or self.st.display
        w = T.text_width(s, face, size, tracking)
        x0 = x - {"l": 0.0, "m": w / 2, "r": w}[anchor]
        self.ops.append(dict(kind="text", s=s, x=x0, y=y, size=size, colour=colour, face=face, tracking=tracking, shadow=shadow, w=w))
        return self

    def colours(self):
        out = []
        for o in self.ops:
            for c in (o.get("shadow"), o["colour"], o.get("strip")):
                if c and c.upper() not in out:
                    out.append(c.upper())
        return out

    def _logo_polys(self, o, k=1.0):
        return self.st.logo.polys(o["x"] * k, o["y"] * k, o["h"] * k, o["parts"])

    def _off(self, o):
        ref = o["h"] * 0.55 if o["kind"] == "logo" else o["size"]
        d = 0.030 * ref
        return d, d * 0.9

    # ---- raster -------------------------------------------------------------------------------------
    def image(self, width_px=None, dpi=300, soft=True):
        """-> (rgb float, alpha float). soft=True gives the edges the brand's slight ink bleed (no specks, no grain)."""
        k = (width_px / self.w) if width_px else dpi / 25.4
        W, H = int(round(self.w * k)), int(round(self.h * k))
        rgb = np.zeros((H, W, 3), np.float32)
        al = np.zeros((H, W), np.float32)
        s = max(1.0, W / 1700.0)
        ss = 4 if W <= 2400 else 2

        def over(m, colour, size, seed):
            nonlocal rgb, al
            if soft:
                m = press(m, size, s, seed=seed, bleed=self.st.bleed, rough=self.st.rough * 0.8, wear=0)
            c = hex_rgb(colour)
            rgb = rgb * (1 - m[..., None]) + c * m[..., None]
            al = al * (1 - m) + m

        for i, o in enumerate(self.ops):
            dx, dy = [v * k for v in self._off(o)]
            if o["kind"] == "logo":
                polys = self._logo_polys(o, k)
                if not o["holes"]:
                    polys = [(n, p, []) for n, p, _ in polys]
                size = o["h"] * k * 0.55
                if o["shadow"]:
                    sh = [("s", outer, holes) for outer, holes in shadow_shapes(polys, dx, dy)]
                    over(raster_polys(sh, (H, W), ss=ss), o["shadow"], size, f"sh{i}")
                for name, outer, holes in polys:
                    col = o["strip"] if (o["strip"] and name == "film-strip") else o["colour"]
                    over(raster_polys([(name, outer, holes)], (H, W), ss=ss), col, size, f"{i}{name}")
            else:
                m, (ox, oy) = T.text_mask(o["s"], o["face"], o["size"] * k, o["tracking"], ss=3 if o["size"] * k < 300 else 2)
                for colour, ddx, ddy in (((o["shadow"], dx, dy),) if o["shadow"] else ()) + ((o["colour"], 0, 0),):
                    full = np.zeros((H, W), np.float32)
                    px, py = int(round(o["x"] * k + ox + ddx)), int(round(o["y"] * k + oy + ddy))
                    y0, x0, y1, x1 = max(0, py), max(0, px), min(H, py + m.shape[0]), min(W, px + m.shape[1])
                    if y1 > y0 and x1 > x0:
                        full[y0:y1, x0:x1] = m[y0 - py:y1 - py, x0 - px:x1 - px]
                    over(full, colour, o["size"] * k, f"t{i}{colour}")
        straight = rgb / np.maximum(al, 1e-4)[..., None]
        if self.ops:
            straight[al < 1e-4] = hex_rgb(self.ops[-1]["colour"])
        return straight, al

    # ---- vector -------------------------------------------------------------------------------------
    def svg(self):
        L = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(self.w)}mm" height="{fmt(self.h)}mm" viewBox="0 0 {fmt(self.w)} {fmt(self.h)}">',
             f"  <title>{self.title}</title>", f"  <desc>Sizes are real: 1 unit = 1 mm. Spot colours: {', '.join(self.colours())}.</desc>"]
        for i, o in enumerate(self.ops):
            dx, dy = self._off(o)
            if o["kind"] == "logo":
                polys = self._logo_polys(o)
                if not o["holes"]:
                    polys = [(n, p, []) for n, p, _ in polys]
                if o["shadow"]:
                    d = " ".join(" ".join([path_d(outer, 3)] + [path_d(h, 3) for h in holes]) for outer, holes in shadow_shapes(polys, dx, dy))
                    L.append(f'  <path id="logo-shadow" fill="{o["shadow"]}" fill-rule="evenodd" d="{d}"/>')
                for name, outer, holes in polys:
                    col = o["strip"] if (o["strip"] and name == "film-strip") else o["colour"]
                    d = " ".join([path_d(outer, 3)] + [path_d(h, 3) for h in holes])
                    L.append(f'  <path id="logo-{name}" fill="{col}" fill-rule="evenodd" d="{d}"/>')
            else:
                if o["shadow"]:
                    d, _ = T.text_svg(o["s"], o["face"], o["size"], o["tracking"], o["x"] + dx, o["y"] + dy, nd=3)
                    L.append(f'  <path id="text-{i}-shadow" fill="{o["shadow"]}" d="{d}"/>')
                d, _ = T.text_svg(o["s"], o["face"], o["size"], o["tracking"], o["x"], o["y"], nd=3)
                L.append(f'  <path id="text-{i}" fill="{o["colour"]}" d="{d}"/>')
        L.append("</svg>")
        return "\n".join(L) + "\n"

    def pdf(self, path):
        doc = Doc(path, self.w, self.h, title=self.title)
        c = doc.c

        def fill(shapes, colour):
            c.setFillColorRGB(*pdf_rgb(colour))
            p = c.beginPath()
            for outer, holes in shapes:
                for poly in [outer] + list(holes):
                    p.moveTo(poly[0][0] * MM, (self.h - poly[0][1]) * MM)
                    for q in poly[1:]:
                        p.lineTo(q[0] * MM, (self.h - q[1]) * MM)
                    p.close()
            c.drawPath(p, stroke=0, fill=1, fillMode=0)
        for o in self.ops:
            dx, dy = self._off(o)
            if o["kind"] == "logo":
                polys = self._logo_polys(o)
                if not o["holes"]:
                    polys = [(n, p, []) for n, p, _ in polys]
                if o["shadow"]:
                    fill(shadow_shapes(polys, dx, dy), o["shadow"])
                for name, outer, holes in polys:
                    fill([(outer, holes)], o["strip"] if (o["strip"] and name == "film-strip") else o["colour"])
            else:
                pt = o["size"] * 72 / 25.4
                if o["shadow"]:
                    doc.text(o["x"] + dx, o["y"] + dy, o["s"], o["face"].key, pt, o["shadow"], tracking=o["tracking"])
                doc.text(o["x"], o["y"], o["s"], o["face"].key, pt, o["colour"], tracking=o["tracking"])
        doc.save()
        return path

    def save(self, stem, dpi=300):
        """stem: a path without extension -> stem.png (transparent, 300 dpi), stem.svg, stem.pdf"""
        rgb, al = self.image(dpi=dpi)
        save_png_alpha(rgb, al, stem.with_name(stem.name + ".png"), dpi=dpi)
        stem.with_name(stem.name + ".svg").write_text(self.svg())
        self.pdf(stem.with_name(stem.name + ".pdf"))
        return 3
