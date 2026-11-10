"""
Stickers: twelve designs in different shapes, each as
  - print-ready artwork (PNG, 300 dpi, with 2 mm of bleed past the cut line),
  - an SVG that places that artwork under a VECTOR CUT LINE on its own layer,
plus one A4 sheet of all twelve (PNG + PDF with the cut lines as vectors).
"""
import math

import cv2
import numpy as np
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas
from shapely.geometry import Polygon
from shapely.ops import unary_union

from assets.youtube import logo_fit
from engine import lockup as L
from engine import type as T
from engine.core import Art, rounded_mask, save_png, save_png_alpha, to_u8
from engine.paths import out
from engine.style import config

DPI = 300
MM = DPI / 25.4
BLEED = 2.0                # mm of artwork past the cut line
CUT_COLOUR = "#FF00FF"     # the usual "CutContour" magenta


def designs(style):
    """(name, shape, size in mm, scheme, draw(art, cx, cy, w, h))"""
    k = style.key
    b = config()["brand"]
    dl = "second" if k == "red" else "ink"          # logo colour on the dark scheme

    def big_logo(art, cx, cy, w, h, fill=0.66, role="ink"):
        lx, ly, lh = logo_fit(style, min(w, h), fill)
        art.logo(cx - min(w, h) / 2 + lx, cy - min(w, h) / 2 + ly, lh, role=role)

    return [
        ("01-circle-logo", "circle", (60, 60), "main", lambda a, cx, cy, w, h: big_logo(a, cx, cy, w, h)),
        ("02-circle-wordmark", "circle", (60, 60), "main", lambda a, cx, cy, w, h: L.stacked(a, cx, cy, w * 0.60)),
        ("03-circle-dark-logo", "circle", (50, 50), "dark", lambda a, cx, cy, w, h: big_logo(a, cx, cy, w, h, role=dl)),
        ("04-rounded-lockup", "rrect", (90, 50, 6), "main", lambda a, cx, cy, w, h: L.horizontal(a, cx, cy, h * 0.42)),
        ("05-rounded-name", "rrect", (100, 36, 6), "main", lambda a, cx, cy, w, h: L.name_line(a, cx, cy - h * 0.07, w * 0.80, tag_scale=0.22)),
        ("06-die-cut-logo", "diecut", (70, 0, 4), "light", lambda a, cx, cy, w, h: None),
        ("07-wordmark-bar", "rrect", (120, 24, 4), "dark", lambda a, cx, cy, w, h: a.text(b["name"], cx, cy, T.fit_size(b["name"], style.display, w * 0.84, 0.10), tracking=0.10, anchor="mm")),
        ("08-logo-dot", "circle", (25, 25), "main", lambda a, cx, cy, w, h: big_logo(a, cx, cy, w, h, 0.62)),
        ("09-tagline-pill", "pill", (80, 22), "main", lambda a, cx, cy, w, h: a.text(style.tagline, cx, cy, T.fit_size(style.tagline, style.display, w * 0.70, 0.08, max_size=h * 0.62), tracking=0.08, anchor="mm")),
        ("10-presents-ticket", "rrect", (90, 40, 5), "light", lambda a, cx, cy, w, h: presents(a, cx, cy, w, h)),
        ("11-square-logo", "rrect", (50, 50, 8), "light", lambda a, cx, cy, w, h: big_logo(a, cx, cy, w, h, 0.60)),
        ("12-oval-wordmark", "ellipse", (75, 48), "dark", lambda a, cx, cy, w, h: L.stacked(a, cx, cy, w * 0.50)),
    ]


def presents(art, cx, cy, w, h):
    b = config()["brand"]
    s1 = T.fit_size(b["name"], art.style.display, w * 0.78, 0.06)
    art.text(b["name"], cx, cy - h * 0.10, s1, tracking=0.06, anchor="mm")
    art.text("presents", cx, cy + h * 0.24, s1 * 0.52, face=art.style.text_face(500), tracking=0.30, anchor="mm", shadow=False)


def shape_mask(shape, dims, h, w, grow_px):
    """Coverage of the sticker shape (centred on an h x w canvas), grown by grow_px."""
    cx, cy = w / 2, h / 2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if shape == "circle":
        return np.clip(dims[0] * MM / 2 + grow_px - np.hypot(xx - cx, yy - cy) + 0.5, 0, 1)
    if shape == "ellipse":
        a, b = dims[0] * MM / 2 + grow_px, dims[1] * MM / 2 + grow_px
        d = np.hypot((xx - cx) / a, (yy - cy) / b)
        return np.clip((1 - d) * min(a, b) + 0.5, 0, 1)
    ww, hh = dims[0] * MM + 2 * grow_px, dims[1] * MM + 2 * grow_px
    r = (min(dims[0], dims[1]) / 2 if shape == "pill" else dims[2]) * MM + grow_px
    m = np.zeros((h, w), np.float32)
    rm = rounded_mask(int(round(hh)), int(round(ww)), r)
    y0, x0 = int(round(cy - hh / 2)), int(round(cx - ww / 2))
    m[y0:y0 + rm.shape[0], x0:x0 + rm.shape[1]] = rm
    return m


def diecut_outline(style, width_mm, border_mm):
    """The logo's outline pushed out by border_mm, as polygons in mm, origin at the centre."""
    lg = style.logo
    hmm = width_mm / lg.aspect
    polys = lg.polys(-width_mm / 2, -hmm / 2, hmm)
    u = unary_union([Polygon(o) for _, o, _ in polys]).buffer(border_mm, join_style=1, resolution=24)
    u = u.buffer(3.0, join_style=1).buffer(-3.0, join_style=1)          # close the notch between the two legs
    geoms = list(u.geoms) if hasattr(u, "geoms") else [u]
    return [np.asarray(g.exterior.coords)[:-1] for g in geoms], hmm


def cut_svg(shape, dims, die=None):
    if shape == "circle":
        return f'<circle cx="0" cy="0" r="{dims[0] / 2:.3f}"/>'
    if shape == "ellipse":
        return f'<ellipse cx="0" cy="0" rx="{dims[0] / 2:.3f}" ry="{dims[1] / 2:.3f}"/>'
    if shape == "diecut":
        return "".join('<path d="M' + " L".join(f"{p[0]:.3f} {p[1]:.3f}" for p in poly) + ' Z"/>' for poly in die)
    r = min(dims[0], dims[1]) / 2 if shape == "pill" else dims[2]
    return f'<rect x="{-dims[0] / 2:.3f}" y="{-dims[1] / 2:.3f}" width="{dims[0]:.3f}" height="{dims[1]:.3f}" rx="{r:.3f}"/>'


def make(style, d):
    """-> dict(name, img (float rgb), alpha, size_mm (w, h) of the canvas, cut (svg fragment), cut_polys/params)."""
    name, shape, dims, scheme, draw = d
    die = None
    if shape == "diecut":
        die, hmm = diecut_outline(style, dims[0], dims[2])
        allp = np.concatenate(die)
        wmm, hmm_c = float(allp[:, 0].max() - allp[:, 0].min()), float(allp[:, 1].max() - allp[:, 1].min())
        off = np.array([(allp[:, 0].max() + allp[:, 0].min()) / 2, (allp[:, 1].max() + allp[:, 1].min()) / 2])
        die = [p - off for p in die]
    else:
        wmm, hmm_c = dims[0], dims[1]
    cw, ch = int(round((wmm + 2 * BLEED + 2) * MM)), int(round((hmm_c + 2 * BLEED + 2) * MM))
    art = Art(style, cw, ch, scheme=scheme, scale=1.0, seed=f"{style.key}-sticker-{name}")
    cx, cy = cw / 2, ch / 2
    if shape == "diecut":
        lg = style.logo
        hpx = dims[0] / lg.aspect * MM
        art.logo(cx - off[0] * MM, cy - off[1] * MM, hpx)
        m8 = np.zeros((ch, cw), np.uint8)
        for poly in [Polygon(p).buffer(BLEED, join_style=1) for p in die]:
            pts = np.asarray(poly.exterior.coords) * MM + [cx, cy]
            cv2.fillPoly(m8, [np.round(pts * 16).astype(np.int32)], 255, cv2.LINE_AA, 4)
        alpha = m8.astype(np.float32) / 255
    else:
        draw(art, cx, cy, wmm * MM, hmm_c * MM)
        alpha = shape_mask(shape, dims, ch, cw, BLEED * MM)
    return {"name": name, "img": art.render(), "alpha": alpha, "size_mm": (cw / MM, ch / MM), "shape": shape, "dims": dims, "die": die,
            "cut": cut_svg(shape, dims, die), "trim_mm": (wmm, hmm_c)}


def sticker_svg(st, png_name, title):
    w, h = st["size_mm"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w:.2f}mm" height="{h:.2f}mm" '
            f'viewBox="{-w / 2:.3f} {-h / 2:.3f} {w:.3f} {h:.3f}">\n  <title>{title}</title>\n'
            f'  <!-- Units are millimetres. Layer 1 is the artwork (300 dpi, with {BLEED:g} mm of bleed). Layer 2 is the cut line:\n'
            f'       a vector hairline in magenta. Most print shops call this layer "CutContour"; rename it if yours asks. -->\n'
            f'  <g id="artwork">\n    <image x="{-w / 2:.3f}" y="{-h / 2:.3f}" width="{w:.3f}" height="{h:.3f}" xlink:href="{png_name}" href="{png_name}"/>\n  </g>\n'
            f'  <g id="cut-line" fill="none" stroke="{CUT_COLOUR}" stroke-width="0.1">\n    {st["cut"]}\n  </g>\n</svg>\n')


def sheet(style, made, path_png, path_pdf):
    """All twelve on one A4 sheet (210 x 297 mm)."""
    W, H = int(round(210 * MM)), int(round(297 * MM))
    page = np.ones((H, W, 3), np.float32)
    # hand-placed centres (mm) so the sheet looks composed rather than packed
    pos = {"01-circle-logo": (37, 37), "02-circle-wordmark": (102, 37), "03-circle-dark-logo": (167, 37),
           "04-rounded-lockup": (52, 97), "10-presents-ticket": (147, 92),
           "05-rounded-name": (57, 145), "12-oval-wordmark": (149.5, 151),
           "06-die-cut-logo": (46, 205), "11-square-logo": (115, 205), "08-logo-dot": (172, 205),
           "09-tagline-pill": (160, 246), "07-wordmark-bar": (67, 276)}
    cuts = []
    for st in made:
        cxm, cym = pos[st["name"]]
        img, a = st["img"], st["alpha"]
        h, w = a.shape
        x0, y0 = int(round(cxm * MM - w / 2)), int(round(cym * MM - h / 2))
        assert x0 >= 0 and y0 >= 0 and x0 + w <= W and y0 + h <= H, f"{st['name']} leaves the sheet"
        reg = page[y0:y0 + h, x0:x0 + w]
        hard = (a >= 0.5).astype(np.float32)[..., None]
        reg[:] = reg * (1 - hard) + img * hard
        cuts.append((st, cxm, cym))
    # PNG preview: artwork + cut lines drawn in magenta
    prev = to_u8(page)
    for st, cxm, cym in cuts:
        col = (255, 0, 255)
        c = (int(round(cxm * MM * 16)), int(round(cym * MM * 16)))
        if st["shape"] == "circle":
            cv2.circle(prev, c, int(round(st["dims"][0] / 2 * MM * 16)), col, 2, cv2.LINE_AA, 4)
        elif st["shape"] == "ellipse":
            cv2.ellipse(prev, (int(cxm * MM), int(cym * MM)), (int(st["dims"][0] / 2 * MM), int(st["dims"][1] / 2 * MM)), 0, 0, 360, col, 2, cv2.LINE_AA)
        elif st["shape"] == "diecut":
            for poly in st["die"]:
                cv2.polylines(prev, [np.round((poly * MM + [cxm * MM, cym * MM]) * 16).astype(np.int32)], True, col, 2, cv2.LINE_AA, 4)
        else:
            d = st["dims"]
            r = (min(d[0], d[1]) / 2 if st["shape"] == "pill" else d[2])
            pts = rrect_points(cxm, cym, d[0], d[1], r) * MM
            cv2.polylines(prev, [np.round(pts * 16).astype(np.int32)], True, col, 2, cv2.LINE_AA, 4)
    save_png(prev, path_png, dpi=DPI, max_err=1.2)
    # PDF: the artwork as one 300 dpi image + every cut line as a true vector path
    c = pdfcanvas.Canvas(str(path_pdf), pagesize=(210 * 72 / 25.4, 297 * 72 / 25.4))
    c.setTitle(f"ASTRIS PRODUCTIONS sticker sheet, {style.name} style (A4, cut lines in magenta)")
    P = 72 / 25.4
    tmp = path_pdf.with_suffix(".tmp.jpg")
    Image.fromarray(to_u8(page)).save(tmp, quality=93, subsampling=0)
    c.drawImage(str(tmp), 0, 0, 210 * P, 297 * P)
    c.setStrokeColorRGB(1, 0, 1)
    c.setLineWidth(0.25)
    for st, cxm, cym in cuts:
        X, Y = cxm * P, (297 - cym) * P
        d = st["dims"]
        if st["shape"] == "circle":
            c.circle(X, Y, d[0] / 2 * P, stroke=1, fill=0)
        elif st["shape"] == "ellipse":
            c.ellipse(X - d[0] / 2 * P, Y - d[1] / 2 * P, X + d[0] / 2 * P, Y + d[1] / 2 * P, stroke=1, fill=0)
        elif st["shape"] == "diecut":
            for poly in st["die"]:
                p = c.beginPath()
                p.moveTo(X + poly[0][0] * P, Y - poly[0][1] * P)
                for q in poly[1:]:
                    p.lineTo(X + q[0] * P, Y - q[1] * P)
                p.close()
                c.drawPath(p, stroke=1, fill=0)
        else:
            r = (min(d[0], d[1]) / 2 if st["shape"] == "pill" else d[2]) * P
            c.roundRect(X - d[0] / 2 * P, Y - d[1] / 2 * P, d[0] * P, d[1] * P, r, stroke=1, fill=0)
    c.showPage()
    c.save()
    tmp.unlink()


def rrect_points(cx, cy, w, h, r, n=10):
    """Outline of a rounded rectangle as a closed polyline (any units)."""
    pts = []
    for (ax, ay, a0) in ((cx + w / 2 - r, cy - h / 2 + r, -90), (cx + w / 2 - r, cy + h / 2 - r, 0), (cx - w / 2 + r, cy + h / 2 - r, 90), (cx - w / 2 + r, cy - h / 2 + r, 180)):
        for i in range(n + 1):
            t = math.radians(a0 + 90 * i / n)
            pts.append((ax + r * math.cos(t), ay + r * math.sin(t)))
    return np.asarray(pts)


def build(style):
    k = style.key
    d = out(k, "merch", "stickers")
    made = []
    for des in designs(style):
        st = make(style, des)
        png = f"astris-{k}-sticker-{st['name']}.png"
        save_png_alpha(st["img"], st["alpha"], d / png, dpi=DPI, hard_palette=True)
        (d / f"astris-{k}-sticker-{st['name']}-with-cut-line.svg").write_text(
            sticker_svg(st, png, f"ASTRIS sticker {st['name']}, {style.name} style: {st['trim_mm'][0]:.0f} x {st['trim_mm'][1]:.0f} mm, {BLEED:g} mm bleed"))
        made.append(st)
    sheet(style, made, d / f"astris-{k}-sticker-sheet-a4-2480x3508.png", d / f"astris-{k}-sticker-sheet-a4.pdf")
    return [f"{len(made)} stickers + A4 sheet"]
