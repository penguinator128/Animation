"""
Sub-pixel measurement of the logo artwork: shapes, edges (fitted lines), corners and sprocket holes.
Used by analyse_logo.py (the report) and build_logo_pack.py (the two cleaned vectors).
"""
import math

import cv2
import numpy as np

UP = 4          # the scan is upsampled 4x (bicubic) before tracing, so contours land on a 0.25 px grid


def load_grey(path):
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(path)
    if img.ndim == 3:
        if img.shape[2] == 4:                       # transparent logo: composite on black, use alpha x luminance
            a = img[..., 3:4].astype(np.float32) / 255
            img = (img[..., :3].astype(np.float32) * a).astype(np.uint8)
        img = cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2GRAY)
    return img.astype(np.float32)


def fit_line(pts):
    """Total-least-squares line through pts -> (point on line, unit direction, rms residual, max residual)."""
    c = pts.mean(0)
    u, s, vt = np.linalg.svd(pts - c, full_matrices=False)
    d = vt[0]
    n = np.array([-d[1], d[0]])
    res = (pts - c) @ n
    return c, d, float(np.sqrt((res ** 2).mean())), float(np.abs(res).max())


def intersect(p1, d1, p2, d2):
    A = np.array([d1, -d2]).T
    t = np.linalg.solve(A, p2 - p1)
    return p1 + d1 * t[0]


def angle_deg(d):
    """Direction as an angle from the vertical, in degrees, signed (+ leans right going down), folded to +-90."""
    dx, dy = d
    if dy < 0:
        dx, dy = -dx, -dy
    return math.degrees(math.atan2(dx, dy))


def trace(grey, level):
    """Contours (outer + holes) of grey > level, in original pixel coordinates with 1/UP px resolution.
    Returns list of dicts {pts (N,2), parent (index or -1), area}."""
    h, w = grey.shape
    big = cv2.resize(grey, (w * UP, h * UP), interpolation=cv2.INTER_CUBIC)
    bw = (big > level).astype(np.uint8)
    cs, hier = cv2.findContours(bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    for c, hh in zip(cs, hier[0]):
        pts = (c.reshape(-1, 2).astype(np.float64) + 0.5) / UP - 0.5        # pixel-centre convention
        out.append({"pts": pts, "parent": int(hh[3]), "area": cv2.contourArea(c) / UP ** 2})
    return out


def polygon(pts, eps=1.6, trim=0.14, min_trim=2.5):
    """Find the corners of a traced contour and fit a straight line to every edge.
    Returns dict: vertices (ideal corners = intersections of fitted lines), edges [{p, d, rms, max, len, n}],
    rounding [distance from each ideal corner to the traced outline]."""
    cnt = np.round((pts + 0.5) * UP).astype(np.int32).reshape(-1, 1, 2)
    ap = cv2.approxPolyDP(cnt, eps * UP, True).reshape(-1, 2)
    # indices of the approx vertices in the contour
    P = np.round((pts + 0.5) * UP).astype(np.int32)
    idx = []
    for v in ap:
        k = np.where((P[:, 0] == v[0]) & (P[:, 1] == v[1]))[0]
        idx.append(int(k[0]))
    order = np.argsort(idx)
    idx = [idx[k] for k in order]
    n = len(pts)
    edges = []
    for a, b in zip(idx, idx[1:] + [idx[0] + n]):
        seg = pts[np.arange(a, b + 1) % n]
        L = float(np.linalg.norm(seg[-1] - seg[0]))
        cut = max(min_trim, trim * L)
        dist = np.linalg.norm(seg - seg[0], axis=1)
        keep = seg[(dist > cut) & (dist < L - cut)]
        if len(keep) >= 8:
            p, d, rms, mx = fit_line(keep)
        else:
            p, d, rms, mx = seg.mean(0), (seg[-1] - seg[0]) / max(L, 1e-9), 0.0, 0.0
        if np.dot(d, seg[-1] - seg[0]) < 0:
            d = -d
        edges.append({"p": p, "d": d, "rms": rms, "max": mx, "len": L, "n": len(keep), "a": seg[0], "b": seg[-1]})
    verts = []
    for k in range(len(edges)):
        e0, e1 = edges[k - 1], edges[k]
        cross = abs(e0["d"][0] * e1["d"][1] - e0["d"][1] * e1["d"][0])
        verts.append(intersect(e0["p"], e0["d"], e1["p"], e1["d"]) if cross > 1e-3 else e1["a"])
    verts = np.array(verts)
    rounding = [float(np.min(np.linalg.norm(pts - v, axis=1))) for v in verts]
    for k, e in enumerate(edges):
        e["v0"], e["v1"] = verts[k], verts[(k + 1) % len(edges)]
        e["len"] = float(np.linalg.norm(e["v1"] - e["v0"]))
        e["angle"] = angle_deg(e["d"])
    return {"vertices": verts, "edges": edges, "rounding": rounding}


def measure(path):
    grey = load_grey(path)
    # plateau levels of the two parts, measured away from edges
    bw = (grey > 0.45 * grey.max()).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(bw, connectivity=8)
    parts = []
    for i in range(1, n):
        if stats[i][4] < 2000:
            continue
        core = cv2.erode((lab == i).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
        parts.append({"label": i, "level": float(grey[core].mean()), "level_std": float(grey[core].std()),
                      "area_px": int(stats[i][4]), "bbox": [int(v) for v in stats[i][:4]]})
    specks = [{"area": int(stats[i][4]), "at": [float(v) for v in cent[i]]} for i in range(1, n) if stats[i][4] < 2000]
    shapes = []
    for part in parts:
        m = (lab == part["label"]).astype(np.uint8)
        region = cv2.dilate(m, np.ones((7, 7), np.uint8)).astype(bool)
        g = np.where(region, grey, 0)
        for c in trace(g, part["level"] / 2):
            if c["area"] < 40:
                continue
            poly = polygon(c["pts"])
            shapes.append({"part": part["label"], "is_hole": c["parent"] >= 0, "area": c["area"], "pts": c["pts"], **poly})
    return {"grey": grey, "parts": parts, "specks": specks, "shapes": shapes}
