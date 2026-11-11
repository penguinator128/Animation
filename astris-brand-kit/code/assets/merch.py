"""
Merch in a style (stickers have their own step):
  cap        front embroidery artwork (3 flat colours at most) + back and side details
  hoodie     left-chest print + big back print
  t-shirt    two front designs + a small chest logo
  tote       one big print
  bottle     a wrap: print-ready artwork + a template with bleed and safe area
  wallpapers three phone sizes, three designs
  mock-ups   drawn illustrations of each item with the artwork on it (labelled as illustrations: they are not photos)

Every print file is real size: PNG at 300 dpi on transparent, plus SVG and PDF vectors.
Usage: python3 code/build.py merch [--style red] [prints bottle wallpapers mockups readme]
"""
import cv2
import numpy as np

from engine import lockup as L
from engine import type as T
from engine.core import Art, apply_grain, grain_field, hex_rgb, save_jpg, save_png
from engine.paths import STYLE_DIRS, SUB, out
from engine.pdf import Doc
from engine.printart import Print
from engine.style import config

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)
TEE_LINE = {"red": "bring snacks.", "yellow": "stay for the credits.", "wildcard": "films made by hand."}


def ways(style):
    """The two colourways of every item: (A) the style's own colour, (B) its dark partner."""
    h, k = style.hex, style.key
    if k == "red":
        return [dict(item="red", item_hex=h["signature"], main=h["light"], accent=h["light"], shadow=None, strip=None, scheme="main"),
                dict(item="black", item_hex=h["dark"], main=h["light"], accent=h["signature"], shadow=None, strip=h["signature"], scheme="dark")]
    if k == "yellow":
        return [dict(item="yellow", item_hex=h["signature"], main=h["dark"], accent=h["dark"], shadow=None, strip=None, scheme="main"),
                dict(item="black", item_hex=h["dark"], main=h["signature"], accent=h["light"], shadow=None, strip=None, scheme="dark")]
    return [dict(item="cream", item_hex=h["light"], main=h["signature"], accent=h["second"], shadow=h["second"], strip=None, scheme="main"),
            dict(item="blue", item_hex=h["signature"], main=h["light"], accent=h["second"], shadow=h["second"], strip=None, scheme="dark")]


# ====================================================================================================
# the artwork (all sizes in mm)
# ====================================================================================================
def art_icon(style, wy, width, holes=True, flat=False):
    lg = style.logo
    h = width / lg.aspect
    sh = None if flat else wy["shadow"]
    pad = h * 0.03 if sh else 0.0
    p = Print(style, width + pad, h + pad, "ASTRIS logo")
    return p.logo(0, 0, h, wy["main"], strip=wy["strip"], holes=holes, shadow=sh)


def art_stacked(style, wy, width):
    lg, face, b = style.logo, style.display, config()["brand"]
    ih = width / lg.aspect
    s1, s2, track = L.stacked_sizes(face, width)
    cap1, cap2 = face.cap * s1, face.cap * s2
    gap = ih * 0.26
    pad = ih * 0.03 if wy["shadow"] else 0.0
    p = Print(style, width + pad, ih + gap + cap1 * 1.20 + cap2 + pad, "ASTRIS PRODUCTIONS, stacked")
    p.logo(0, 0, ih, wy["main"], strip=wy["strip"], shadow=wy["shadow"])
    p.text(b["first_word"], width / 2, ih + gap + cap1, s1, wy["main"], tracking=0.02, shadow=wy["shadow"])
    p.text(b["second_word"], 0, ih + gap + cap1 * 1.20 + cap2, s2, wy["accent"], tracking=track, anchor="l")
    return p


def art_name(style, wy, width, tagline=True):
    face, name = style.display, config()["brand"]["name_lowercase"]
    size = T.fit_size(name, face, width, L.TRACK_MAIN)
    top = face.cap * size * 1.06
    pad = size * 0.04 if wy["shadow"] else 0.0
    tsize = size * 0.20
    H = top + (size * 0.36 + face.cap * tsize * 1.1 if tagline else face.desc * size * 0.75)
    p = Print(style, width + pad, H + pad, "astris productions.")
    p.text(name, width / 2, top, size, wy["main"], tracking=L.TRACK_MAIN, shadow=wy["shadow"])
    if tagline:
        p.text(style.tagline, width / 2, top + size * 0.36 + face.cap * tsize, tsize, wy["accent"], tracking=L.TRACK_TAG)
    return p


def art_line(style, wy, width, line):
    """A big friendly line, with the logo and name small beneath it."""
    face, lg = style.display, style.logo
    words = line.split()
    lines = [line] if len(line) <= 14 else [" ".join(words[: (len(words) + 1) // 2]), " ".join(words[(len(words) + 1) // 2:])]
    size = min(T.fit_size(l, face, width, L.TRACK_MAIN) for l in lines)
    step = face.cap * size * 1.22
    top = face.cap * size * 1.06
    y = top
    pad = size * 0.04 if wy["shadow"] else 0.0
    y_last = top + step * (len(lines) - 1)
    lh = size * 0.42
    name = config()["brand"]["name_lowercase"]
    ns = size * 0.24
    y_logo = y_last + size * 0.50
    p = Print(style, width + pad, y_logo + lh + pad, line)
    for l in lines:
        p.text(l, width / 2, y, size, wy["main"], tracking=L.TRACK_MAIN, shadow=wy["shadow"])
        y += step
    nw = T.text_width(name, face, ns, L.TRACK_MAIN)
    total = lh * lg.aspect + lh * 0.30 + nw
    x0 = (width - total) / 2
    p.logo(x0, y_logo, lh, wy["accent"] if wy["accent"] != wy["main"] else wy["main"])
    p.text(name, x0 + lh * lg.aspect + lh * 0.30, y_logo + lh / 2 + face.xh * ns / 2, ns, wy["main"], tracking=L.TRACK_MAIN, anchor="l")
    return p


def art_back(style, wy, width):
    """The big back print: logo, name, supporting line."""
    lg, face, name = style.logo, style.display, config()["brand"]["name_lowercase"]
    lw = width * 0.60
    ih = lw / lg.aspect
    size = T.fit_size(name, face, width, L.TRACK_MAIN)
    tsize = size * 0.20
    y_name = ih + ih * 0.22 + face.cap * size * 1.06
    pad = ih * 0.03 if wy["shadow"] else 0.0
    p = Print(style, width + pad, y_name + size * 0.36 + face.cap * tsize * 1.1 + pad, "ASTRIS back print")
    p.logo((width - lw) / 2, 0, ih, wy["main"], strip=wy["strip"], shadow=wy["shadow"])
    p.text(name, width / 2, y_name, size, wy["main"], tracking=L.TRACK_MAIN, shadow=wy["shadow"])
    p.text(style.tagline, width / 2, y_name + size * 0.36 + face.cap * tsize, tsize, wy["accent"], tracking=L.TRACK_TAG)
    return p


def art_word(style, wy, width, s, colour=None):
    face = style.display
    size = T.fit_size(s, face, width, L.TRACK_MAIN)
    p = Print(style, width, face.cap * size * 1.06 + face.desc * size * 0.75, s)
    return p.text(s, width / 2, face.cap * size * 1.06, size, colour or wy["main"], tracking=L.TRACK_MAIN)


def prints(style):
    k = style.key
    n = 0
    name = config()["brand"]["name_lowercase"]
    for wy in ways(style):
        w = f"on-{wy['item']}"
        d = out(k, "merch", "cap")
        n += art_icon(style, wy, 60, flat=True).save(d / f"astris-{k}-cap-front-embroidery-{w}-60mm")
        n += art_icon(style, wy, 60, holes=False, flat=True).save(d / f"astris-{k}-cap-front-embroidery-simplified-{w}-60mm")
        n += art_word(style, wy, 70, name).save(d / f"astris-{k}-cap-back-{w}-70mm")
        n += art_word(style, wy, 45, style.tagline, wy["accent"]).save(d / f"astris-{k}-cap-side-{w}-45mm")
        d = out(k, "merch", "hoodie")
        n += art_icon(style, wy, 85).save(d / f"astris-{k}-hoodie-chest-{w}-85mm")
        n += art_back(style, wy, 300).save(d / f"astris-{k}-hoodie-back-{w}-300mm")
        d = out(k, "merch", "tshirt")
        n += art_name(style, wy, 260).save(d / f"astris-{k}-tshirt-front-name-{w}-260mm")
        n += art_line(style, wy, 240, TEE_LINE[k]).save(d / f"astris-{k}-tshirt-front-line-{w}-240mm")
        n += art_icon(style, wy, 80).save(d / f"astris-{k}-tshirt-chest-logo-{w}-80mm")
        d = out(k, "merch", "tote")
        n += art_stacked(style, wy, 220).save(d / f"astris-{k}-tote-{w}-220mm")
    return n


# ====================================================================================================
# bottle wrap (full colour, with the grain: a wrap is printed all over)
# ====================================================================================================
WRAP_W, WRAP_H, BLEED = 235.0, 160.0, 3.0


def wrap_art(style, wy):
    px = 300 / 25.4
    Wp, Hp = int(round((WRAP_W + 2 * BLEED) * px)), int(round((WRAP_H + 2 * BLEED) * px))
    art = Art(style, Wp, Hp, scheme=wy["scheme"], seed=f"{style.key}-wrap-{wy['item']}", scale=2.0)
    xf, xb = (BLEED + WRAP_W * 0.25) * px, (BLEED + WRAP_W * 0.75) * px
    L.name_line(art, xf, Hp / 2 - 10, 84 * px)
    art.logo(xb, Hp / 2, 62 * px, role="second" if (wy["scheme"] == "dark" and style.key == "red") else "ink")
    return art.render()


def bottle(style):
    k = style.key
    d = out(k, "merch", "bottle")
    arts = {}
    for wy in ways(style):
        img = wrap_art(style, wy)
        arts[wy["item"]] = img
        save_png(img, d / f"astris-{k}-bottle-wrap-{wy['item']}-235x160mm-3mm-bleed-300dpi.png", dpi=300)
    # the template: guides over the artwork
    m = 14.0
    doc = Doc(d / f"astris-{k}-bottle-wrap-template-235x160mm.pdf", WRAP_W + 2 * BLEED + 2 * m, WRAP_H + 2 * BLEED + 2 * m + 26,
              title=f"ASTRIS bottle wrap template ({style.name})")
    first = ways(style)[0]["item"]
    doc.image(arts[first], m, m, WRAP_W + 2 * BLEED, WRAP_H + 2 * BLEED, quality=90, key="wrap")
    tf = f"{style.text_family}-500"
    x0, y0 = m + BLEED, m + BLEED
    doc.rect(m, m, WRAP_W + 2 * BLEED, WRAP_H + 2 * BLEED, stroke="#E5007E", width=0.5)
    doc.rect(x0, y0, WRAP_W, WRAP_H, stroke="#000000", width=0.5)
    doc.rect(x0 + 5, y0 + 5, WRAP_W - 10, WRAP_H - 10, stroke="#000000", width=0.4, dash=([2.5, 2], 0))
    for fx, lab in ((0.25, "FRONT CENTRE"), (0.75, "BACK CENTRE")):
        x = x0 + WRAP_W * fx
        doc.line(x, m - 6, x, m + 3, "#000000", 0.4)
        doc.text(x, m - 8, lab, tf, 6.5, "#000000", anchor="m", tracking=0.12)
    doc.text(x0, m - 8, "SEAM", tf, 6.5, "#000000", anchor="m", tracking=0.12)
    doc.text(x0 + WRAP_W, m - 8, "SEAM", tf, 6.5, "#000000", anchor="m", tracking=0.12)
    yb = m + WRAP_H + 2 * BLEED + 9
    doc.text(m, yb, f"ASTRIS PRODUCTIONS bottle wrap ({style.name})  ·  trim 235 x 160 mm  ·  3 mm bleed  ·  300 dpi", tf, 8, "#000000")
    doc.text(m, yb + 5, "Pink line: bleed (artwork runs to here).  Solid black: trim (the finished wrap).  Dashed: safe area (keep lettering inside).", f"{style.text_family}-400", 7, "#000000")
    doc.text(m, yb + 10, "This is a generic size. Bottles differ: ask your supplier for their template and scale the artwork to fit before ordering.", f"{style.text_family}-400", 7, "#000000")
    doc.save()
    return 3, arts


# ====================================================================================================
# phone wallpapers
# ====================================================================================================
PHONES = [(1290, 2796), (1179, 2556), (1440, 3200)]


def wallpaper(style, design, W, H):
    scheme = "dark" if design == "dark" else "main"
    art = Art(style, W, H, scheme=scheme, seed=f"{style.key}-wall-{design}-{W}")
    if design == "logo":
        art.logo(W / 2, H * 0.60, W * 0.44)
        art.text(style.tagline, W / 2, H * 0.80, W * 0.034, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
    elif design == "name":
        L.name_line(art, W / 2, H * 0.62, W * 0.76)
        art.tag = "main"
    else:
        L.vertical(art, W / 2, H * 0.60, W * 0.40, logo_role="second" if style.key == "red" else None)
    return art.render()


def wallpapers(style):
    k = style.key
    d = out(k, "merch", "phone-wallpapers")
    n = 0
    for W, H in PHONES:
        for design in ("logo", "name", "dark"):
            save_png(wallpaper(style, design, W, H), d / f"astris-{k}-wallpaper-{design}-{W}x{H}.png")
            n += 1
    return n


# ====================================================================================================
# mock-ups: drawn, not photographed
# ====================================================================================================
SS = 2


def qb(p0, c, p1, n=18):
    t = np.linspace(0, 1, n + 1)[1:, None]
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * c + t ** 2 * p1


def cb(p0, c1, c2, p1, n=26):
    t = np.linspace(0, 1, n + 1)[1:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * p1


def path(start, *segs):
    """A polyline from a start point and segments: (x, y) line, (cx, cy, x, y) curve, (c1x, c1y, c2x, c2y, x, y) curve."""
    pts = [np.array(start, float)]
    for s in segs:
        a = np.array(s, float)
        if len(s) == 2:
            pts.append(a)
        elif len(s) == 4:
            pts.extend(qb(pts[-1], a[:2], a[2:]))
        else:
            pts.extend(cb(pts[-1], a[:2], a[2:4], a[4:]))
    return np.array(pts)


def mirror(half):
    left = half[::-1].copy()
    left[:, 0] *= -1
    return np.concatenate([half, left[1:-1]])


def flip(pts):
    q = np.array(pts, float).copy()
    q[:, 0] *= -1
    return q


class Draw:
    """Draws one item into the scene. Local units are roughly millimetres; (0, 0) is the item's top centre."""

    def __init__(self, img, ox, oy, sc):
        self.img, self.ox, self.oy, self.sc = img, ox, oy, sc
        self.h, self.w = img.shape[:2]

    def P(self, pts):
        return np.asarray(pts, float) * self.sc + [self.ox, self.oy]

    def mask(self, polys):
        m = np.zeros((self.h * SS, self.w * SS), np.uint8)
        cv2.fillPoly(m, [np.round(self.P(p) * SS * 16).astype(np.int32) for p in polys], 255, cv2.LINE_AA, 4)
        return cv2.resize(m, (self.w, self.h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0

    def line(self, pts, width, closed=False):
        m = np.zeros((self.h * SS, self.w * SS), np.uint8)
        cv2.polylines(m, [np.round(self.P(pts) * SS * 16).astype(np.int32)], closed, 255, max(1, int(round(width * self.sc * SS))), cv2.LINE_AA, 4)
        return cv2.resize(m, (self.w, self.h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0

    def paint(self, m, colour, alpha=1.0):
        a = (m * alpha)[..., None]
        self.img[:] = self.img * (1 - a) + np.asarray(colour, np.float32) * a

    def fill(self, polys, colour, alpha=1.0):
        m = self.mask(polys)
        self.paint(m, colour, alpha)
        return m

    def stroke(self, pts, colour, width, alpha=1.0, closed=False):
        self.paint(self.line(pts, width, closed), colour, alpha)

    def shadow(self, m, amount=0.24):
        s = self.sc
        sh = cv2.warpAffine(m, np.float32([[1, 0, 9 * s], [0, 1, 15 * s]]), (self.w, self.h))
        sh = cv2.GaussianBlur(sh, (0, 0), 16 * s)
        self.img *= 1 - amount * sh[..., None]

    def form(self, m, colour, folds=()):
        """Soft shading over the finished item: edges turn away, a few folds, a little cloth texture."""
        dark = float(np.asarray(colour) @ LUMA) < 0.16
        dist = cv2.distanceTransform((m > 0.5).astype(np.uint8), cv2.DIST_L2, 3)
        edge = np.clip(1 - dist / (22 * self.sc), 0, 1) ** 2 * m
        f = np.zeros_like(m)
        for pts, width, amt in folds:
            f += cv2.GaussianBlur(self.line(pts, width), (0, 0), width * self.sc * 0.55) * amt
        f *= m
        if dark:
            self.img += (edge * 0.045 + f * 0.55)[..., None]
        else:
            self.img *= 1 - (edge * 0.15 + f)[..., None]
        n = np.random.default_rng(7).standard_normal((self.h, self.w)).astype(np.float32)
        self.img += (cv2.GaussianBlur(n, (0, 0), 0.8) * 0.010 * m)[..., None]

    def art(self, prt, cx, cy, width, alpha=0.97):
        rgb, al = prt.image(width_px=width * self.sc, soft=False)
        hh, ww = al.shape
        x0, y0 = int(round(self.ox + cx * self.sc - ww / 2)), int(round(self.oy + cy * self.sc - hh / 2))
        reg = self.img[y0:y0 + hh, x0:x0 + ww]
        a = (al * alpha)[..., None]
        reg[:] = reg * (1 - a) + rgb * a


def tone(col, k):
    """Lighter (k > 0) or darker (k < 0) version of a colour, for seams and ribs."""
    col = np.asarray(col, np.float32)
    return col + (1 - col) * k if k > 0 else col * (1 + k)


def seam(col):
    return tone(col, 0.16) if float(np.asarray(col) @ LUMA) < 0.16 else tone(col, -0.22)


def draw_tshirt(d, col, prt, pw, py=440):
    half = path((0, 34), (60, 36, 88, 62), (285, 112), (420, 268), (345, 335), (262, 262), (254, 600, 262, 905), (130, 922, 0, 920))
    body = mirror(half)
    back = path((-88, 62), (-60, 36, 0, 34), (60, 36, 88, 62))
    front = path((-88, 62), (-70, 138, 70, 138, 88, 62))
    m = d.mask([body])
    d.shadow(m)
    d.paint(m, col)
    d.fill([np.concatenate([back, front[::-1]])], tone(col, -0.32))
    d.stroke(front, seam(col), 15, 0.55)
    d.stroke(back, seam(col), 11, 0.4)
    for sgn in (1, -1):
        arm = path((285, 112), (246, 180, 262, 262))
        hem = path((414, 258), (340, 324))
        d.stroke(arm * [sgn, 1], seam(col), 2.2, 0.55)
        d.stroke(hem * [sgn, 1], seam(col), 2.0, 0.45)
    d.stroke(path((-258, 892), (-130, 906, 0, 905), (130, 906, 258, 892)), seam(col), 2.0, 0.45)
    d.art(prt, 0, py, pw)
    folds = [(path((178, 330), (205, 520, 160, 760)), 34, 0.07), (path((-178, 330), (-205, 520, -160, 760)), 34, 0.07),
             (path((262, 262), (220, 300, 190, 380)), 26, 0.09), (path((-262, 262), (-220, 300, -190, 380)), 26, 0.09),
             (path((330, 180), (360, 240)), 22, 0.06), (path((-330, 180), (-360, 240)), 22, 0.06)]
    d.form(m, col, folds)


def hoodie_body():
    half = path((0, 62), (70, 64, 105, 100), (290, 150), (400, 430, 455, 760), (392, 790), (330, 560, 290, 360), (282, 880), (275, 935), (0, 938))
    return mirror(half)


def draw_hoodie_front(d, col, prt, pw, cord):
    body = hoodie_body()
    hood = path((-118, 110), (-175, -75, 175, -75, 118, 110))
    m = d.mask([body, hood])
    d.shadow(m)
    d.paint(m, col)
    d.fill([hood], tone(col, -0.10) if float(np.asarray(col) @ LUMA) >= 0.16 else tone(col, 0.05))
    neck = path((-105, 100), (-60, 215, 60, 215, 105, 100))
    inner = np.concatenate([path((-96, 104), (-135, -40, 135, -40, 96, 104)), neck[::-1]])
    d.fill([inner], tone(col, -0.36))
    d.fill([body], col)
    d.fill([np.concatenate([path((-105, 100), (-70, 64, 0, 62), (70, 64, 105, 100)), neck[::-1]])], tone(col, -0.36))
    d.stroke(neck, seam(col), 13, 0.5)
    d.stroke(path((-118, 110), (-175, -75, 175, -75, 118, 110)), seam(col), 3, 0.4)
    for sgn in (1, -1):
        d.stroke(path((290, 150), (262, 250, 290, 360)) * [sgn, 1], seam(col), 2.2, 0.5)
        d.fill([np.array([(455, 760), (392, 790), (372, 742), (438, 712)]) * [sgn, 1]], seam(col), 0.35)
        d.stroke(path((40, 178), (46, 250, 44, 345)) * [sgn, 1], cord, 5.5, 0.95)
        d.stroke(path((44, 345), (44, 362)) * [sgn, 1], tone(cord, -0.3), 7.5, 0.95)
    d.fill([np.array([(-282, 884), (282, 884), (275, 935), (0, 938), (-275, 935)])], seam(col), 0.30)
    pocket = np.array([(-150, 650), (150, 650), (205, 800), (205, 850), (-205, 850), (-205, 800)])
    d.stroke(pocket, seam(col), 2.4, 0.6, closed=True)
    d.art(prt, 128, 325, pw)
    folds = [(path((330, 330), (400, 520, 420, 700)), 30, 0.07), (path((-330, 330), (-400, 520, -420, 700)), 30, 0.07),
             (path((190, 420), (215, 600, 180, 820)), 36, 0.06), (path((-190, 420), (-215, 600, -180, 820)), 36, 0.06)]
    d.form(m, col, folds)


def draw_hoodie_back(d, col, prt, pw):
    body = hoodie_body()
    m = d.mask([body])
    d.shadow(m)
    d.paint(m, col)
    hood = path((-122, 92), (0, 56, 122, 92), (150, 250, 0, 322), (-150, 250, -122, 92))
    d.fill([hood], tone(col, -0.07) if float(np.asarray(col) @ LUMA) >= 0.16 else tone(col, 0.05))
    d.stroke(hood, seam(col), 2.6, 0.55, closed=True)
    d.stroke(path((0, 60), (0, 318)), seam(col), 2.0, 0.4)
    for sgn in (1, -1):
        d.stroke(path((290, 150), (262, 250, 290, 360)) * [sgn, 1], seam(col), 2.2, 0.5)
        d.fill([np.array([(455, 760), (392, 790), (372, 742), (438, 712)]) * [sgn, 1]], seam(col), 0.35)
    d.fill([np.array([(-282, 884), (282, 884), (275, 935), (0, 938), (-275, 935)])], seam(col), 0.30)
    d.art(prt, 0, 600, pw)
    folds = [(path((330, 330), (400, 520, 420, 700)), 30, 0.07), (path((-330, 330), (-400, 520, -420, 700)), 30, 0.07)]
    d.form(m, col, folds)


def draw_cap(d, col, prt, pw, view="front"):
    dark = float(np.asarray(col) @ LUMA) < 0.16
    under = tone(col, 0.07) if dark else tone(col, -0.16)
    if view == "side":
        crown = path((-190, 400), (-196, 170, 60, 120, 190, 300), (216, 350, 205, 400))
        brim = path((-182, 380), (-300, 388, -410, 424), (-424, 436, -408, 446), (-290, 428, -182, 420))
        m = d.mask([crown, brim])
        d.shadow(m, 0.2)
        d.paint(m, col)
        d.fill([brim], under)
        d.stroke(path((-62, 200), (-22, 290, -30, 398)), seam(col), 2.2, 0.45)
        d.stroke(path((72, 224), (112, 310, 110, 398)), seam(col), 2.2, 0.45)
        d.stroke(path((-188, 392), (205, 392)), seam(col), 3.0, 0.35)
        d.fill([path((-58, 197), (-44, 184, -28, 194), (-42, 203, -58, 197))], seam(col), 0.8)
        d.art(prt, 34, 322, pw)
        d.form(m, col, [])
        return
    crown = path((-205, 400), (-218, 140, 218, 140, 205, 400), (0, 432, -205, 400))
    if view == "front":
        # the peak, seen from the front: a shallow crescent under the crown
        brim = path((-216, 396), (0, 372, 216, 396), (130, 448, 0, 448), (-130, 448, -216, 396))
        m = d.mask([crown, brim])
        d.shadow(m, 0.2)
        d.paint(m, col)
        d.fill([brim], under)
        d.stroke(path((-216, 396), (0, 372, 216, 396)), seam(col), 3.0, 0.5)
        d.stroke(path((-150, 420), (0, 436, 150, 420)), seam(col), 1.8, 0.35)
        for x in (-118, 118):
            d.stroke(path((x * 0.16, 208), (x * 0.9, 250, x, 378)), seam(col), 2.0, 0.4)
    else:
        m = d.mask([crown])
        d.shadow(m, 0.2)
        d.paint(m, col)
        hole = path((-72, 412), (-72, 300, 72, 300, 72, 412))
        d.fill([hole], d.back, 1.0)
        d.stroke(hole, seam(col), 3.0, 0.6)
        d.fill([np.array([(-74, 380), (74, 380), (74, 404), (-74, 404)])], under)
        d.fill([np.array([(-12, 376), (12, 376), (12, 408), (-12, 408)])], seam(col), 0.9)
        for x in (-118, 118):
            d.stroke(path((x * 0.16, 208), (x * 0.9, 250, x, 396)), seam(col), 2.0, 0.4)
    d.stroke(path((0, 208), (0, 372 if view == "front" else 300)), seam(col), 2.0, 0.35)
    d.fill([path((-15, 207), (0, 195, 15, 207), (0, 216, -15, 207))], seam(col), 0.8)
    d.art(prt, 0, 312 if view == "front" else 258, pw)
    d.form(m, col, [])


def draw_tote(d, col, prt, pw):
    body = path((-190, 330), (190, 330), (196, 880), (196, 900, 176, 900), (-176, 900), (-196, 900, -196, 880))
    back_h = path((-112, 334), (-112, 80, 112, 80, 112, 334))
    front_h = path((-92, 345), (-92, 40, 92, 40, 92, 345))
    mh = d.line(back_h, 24) + d.line(front_h, 24)
    m = np.clip(d.mask([body]) + mh, 0, 1)
    d.shadow(m)
    d.stroke(back_h, tone(col, -0.16) if float(np.asarray(col) @ LUMA) >= 0.16 else tone(col, 0.05), 24)
    d.fill([body], col)
    d.stroke(front_h, col, 24)
    for x in (-92, 92):
        d.stroke(path((x - 12, 345), (x + 12, 345)), seam(col), 2.0, 0.5)
        d.stroke(np.array([(x - 11, 332), (x + 11, 332), (x + 11, 372), (x - 11, 372)]), seam(col), 1.6, 0.4, closed=True)
    d.stroke(path((-190, 352), (190, 352)), seam(col), 1.8, 0.4)
    d.art(prt, 0, 630, pw)
    d.form(m, col, [(path((-120, 420), (-140, 600, -110, 860)), 30, 0.05), (path((130, 400), (150, 640, 120, 870)), 30, 0.05)])


def draw_bottle(d, wrap, steel, cap_col):
    R, y0, y1 = 105.0, 330.0, 900.0
    body = path((0, 210), (38, 210), (38, 250, 105, 268, 105, 340), (105, 880), (105, 900, 85, 900), (0, 900))
    body = mirror(body)
    cap_ = np.array([(-46, 132), (46, 132), (46, 214), (-46, 214)])
    loop = path((-30, 134), (-30, 84, 30, 84, 30, 134))
    m = np.clip(d.mask([body, cap_]) + d.line(loop, 11), 0, 1)
    d.shadow(m)
    d.fill([body], steel)
    d.stroke(loop, cap_col, 11)
    d.fill([cap_], cap_col)
    for y in (150, 168, 186):
        d.stroke(path((-46, y), (46, y)), tone(cap_col, 0.14), 2.0, 0.5)
    # the wrap, as if round a cylinder: we see the middle half of it
    px = 300 / 25.4
    art = wrap[int(BLEED * px):-int(BLEED * px), int(BLEED * px):-int(BLEED * px)]
    ah, aw = art.shape[:2]
    wy0, wy1 = 372.0, 372.0 + WRAP_H * 3.0
    X0, X1 = int(round(d.ox - R * d.sc)), int(round(d.ox + R * d.sc))
    Y0, Y1 = int(round(d.oy + wy0 * d.sc)), int(round(d.oy + wy1 * d.sc))
    xs = (np.arange(X0, X1) + 0.5 - d.ox) / (R * d.sc)
    th = np.arcsin(np.clip(xs, -0.999, 0.999))
    r_mm = WRAP_W / (2 * np.pi)
    u = (WRAP_W * 0.25 + th * r_mm) / WRAP_W * aw
    v = (np.arange(Y0, Y1) + 0.5 - Y0) / (Y1 - Y0) * ah
    mapx, mapy = np.meshgrid(u.astype(np.float32), v.astype(np.float32))
    small = cv2.resize(art, (aw // 2, ah // 2), interpolation=cv2.INTER_AREA)
    warped = cv2.remap(small, mapx / 2, mapy / 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    d.img[Y0:Y1, X0:X1] = warped
    # roundness: darker toward the sides, one soft highlight
    xx = (np.arange(d.w) + 0.5 - d.ox) / (R * d.sc)
    cyl = np.clip(1 - xx ** 2, 0, 1) ** 0.5
    shade = (0.60 + 0.40 * cyl ** 0.7) + 0.10 * np.exp(-((xx + 0.42) / 0.16) ** 2)
    bm = d.mask([body])
    d.img[:] = d.img * (1 - bm[..., None]) + d.img * shade[None, :, None] * bm[..., None]
    cm = d.mask([cap_])
    cx = (np.arange(d.w) + 0.5 - d.ox) / (46 * d.sc)
    cshade = 0.70 + 0.30 * np.clip(1 - cx ** 2, 0, 1) ** 0.5
    d.img[:] = d.img * (1 - cm[..., None]) + d.img * cshade[None, :, None] * cm[..., None]


def scene(style, title, W=3000, H=2000):
    art = Art(style, W, H, scheme="light", seed=f"{style.key}-mock-{title}", grain=False)
    tf = style.text_face(500)
    art.text(title.upper(), 90, 110, 34, face=tf, tracking=0.30, anchor="lm", shadow=False, wear=0)
    art.text("ILLUSTRATION  ·  NOT A PRODUCT PHOTO", 90, H - 100, 28, face=tf, tracking=0.24, anchor="lm", shadow=False, wear=0)
    art.text(config()["brand"]["name_lowercase"], W - 90, H - 100, 58, tracking=L.TRACK_MAIN, anchor="rm", shadow=False)
    return art.render(grain=False).copy()


def finish(style, img, path_):
    g = grain_field(img.shape[0], img.shape[1], str(path_.name), style.grain_sigma * 2.0)
    img = np.clip(apply_grain(img, g, style.grain_amount * 0.8, style.grain_lift), 0, 1)
    save_jpg(img, path_, 90)
    return path_


def item_col(wy):
    c = hex_rgb(wy["item_hex"])
    return c * 0.93 if wy["item"] == "cream" else c            # natural cotton is a shade deeper than the paper behind it


def mockups(style, wraps=None):
    k = style.key
    d_ = out(k, "merch", "mock-ups")
    A, B = ways(style)
    cA, cB = item_col(A), item_col(B)
    light = hex_rgb(style.hex["light"])
    made = 0
    # ---- t-shirts
    img = scene(style, "t-shirt")
    draw_tshirt(Draw(img, 780, 300, 1.52), cA, art_name(style, A, 260), 260)
    draw_tshirt(Draw(img, 2220, 300, 1.52), cB, art_line(style, B, 240, TEE_LINE[k]), 240)
    finish(style, img, d_ / f"astris-{k}-mockup-tshirt-illustration.jpg")
    # ---- hoodies: front and back, one image per colourway
    for wy, col in ((A, cA), (B, cB)):
        img = scene(style, f"hoodie, {wy['item']}")
        draw_hoodie_front(Draw(img, 780, 330, 1.50), col, art_icon(style, wy, 85), 85, hex_rgb(wy["main"]))
        draw_hoodie_back(Draw(img, 2220, 330, 1.50), col, art_back(style, wy, 300), 300)
        finish(style, img, d_ / f"astris-{k}-mockup-hoodie-{wy['item']}-illustration.jpg")
        made += 1
    # ---- caps: front in both colours, back and side
    img = scene(style, "cap")
    name = config()["brand"]["name_lowercase"]
    for (ox, oy, wy, col, view) in ((800, 60, A, cA, "front"), (2200, 60, B, cB, "front"), (800, 960, A, cA, "back"), (2260, 960, B, cB, "side")):
        d = Draw(img, ox, oy, 2.15)
        d.back = light
        prt = {"front": art_icon(style, wy, 60, flat=True), "back": art_word(style, wy, 70, name), "side": art_word(style, wy, 45, style.tagline, wy["accent"])}[view]
        draw_cap(d, col, prt, {"front": 150, "back": 150, "side": 100}[view], view)
    finish(style, img, d_ / f"astris-{k}-mockup-cap-illustration.jpg")
    # ---- totes
    img = scene(style, "tote bag")
    tote_ways = [dict(A, item="natural", item_hex=style.hex["light"]) if k != "wildcard" else A, B]
    if k == "red":
        tote_ways[0].update(main=style.hex["signature"], accent=style.hex["dark"], strip=None)
    if k == "yellow":
        tote_ways[0].update(main=style.hex["dark"], accent=style.hex["dark"])
    for ox, wy in ((780, tote_ways[0]), (2220, tote_ways[1])):
        col = hex_rgb(wy["item_hex"]) * (0.93 if wy["item"] in ("natural", "cream") else 1.0)
        draw_tote(Draw(img, ox, 150, 1.85), col, art_stacked(style, wy, 220), 220)
    finish(style, img, d_ / f"astris-{k}-mockup-tote-illustration.jpg")
    # ---- bottles
    if wraps:
        img = scene(style, "drink bottle")
        steel = np.array([0.80, 0.80, 0.79], np.float32)
        for ox, wy in ((1020, A), (1980, B)):
            draw_bottle(Draw(img, ox, 60, 1.95), wraps[wy["item"]], steel, hex_rgb(style.hex["dark"]))
        finish(style, img, d_ / f"astris-{k}-mockup-bottle-illustration.jpg")
        made += 1
    return made + 3


# ====================================================================================================
def readme(style):
    k = style.key
    A, B = ways(style)
    cols = "\n".join(f"| {n} | `{hx}` |" for n, hx in [(style.colour_names[c], style.hex[c]) for c in style.hex])
    (STYLE_DIRS[k] / SUB["merch"] / "README.md").write_text(f"""# Merch ({style.name})

Every print file here is **real size**. A file called `...-260mm` prints 260 mm wide at 100 %.
Each design comes three ways: `.png` (transparent, 300 dpi), `.svg` and `.pdf` (clean vectors that scale to any size).
Each design also comes in two colourways: **on {A['item']}** and **on {B['item']}** items.

| Folder | What is in it |
|---|---|
| `stickers/` | Twelve stickers in different shapes, each with a vector cut line, and an A4 sheet of all of them. |
| `cap/` | Front embroidery (60 mm, flat colours only), a simplified front for small stitching, back wordmark (70 mm), side detail (45 mm). |
| `hoodie/` | Left-chest logo (85 mm) and big back print (300 mm). |
| `tshirt/` | Two front designs (the name at 260 mm, a friendly line at 240 mm) and a small chest logo (80 mm). |
| `tote/` | One big print (220 mm). |
| `bottle/` | A drink-bottle wrap: print-ready artwork in two colours (235 x 160 mm + 3 mm bleed, 300 dpi) and a template PDF with bleed, trim and safe-area guides. |
| `phone-wallpapers/` | Three designs in three sizes: 1290 x 2796, 1179 x 2556 and 1440 x 3200. The top third is left clear for the clock. |
| `mock-ups/` | Drawn previews of each item. |

## A few honest notes

- **The mock-ups are illustrations.** They are drawn by code to show placement and colour. They are not photos of real products, and each one says so in the corner.
- **Embroidery:** the cap files are flat-colour artwork for an embroiderer to digitise. They are not stitch files (`.dst`, `.pes`): your embroiderer makes those from the SVG or PDF. Each uses three colours or fewer.
- **The simplified cap logo** leaves out the small sprocket holes of the film strip. At 60 mm wide those holes are under 2 mm, which is too fine for most stitching. It is a production version for small embroidery only: everywhere else the full logo is used. Ask your embroiderer which they prefer.
- **The bottle wrap is a generic size.** Bottles differ, so ask your supplier for their template and scale the artwork to fit before ordering.
- **Colours on fabric shift.** Give your printer the values below and ask for a proof.

## Colours

| Name | HEX |
|---|---|
{cols}

On {A['item']} items the print is {('one colour: ' + A['main']) if A['main'] == A['accent'] or not A['accent'] else ('two colours: ' + A['main'] + ' and ' + A['accent'])}.
On {B['item']} items the print is {('one colour: ' + B['main']) if B['main'] == B['accent'] else ('two colours: ' + B['main'] + ' and ' + B['accent'])}.

## Print methods that suit these files

- **Screen print:** use the SVG or PDF. Each colour is a separate flat shape.
- **DTG / DTF (direct to garment / film):** use the PNG at 100 %.
- **Embroidery:** use the SVG or PDF for digitising.
- **Stickers:** send the SVG (artwork + cut line) or the A4 sheet PDF.
""")
    return 1


PIECES = ["prints", "bottle", "wallpapers", "mockups", "readme"]


def build(style, *which):
    which = [w for w in which if w in PIECES] or PIECES
    n = 0
    wraps = None
    if "prints" in which:
        n += prints(style)
    if "bottle" in which or "mockups" in which:
        nb, wraps = bottle(style)
        n += nb
    if "wallpapers" in which:
        n += wallpapers(style)
    if "mockups" in which:
        n += mockups(style, wraps)
    if "readme" in which:
        n += readme(style)
    return [f"{n} merch files"]
