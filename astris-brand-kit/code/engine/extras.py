"""Small drawing helpers shared by the templates: placeholder boxes and the highlight-cover icons."""
import math

import cv2
import numpy as np

from . import type as T


def dashed_box(h, w, radius, stroke, dash, gap, ss=3):
    """Mask of a dashed rounded-rectangle outline (h x w)."""
    H, W = h * ss, w * ss
    im = np.zeros((H, W), np.uint8)
    r = int(radius * ss)
    st = max(1, int(stroke * ss))
    pts = []
    m = st // 2 + 1
    x0, y0, x1, y1 = m, m, W - m - 1, H - m - 1
    n = 14

    def arc(cx, cy, a0, a1):
        return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    pts += arc(x1 - r, y0 + r, -math.pi / 2, 0) + arc(x1 - r, y1 - r, 0, math.pi / 2) + arc(x0 + r, y1 - r, math.pi / 2, math.pi) + arc(x0 + r, y0 + r, math.pi, 1.5 * math.pi)
    pts.append(pts[0])
    # walk the outline, drawing dashes
    d, g = dash * ss, gap * ss
    pos, draw = 0.0, True
    seg_left = d
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, by - ay)
        t = 0.0
        while t < L:
            step = min(seg_left, L - t)
            if draw:
                p0 = (int(ax + (bx - ax) * t / L), int(ay + (by - ay) * t / L))
                p1 = (int(ax + (bx - ax) * (t + step) / L), int(ay + (by - ay) * (t + step) / L))
                cv2.line(im, p0, p1, 255, st, cv2.LINE_AA)
            t += step
            seg_left -= step
            if seg_left <= 1e-6:
                draw = not draw
                seg_left = d if draw else g
    return cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def placeholder(art, x0, y0, x1, y1, label, role="ink", radius=None, text_size=None, alpha=1.0, face=None, fill=0.0):
    """A clearly marked slot: dashed outline + a [LABEL] in the middle."""
    w, h = int(x1 - x0), int(y1 - y0)
    s = art.s
    radius = radius if radius is not None else 18 * s
    art.add(dashed_box(h, w, radius, 3.2 * s, 22 * s, 14 * s), x0, y0, role=role, size=120 * s, alpha=alpha, shadow=False, wear=0)
    if fill:
        from .core import rounded_mask
        art.add(rounded_mask(h, w, radius), x0, y0, role=role, size=300 * s, alpha=fill, shadow=False, wear=0)
    if label:
        face = face or art.style.text_face(500)
        size = text_size or min(30 * s, h * 0.28)
        lines = label.split("\n")
        # shrink to fit the width
        widest = max(T.text_width(l, face, size, 0.06) for l in lines)
        if widest > w * 0.86:
            size *= w * 0.86 / widest
        lh = size * 1.45
        cy = (y0 + y1) / 2 - lh * (len(lines) - 1) / 2
        for i, l in enumerate(lines):
            art.text(l, (x0 + x1) / 2, cy + i * lh, size, face=face, tracking=0.06, anchor="mm", role=role, shadow=False, alpha=alpha, wear=0)


# ----------------------------------------------------------------------------------------------------
# icons: chunky, flat, built from a few shapes on a 100 x 100 grid. '+' adds ink, '-' cuts it away.
# ----------------------------------------------------------------------------------------------------
def _rr(x, y, w, h, r=0):
    return ("rr", x, y, w, h, r)


def _c(cx, cy, r):
    return ("c", cx, cy, r)


def _p(*pts):
    return ("p", pts)


def _sprockets(y, n=6, x0=13, x1=87, size=6.5):
    step = (x1 - x0 - size) / (n - 1)
    return [("-", _rr(x0 + i * step, y, size, size, 1)) for i in range(n)]


ICONS = {
    "Films": [("+", _rr(6, 22, 88, 56, 5))] + _sprockets(27) + _sprockets(66.5) + [("-", _rr(20, 39, 60, 22, 2)), ("+", _p((44, 43.5), (44, 56.5), (57, 50)))],
    "Behind the Scenes": [("+", _rr(12, 42, 76, 44, 5)), ("+", _p((10, 30), (84, 12), (87, 24), (13, 42))),
                          ("-", _p((26, 26.2), (36, 23.8), (33, 37.2), (23, 39.6))), ("-", _p((46, 21.3), (56, 18.9), (53, 32.3), (43, 34.7))),
                          ("-", _p((66, 16.4), (76, 14), (73, 27.4), (63, 29.8))), ("-", _rr(22, 54, 56, 5, 1)), ("-", _rr(22, 66, 36, 5, 1))],
    "Gear": [("+", _rr(8, 36, 60, 42, 6)), ("+", _p((68, 49), (92, 38), (92, 76), (68, 65))), ("+", _c(26, 23, 12)), ("+", _c(52, 23, 12)),
             ("-", _c(26, 23, 4)), ("-", _c(52, 23, 4)), ("-", _c(38, 57, 10))],
    "Edits": [("+", _rr(8, 22, 54, 13, 3)), ("+", _rr(30, 43.5, 62, 13, 3)), ("+", _rr(8, 65, 40, 13, 3)), ("+", _p((60, 10), (67, 10), (49, 90), (42, 90))),
              ("-", _p((67.5, 10), (70.5, 10), (52.5, 90), (49.5, 90))), ("-", _p((38.5, 10), (41.5, 10), (41.5, 10), (59.5, 10), (41.5, 90), (38.5, 90)))][:4],
    "Posters": [("+", _rr(22, 8, 56, 84, 4)), ("-", _c(50, 36, 14)), ("-", _rr(32, 60, 36, 6, 1)), ("-", _rr(38, 72, 24, 5, 1))],
    "Intros": [("+", _c(50, 50, 43)), ("-", _p((40, 30), (40, 70), (72, 50)))],
    "News": [("+", _p((12, 40), (58, 18), (58, 82), (12, 60))), ("+", _rr(58, 24, 9, 52, 3)), ("+", _rr(22, 60, 12, 26, 4)),
             ("+", _p((74, 32), (90, 24), (92, 29), (76, 37))), ("+", _rr(76, 47, 17, 6, 2)), ("+", _p((76, 63), (92, 71), (90, 76), (74, 68)))],
    "Q&A": [("+", _rr(10, 12, 80, 56, 13)), ("+", _p((28, 64), (48, 64), (24, 88))), ("text", "?", 50, 40, 46)],
    "Crew": [("+", _c(50, 32, 15)), ("+", _rr(26, 52, 48, 36, 16)), ("+", _c(20, 42, 10)), ("+", _rr(4, 57, 30, 30, 11)), ("+", _c(80, 42, 10)), ("+", _rr(66, 57, 30, 30, 11)),
             ("-", _rr(22.5, 50, 3.5, 40, 0)), ("-", _rr(74, 50, 3.5, 40, 0))],
    "Shorts": [("+", _p((58, 5), (20, 55), (45, 55), (36, 95), (80, 40), (54, 40)))],
    "Showreel": [("+", _c(50, 50, 43)), ("-", _c(50, 50, 7))] + [("-", _c(50 + 25 * math.cos(a), 50 + 25 * math.sin(a), 9.5)) for a in [math.pi * (0.5 + 0.4 * k) for k in range(5)]],
    "Contact": [("+", _rr(8, 22, 84, 56, 6)), ("-", _p((8, 26), (12, 22), (50, 52), (88, 22), (92, 26), (50, 60)))],
}


def icon_mask(name, px, face=None):
    """px x px coverage mask of an icon."""
    ss = 4
    n = px * ss
    k = n / 100.0
    im = np.zeros((n, n), np.uint8)
    for op in ICONS[name]:
        if op[0] == "text":
            _, string, cx, cy, size = op
            m, (ox, oy) = T.text_mask(string, face, size * k, 0.0, ss=1)
            w = T.text_width(string, face, size * k)
            x0, y0 = int(cx * k - w / 2 + ox), int(cy * k + face.cap * size * k / 2 + oy)
            hh, ww = m.shape
            sub = im[max(0, y0):y0 + hh, max(0, x0):x0 + ww]
            mm = m[max(0, -y0):max(0, -y0) + sub.shape[0], max(0, -x0):max(0, -x0) + sub.shape[1]]
            sub[:] = np.clip(sub.astype(np.float32) * (1 - mm), 0, 255).astype(np.uint8)
            continue
        val = 255 if op[0] == "+" else 0
        shp = op[1]
        if shp[0] == "rr":
            _, x, y, w, h, r = shp
            x0, y0, x1, y1, rr = int(x * k), int(y * k), int((x + w) * k), int((y + h) * k), int(r * k)
            if rr > 0:
                cv2.rectangle(im, (x0 + rr, y0), (x1 - rr, y1), val, -1)
                cv2.rectangle(im, (x0, y0 + rr), (x1, y1 - rr), val, -1)
                for cx, cy in ((x0 + rr, y0 + rr), (x1 - rr, y0 + rr), (x0 + rr, y1 - rr), (x1 - rr, y1 - rr)):
                    cv2.circle(im, (cx, cy), rr, val, -1, cv2.LINE_AA)
            else:
                cv2.rectangle(im, (x0, y0), (x1, y1), val, -1)
        elif shp[0] == "c":
            _, cx, cy, r = shp
            cv2.circle(im, (int(cx * k), int(cy * k)), int(r * k), val, -1, cv2.LINE_AA)
        else:
            cv2.fillPoly(im, [np.round(np.asarray(shp[1]) * k).astype(np.int32)], val, cv2.LINE_AA)
    return cv2.resize(im, (px, px), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
