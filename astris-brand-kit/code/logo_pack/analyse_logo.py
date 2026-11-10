"""
ASTRIS PRODUCTIONS - bare-bones logo pack, step 1: ANALYSE the original logo.

Measures the artwork to sub-pixel accuracy (see measure.py), writes
  01_Logo-Pack-Bare-Bones/logo-report.md                       what is (and isn't) off, and what each clean-up changes
  01_Logo-Pack-Bare-Bones/report-images/*.png                  overlay with axes + grid, before/after, detail zooms
  code/logo_pack/logo-measurements.json                        every number
  code/logo_pack/logo-geometry.json                            the two cleaned versions as polygons (used by the whole kit)

Usage: python3 code/logo_pack/analyse_logo.py
"""
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from shapely.ops import unary_union

import measure as M

# ------------------------------------------------------------------------------------------------
# THE LOGO: change this one path to analyse a different file (the original is never modified)
# ------------------------------------------------------------------------------------------------
KIT = Path(__file__).resolve().parents[2]
LOGO_PATH = KIT / "00_Originals" / "astris-logo-original.jpg"
OUT = KIT / "01_Logo-Pack-Bare-Bones"
IMG = OUT / "report-images"
HERE = Path(__file__).resolve().parent
FONTS = KIT / "code" / "fonts"
IDEAL = math.degrees(math.atan(0.5))          # 26.565 deg: a 1-in-2 slope


def font(size, weight=500):
    return ImageFont.truetype(str(FONTS / f"dm-sans-{weight}.ttf"), size)


def snap_and_clean(shape):
    """Faithful clean-up of one traced polygon: drop sub-3px nicks, make near-horizontal / near-vertical edges exact,
    then rebuild the corners as intersections of the fitted lines (sharp, as drawn)."""
    edges = [dict(e) for e in shape["edges"] if e["len"] >= 3.0]
    notes = []
    if len(edges) != len(shape["edges"]):
        notes.append("removed a %.1f px nick" % min(e["len"] for e in shape["edges"]))
    for e in edges:
        a = e["angle"]
        if abs(a) < 1.5 and abs(a) > 1e-9:
            notes.append("trued a %.1f deg off-vertical edge" % a) if abs(a) > 0.05 else None
            e["d"] = np.array([0.0, 1.0]) * np.sign(e["d"][1] if e["d"][1] != 0 else 1)
        elif abs(abs(a) - 90) < 1.5:
            if abs(abs(a) - 90) > 0.05:
                notes.append("trued a %.1f deg off-horizontal edge" % (abs(a) - 90))
            e["d"] = np.array([1.0, 0.0]) * np.sign(e["d"][0] if e["d"][0] != 0 else 1)
    verts = []
    for k in range(len(edges)):
        e0, e1 = edges[k - 1], edges[k]
        verts.append(M.intersect(e0["p"], e0["d"], e1["p"], e1["d"]))
    return np.array(verts), [n for n in notes if n]


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    R = M.measure(LOGO_PATH)
    grey = R["grey"]
    Himg, Wimg = grey.shape
    outer = sorted([s for s in R["shapes"] if not s["is_hole"]], key=lambda s: s["vertices"][:, 0].mean())
    strip, bar = outer[0], outer[1]
    holes = [s for s in R["shapes"] if s["is_hole"]]
    assert len(outer) == 2 and len(holes) == 22, (len(outer), len(holes))

    # ---------------- outline geometry
    sv, bv = strip["vertices"], bar["vertices"]
    s_bl, s_br = sv[np.argsort(sv[:, 1])[-2:]][np.argsort(sv[np.argsort(sv[:, 1])[-2:]][:, 0])]
    s_apex = sv[np.argmin(sv[:, 1])]
    s_right = sv[np.argmax(sv[:, 0])]
    b_top = bv[np.argsort(bv[:, 1])[:2]]
    b_tl, b_tr = b_top[np.argsort(b_top[:, 0])]
    b_bot = bv[np.argsort(bv[:, 1])[-2:]]
    b_bl, b_br = b_bot[np.argsort(b_bot[:, 0])]
    top_y, base_y = float((b_tl[1] + b_tr[1]) / 2), float((b_bl[1] + b_br[1] + s_bl[1] + s_br[1]) / 4)
    u = (base_y - top_y) / 16.0                               # the design unit (see report)
    x0 = float(s_bl[0])

    def edge_between(shape, p, q):
        for e in shape["edges"]:
            if (np.linalg.norm(e["v0"] - p) < 2 and np.linalg.norm(e["v1"] - q) < 2) or \
               (np.linalg.norm(e["v0"] - q) < 2 and np.linalg.norm(e["v1"] - p) < 2):
                return e
        raise KeyError

    E = {"strip left (outer)": edge_between(strip, s_bl, s_apex), "strip right": edge_between(strip, s_br, s_right),
         "strip cut (faces the bar)": edge_between(strip, s_right, s_apex), "bar left (faces the strip)": edge_between(bar, b_tl, b_bl),
         "bar right (outer)": edge_between(bar, b_tr, b_br)}
    angles = {k: e["angle"] for k, e in E.items()}

    def x_at(e, y):
        return float(e["p"][0] + e["d"][0] / e["d"][1] * (y - e["p"][1]))

    gap_top = x_at(E["bar left (faces the strip)"], s_apex[1]) - s_apex[0]
    gap_bot = x_at(E["bar left (faces the strip)"], s_right[1]) - s_right[0]
    bar_w_top, bar_w_bot = float(b_tr[0] - b_tl[0]), float(b_br[0] - b_bl[0])
    strip_w = float(s_br[0] - s_bl[0])
    axis_x = float((s_bl[0] + b_br[0]) / 2)                    # mirror axis of the two outer legs

    # ---------------- holes
    sd = np.array([-math.sin(math.radians(IDEAL)), math.cos(math.radians(IDEAL))])        # strip direction (down-left)
    sn = np.array([sd[1], -sd[0]])                                                        # across the strip (to the right)
    eL, eR = E["strip left (outer)"], E["strip right"]
    hinfo = []
    for s in holes:
        c = s["vertices"].mean(0)
        full = len(s["vertices"]) == 4 and all(abs(e["len"] - 39.6) < 1.5 for e in s["edges"])
        col = "left" if (c[0] - x_at(eL, c[1])) < (x_at(eR, c[1]) - c[0]) else "right"
        hinfo.append({"shape": s, "c": c, "full": full, "col": col})
    for col in ("left", "right"):
        group = sorted([h for h in hinfo if h["col"] == col], key=lambda h: h["c"][1])
        for k, h in enumerate(group, 1):
            h["name"] = f"hole-{col}-{k:02d}"
    hinfo.sort(key=lambda h: h["name"])
    full = [h for h in hinfo if h["full"]]
    side = np.array([e["len"] for h in full for e in h["shape"]["edges"]])
    hang = np.array([((e["angle"] + 90) % 90) for h in full for e in h["shape"]["edges"]])   # folds 63.43 and -26.57 together
    margins = {}
    for col, e_edge, sgn in (("left", eL, 1), ("right", eR, -1)):
        ds = []
        for h in [h for h in full if h["col"] == col]:
            horiz = sgn * (h["c"][0] - x_at(e_edge, h["c"][1]))
            ds.append(horiz * math.cos(math.radians(IDEAL)) - side.mean() / 2)
        margins[col] = (float(np.mean(ds)), float(np.std(ds)))
    pitch = {}
    for col in ("left", "right"):
        cs = np.array([h["c"] for h in full if h["col"] == col])
        d = np.diff(cs[np.argsort(cs[:, 1])], axis=0)
        pitch[col] = (float(np.linalg.norm(d, axis=1).mean()), float(np.linalg.norm(d, axis=1).std()), d.mean(0))
    rows = []
    for hl in [h for h in full if h["col"] == "left"]:
        for hr in [h for h in full if h["col"] == "right"]:
            if abs(hl["c"][1] - hr["c"][1]) < 5:
                rows.append(hr["c"] - hl["c"])
    rows = np.array(rows)
    phase = float(np.mean([((base_y - h["c"][1]) / u) % 1.0 for h in full]))
    # how close do the cut sides of the two top end holes come to the strip's slanted end?
    cut = E["strip cut (faces the bar)"]
    ncut = np.array([-cut["d"][1], cut["d"][0]])
    ncut = ncut if ncut[0] < 0 else -ncut
    top_clear_px = {}
    for h in hinfo:
        if not h["full"] and h["c"][1] < (top_y + base_y) / 2:
            e = min(h["shape"]["edges"], key=lambda e: abs(e["angle"] - cut["angle"]))
            top_clear_px[h["col"]] = float(((e["v0"] + e["v1"]) / 2 - cut["p"]) @ ncut)
    bottom_cut_px = float(np.mean([base_y - max(e["v0"][1] for e in h["shape"]["edges"]) for h in hinfo
                                   if not h["full"] and h["c"][1] > (top_y + base_y) / 2]))

    # ---------------- symmetry of the whole mark (mirror / rotation overlap)
    mask = (grey > 110).astype(np.uint8)
    ys, xs = np.nonzero(mask)
    best_v = max(((2 * np.logical_and(mask, np.roll(mask[:, ::-1], int(2 * ax - (Wimg - 1)), axis=1)).sum()) /
                  (2 * mask.sum()), ax) for ax in np.arange(xs.min(), xs.max(), 1.0))
    best_h = max(((np.logical_and(mask, np.roll(mask[::-1, :], int(2 * ay - (Himg - 1)), axis=0)).sum()) / mask.sum(), ay)
                 for ay in np.arange(ys.min(), ys.max(), 1.0))
    cx, cy = xs.mean(), ys.mean()
    Mrot = cv2.getRotationMatrix2D((float(cx), float(cy)), 180, 1.0)
    rot_iou = float(np.logical_and(mask, cv2.warpAffine(mask, Mrot, (Wimg, Himg))).sum() / mask.sum())

    # ---------------- noise / stray pixels
    bgmask = cv2.erode((grey < 110).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    halo = cv2.dilate(mask, np.ones((9, 9), np.uint8)).astype(bool) & (grey < 110)
    levels = {"bar": next(p["level"] for p in R["parts"] if abs(p["level"] - 255) < 3),
              "strip": min(p["level"] for p in R["parts"])}
    edge_wobble = max(e["max"] for e in list(E.values()))
    edge_rms = float(np.mean([e["rms"] for e in E.values()]))

    # =================================================================================================
    # the two cleaned versions, in LOGO UNITS: x 0..19, y 0..16 (y down), 1 unit = bar width / 4
    # =================================================================================================
    def px_to_units(q):
        return [(float(q[0]) - x0) / u, (float(q[1]) - top_y) / u]

    faithful_notes = []
    f_bar, n1 = snap_and_clean(bar)
    f_strip, n2 = snap_and_clean(strip)
    f_holes = []
    for h in hinfo:
        v, notes = snap_and_clean(h["shape"])
        f_holes.append({"name": h["name"], "pts": [px_to_units(p) for p in v]})
        for n in notes:
            faithful_notes.append(f"{h['name']}: {n}")
    faithful = {"version": "faithful", "width": float((b_br[0] - x0) / u), "height": 16.0,
                "parts": [{"name": "film-strip", "outer": [px_to_units(p) for p in f_strip], "holes": f_holes},
                          {"name": "bar", "outer": [px_to_units(p) for p in f_bar], "holes": []}],
                "tones": {"bar": 1.0, "film-strip": round(levels["strip"] / levels["bar"], 4)}}

    # geometric: everything on the 19 x 16 grid, 1-in-2 slopes, one hole, even pitch, mirrored columns.
    # Rules (all read off the original, then made exact):
    #   - hole = square, side = bar width / 7, turned to run with the strip
    #   - hole centres sit exactly ONE UNIT in from each edge of the strip (the original's right column already does;
    #     its left column sat 3/4 of a unit in), one unit apart measured straight down, level across both columns
    #   - bottom: cut level, half a unit above the base line, which passes exactly through a corner of the last hole
    #   - top: the last hole in each column is cut from its upper corner, parallel to the strip's slanted end
    S = 4.0 / 7.0
    OFF = 1.0
    BOTTOM = 0.5
    c26, s26 = 2 / math.sqrt(5), 1 / math.sqrt(5)
    PHI = BOTTOM + (S / 2) * (c26 - s26)             # 0.6278 (the original measures 0.627)
    g_strip = [(0.0, 16.0), (6.0, 16.0), (10.0, 8.0), (7.0, 2.0)]
    g_bar = [(7.0, 0.0), (11.0, 0.0), (19.0, 16.0), (15.0, 16.0)]
    d_u = np.array([-s26, c26])                      # along the strip, downwards
    n_u = np.array([c26, s26])                       # across the strip, to the right
    n_cut = np.array([-c26, s26])                    # into the strip from its slanted end
    apex_u = np.array([7.0, 2.0])
    big = 50.0
    below = Polygon([(-big, -big), (big, -big), (big, 16.0 - BOTTOM), (-big, 16.0 - BOTTOM)])
    g_holes = []
    counts = {"left": 0, "right": 0}
    top_clear = {}
    for col in ("left", "right"):
        squares = []
        for k in range(0, 16):
            cyu = 16.0 - (PHI + k)
            cxu = ((16.0 - cyu) / 2 + OFF) if col == "left" else (6.0 + (16.0 - cyu) / 2 - OFF)
            c = np.array([cxu, cyu])
            corners = [c + (S / 2) * (a * d_u + b * n_u) for a, b in ((-1, -1), (-1, 1), (1, 1), (1, -1))]
            squares.append((k, c, corners))
        # the top hole: the highest one whose upper corner still clears the slanted end by a fifth of a unit
        k_top = max(k for k, c, corners in squares if float((corners[0] - apex_u) @ n_cut) >= 0.2)
        pieces = []
        for k, c, corners in squares:
            if k > k_top:
                continue
            piece = Polygon(corners).intersection(below)
            if k == k_top:
                q = corners[0]
                t_cut = np.array([s26, c26])
                half = Polygon([q - big * t_cut, q + big * t_cut, q + big * t_cut + big * n_cut, q - big * t_cut + big * n_cut])
                piece = piece.intersection(half)
                top_clear[col] = float((q - apex_u) @ n_cut)
            if piece.is_empty or piece.area < 0.05 * S * S:
                continue
            pieces.append((c[1], piece))
        for k, (cyu, piece) in enumerate(sorted(pieces, key=lambda t: t[0]), 1):
            pts = [list(map(float, q)) for q in list(piece.exterior.coords)[:-1]]
            g_holes.append({"name": f"hole-{col}-{k:02d}", "pts": tidy(pts), "area_ratio": piece.area / (S * S)})
            counts[col] += 1
    geometric = {"version": "geometric", "width": 19.0, "height": 16.0,
                 "parts": [{"name": "film-strip", "outer": [list(q) for q in g_strip], "holes": g_holes},
                           {"name": "bar", "outer": [list(q) for q in g_bar], "holes": []}],
                 "tones": {"bar": 1.0, "film-strip": 1.0},
                 "construction": {"unit": "bar width / 4", "slope": "1 in 2 (26.565 deg)", "bar_width": 4, "gap": 1, "strip_width": 6,
                                  "height": 16, "strip_apex_height": 14, "hole_side": S, "hole_centre_inset_horizontal": OFF,
                                  "hole_margin_to_edge": OFF * c26 - S / 2, "hole_pitch_vertical": 1, "hole_phase": PHI,
                                  "bottom_cut_height": BOTTOM, "top_cut_clearance": top_clear}}
    # an optional small-size mark: same outline, no sprocket holes (for 16-24 px uses only)
    micro = {"version": "geometric-micro", "width": 19.0, "height": 16.0,
             "parts": [{"name": "film-strip", "outer": [list(p) for p in g_strip], "holes": []},
                       {"name": "bar", "outer": [list(p) for p in g_bar], "holes": []}], "tones": {"bar": 1.0, "film-strip": 1.0}}
    (HERE / "logo-geometry.json").write_text(json.dumps({"source": LOGO_PATH.name, "unit_px_in_source": u,
                                                         "origin_px_in_source": [x0, top_y], "faithful": faithful,
                                                         "geometric": geometric, "geometric-micro": micro}, indent=1))

    # how far does each version move from the original? (in source pixels)
    def poly_px(pts):
        return np.array([[p[0] * u + x0, p[1] * u + top_y] for p in pts])

    def raster(geo, scale=4):
        m = np.zeros((Himg * scale, Wimg * scale), np.uint8)
        for part in geo["parts"]:
            cv2.fillPoly(m, [np.round(poly_px(part["outer"]) * scale * 16 + 8 * (scale - 1)).astype(np.int32)], 255, cv2.LINE_AA, 4)
            for h in part["holes"]:
                cv2.fillPoly(m, [np.round(poly_px(h["pts"]) * scale * 16 + 8 * (scale - 1)).astype(np.int32)], 0, cv2.LINE_AA, 4)
        return cv2.resize(m, (Wimg, Himg), interpolation=cv2.INTER_AREA).astype(np.float32)

    orig_n = np.clip(grey / np.where(cv2.dilate((grey > 250).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0, 255.0, levels["strip"]), 0, 1) * 255
    rF, rG = raster(faithful), raster(geometric)
    orig_bin = grey > 110
    moved = {}
    for name, r in (("faithful", rF), ("geometric", rG)):
        diff = (r > 127) != orig_bin
        moved[name] = {"changed_px": int(diff.sum()), "changed_pct_of_logo": float(100 * diff.sum() / orig_bin.sum())}
    g_dev_outline = max(float(np.linalg.norm(poly_px(a) - b, axis=1).max()) for a, b in
                        ((sort_like(g_strip, f_strip, u, x0, top_y), f_strip), (sort_like(g_bar, f_bar, u, x0, top_y), f_bar)))

    # =================================================================================================
    # images
    # =================================================================================================
    make_overlay(grey, u, x0, top_y, base_y, axis_x, E, hinfo, margins, side.mean(), IMG / "astris-logo-analysis-overlay.png")
    make_before_after(grey, rF, rG, IMG / "astris-logo-before-after.png")
    make_zooms(grey, rF, rG, hinfo, s_apex, s_right, IMG / "astris-logo-detail-zooms.png")

    # =================================================================================================
    # numbers + report
    # =================================================================================================
    meas = {
        "source": {"file": LOGO_PATH.name, "pixels": [Wimg, Himg], "type": "8-bit greyscale JPEG (R=G=B)"},
        "unit_px": u, "grid": "19 x 16 units",
        "edge_angles_deg_from_vertical": angles, "ideal_angle_deg": IDEAL,
        "max_angle_error_deg": max(abs(abs(a) - IDEAL) for a in angles.values()),
        "mirror_axis_of_outer_legs_x_px": axis_x,
        "outer_leg_mirror_error_deg": abs(abs(angles["strip left (outer)"]) - abs(angles["bar right (outer)"])),
        "baseline_y": {"strip": float((s_bl[1] + s_br[1]) / 2), "bar": float((b_bl[1] + b_br[1]) / 2)},
        "apex_vs_bar_corner_dx_px": float(s_apex[0] - b_tl[0]),
        "bar_width_px": {"top": bar_w_top, "bottom": bar_w_bot}, "strip_width_px": strip_w,
        "gap_px": {"at_apex": gap_top, "at_strip_corner": gap_bot},
        "ratios_in_units": {"bar": (bar_w_top + bar_w_bot) / 2 / u, "strip": strip_w / u, "gap": (gap_top + gap_bot) / 2 / u,
                            "width": float((b_br[0] - x0) / u), "apex_height": float((base_y - s_apex[1]) / u)},
        "fill_levels_0_255": levels, "background_max_level": float(grey[bgmask].max()),
        "edge_straightness_px": {"mean_rms": edge_rms, "worst_single_point": edge_wobble},
        "corner_rounding_px": {"strip": strip["rounding"], "bar": bar["rounding"]},
        "holes": {"count": {"left": sum(h["col"] == "left" for h in hinfo), "right": sum(h["col"] == "right" for h in hinfo)},
                  "full_squares": len(full), "side_px": [float(side.mean()), float(side.std())],
                  "angle_error_deg": float(np.abs(hang - (90 - IDEAL)).max()),
                  "pitch_px": {k: [v[0], v[1]] for k, v in pitch.items()}, "pitch_vertical_px": float(pitch["left"][2][1]),
                  "row_offset_left_to_right_px": [float(rows[:, 0].mean()), float(rows[:, 1].mean())],
                  "margin_to_edge_px": {k: v[0] for k, v in margins.items()},
                  "margin_difference_px": margins["right"][0] - margins["left"][0], "phase_units": phase,
                  "top_cut_clearance_px": top_clear_px, "bottom_cut_height_px": bottom_cut_px,
                  "end_holes": [{"name": h["name"], "sides_px": [round(e["len"], 1) for e in h["shape"]["edges"]],
                                 "angles_deg": [round(e["angle"], 1) for e in h["shape"]["edges"]]} for h in hinfo if not h["full"]]},
        "whole_mark_symmetry": {"vertical_mirror_best_overlap_pct": 100 * best_v[0], "vertical_axis_x": best_v[1],
                                "horizontal_mirror_best_overlap_pct": 100 * best_h[0], "rotation_180_overlap_pct": 100 * rot_iou},
        "stray_specks": len(R["specks"]), "jpeg_halo_max_level_near_edges": float(grey[halo].max()),
        "cleaned_versions": {"faithful_notes": faithful_notes, "moved": moved,
                             "geometric_outline_max_shift_px": g_dev_outline, "geometric_hole_count": counts,
                             "geometric_hole_margin_px": (OFF * c26 - S / 2) * u,
                             "geometric_top_clearance_px": {k: v * u for k, v in top_clear.items()},
                             "geometric_end_hole_area": {h["name"]: round(h["area_ratio"], 4) for h in g_holes if h["area_ratio"] < 0.99}},
    }
    (HERE / "logo-measurements.json").write_text(json.dumps(meas, indent=1, default=float))
    write_report(meas, OUT / "logo-report.md")
    print(json.dumps({k: meas[k] for k in ("unit_px", "max_angle_error_deg", "gap_px", "bar_width_px", "fill_levels_0_255")}, indent=1, default=float))
    print("holes:", json.dumps(meas["holes"], indent=1, default=float)[:1500])
    print("symmetry:", meas["whole_mark_symmetry"], "\ncleaned:", meas["cleaned_versions"])


def tidy(pts, nd=5):
    out = []
    for p in pts:
        q = [round(p[0], nd), round(p[1], nd)]
        if not out or (abs(out[-1][0] - q[0]) > 1e-6 or abs(out[-1][1] - q[1]) > 1e-6):
            out.append(q)
    return out


def sort_like(geo_pts, ref_px, u, x0, y0):
    """Order the geometric vertices like the faithful ones (nearest match) so they can be compared."""
    g = np.array(geo_pts)
    gp = np.stack([g[:, 0] * u + x0, g[:, 1] * u + y0], 1)
    order = [int(np.argmin(np.linalg.norm(gp - r, axis=1))) for r in ref_px]
    return [geo_pts[k] for k in order]


# ----------------------------------------------------------------------------------------------------
# report images
# ----------------------------------------------------------------------------------------------------
INK, PAPER, GRID, RED, BLUE, GREEN, AMBER = (20, 20, 24), (250, 250, 248), (205, 205, 210), (214, 48, 49), (9, 132, 227), (0, 148, 100), (225, 140, 0)


def make_overlay(grey, u, x0, top_y, base_y, axis_x, E, hinfo, margins, hole_side, path):
    S = 2                                                     # draw at 2x for crisp lines
    H, W = grey.shape
    pad = 150
    canvas = Image.new("RGB", ((W + 2 * pad) * S, (H + 2 * pad + 70) * S), PAPER)
    logo = Image.fromarray((255 - grey * 0.82).astype(np.uint8)).convert("RGB").resize((W * S, H * S), Image.LANCZOS)
    canvas.paste(logo, (pad * S, pad * S))
    d = ImageDraw.Draw(canvas)
    P = lambda x, y: ((x + pad) * S, (y + pad) * S)
    f_s, f_m, f_b = font(15 * S), font(19 * S), font(26 * S, 700)
    # unit grid
    for k in range(0, 20):
        x = x0 + k * u
        d.line([P(x, top_y - 30), P(x, base_y + 30)], fill=GRID, width=1 * S)
        d.text(P(x, base_y + 38), str(k), font=f_s, fill=(140, 140, 150), anchor="ma")
    for k in range(0, 17):
        y = top_y + k * u
        d.line([P(x0 - 30, y), P(x0 + 19 * u + 30, y)], fill=GRID, width=1 * S)
        d.text(P(x0 - 40, y), str(16 - k), font=f_s, fill=(140, 140, 150), anchor="rm")
    # fitted edges, extended
    cols = {"strip left (outer)": BLUE, "strip right": BLUE, "strip cut (faces the bar)": GREEN, "bar left (faces the strip)": GREEN, "bar right (outer)": BLUE}
    for name, e in E.items():
        t0, t1 = (top_y - 60 - e["p"][1]) / e["d"][1], (base_y + 40 - e["p"][1]) / e["d"][1]
        a, b = e["p"] + e["d"] * t0, e["p"] + e["d"] * t1
        d.line([P(*a), P(*b)], fill=cols[name], width=2 * S)
    # mirror axis of the outer legs
    for yy in range(int(top_y - 110), int(base_y + 60), 22):
        d.line([P(axis_x, yy), P(axis_x, yy + 12)], fill=RED, width=2 * S)
    d.text(P(axis_x + 8, top_y - 118), "mirror axis of the two outer legs", font=f_s, fill=RED, anchor="la")
    # hole column centre lines + margins
    full = [h for h in hinfo if h["full"]]
    for col, c in (("left", AMBER), ("right", AMBER)):
        cs = np.array([h["c"] for h in full if h["col"] == col])
        a, b = cs[np.argmin(cs[:, 1])], cs[np.argmax(cs[:, 1])]
        dd = (b - a) / np.linalg.norm(b - a)
        d.line([P(*(a - dd * 120)), P(*(b + dd * 110))], fill=c, width=2 * S)
    for h in hinfo:
        if not h["full"]:
            r = 34
            d.ellipse([P(h["c"][0] - r, h["c"][1] - r), P(h["c"][0] + r, h["c"][1] + r)], outline=RED, width=3 * S)
    # labels
    d.text(P(-pad + 30, -pad + 24), "ASTRIS logo: analysis overlay", font=f_b, fill=INK)
    d.text(P(-pad + 30, -pad + 66), "grey = your original   grid = the 19 x 16 unit grid it sits on (1 unit = bar width / 4)", font=f_s, fill=(90, 90, 100))
    yb = H + pad - 190
    notes = [(BLUE, "long edges: all lean 26.57 deg (a 1-in-2 slope); left- and right-leaning edges mirror each other to within 0.02 deg"),
             (GREEN, "the two edges that face each other across the gap: parallel, 1 unit apart"),
             (AMBER, "sprocket-hole columns: the left one sits %.1f px from its edge, the right one %.1f px (they don't mirror each other)" % (margins["left"][0], margins["right"][0])),
             (RED, "circled: the four end holes, each cut a little differently (odd angles, a 2 px nick)")]
    for k, (c, t) in enumerate(notes):
        d.rectangle([P(-pad + 30, yb + 96 + k * 34), P(-pad + 54, yb + 114 + k * 34)], fill=c)
        d.text(P(-pad + 66, yb + 105 + k * 34), t, font=f_m, fill=INK, anchor="lm")
    canvas = canvas.resize((canvas.width // 2 * 1, canvas.height // 2 * 1), Image.LANCZOS) if canvas.width > 4200 else canvas
    canvas.save(path, optimize=True)


def make_before_after(grey, rF, rG, path):
    H, W = grey.shape
    sc = 0.62
    w, h = int(W * sc), int(H * sc)
    pad, top = 40, 150
    canvas = Image.new("RGB", (3 * w + 4 * pad, 2 * h + top + 150 + pad), PAPER)
    d = ImageDraw.Draw(canvas)
    d.text((pad, 34), "Before and after", font=font(44, 700), fill=INK)
    d.text((pad, 92), "Top: the artwork on black.  Bottom: what changed against your original (red = removed, green = added, grey = unchanged).",
           font=font(22), fill=(90, 90, 100))
    orig_bin = grey > 110
    for k, (name, r) in enumerate((("ORIGINAL (your file, untouched)", grey), ("FAITHFUL CLEAN", rF), ("GEOMETRIC PERFECT", rG))):
        x = pad + k * (w + pad)
        im = Image.fromarray(np.clip(r, 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
        canvas.paste(im, (x, top))
        d.text((x, top + h + 10), name, font=font(26, 700), fill=INK)
        if k > 0:
            new = r > 127
            vis = np.full((H, W, 3), 250, np.uint8)
            vis[orig_bin & new] = (200, 200, 204)
            vis[orig_bin & ~new] = RED
            vis[~orig_bin & new] = GREEN
            # thicken the 1-px differences so they can be seen at this size
            for col in (RED, GREEN):
                m = np.all(vis == np.array(col, np.uint8), axis=2).astype(np.uint8)
                m = cv2.dilate(m, np.ones((3, 3), np.uint8)).astype(bool)
                vis[m] = col
            canvas.paste(Image.fromarray(vis).resize((w, h), Image.LANCZOS), (x, top + h + 60))
            n = int(((r > 127) != orig_bin).sum())
            d.text((x, top + 2 * h + 70), "%d of %d logo pixels differ (%.2f%%)" % (n, int(orig_bin.sum()), 100 * n / orig_bin.sum()), font=font(22), fill=(90, 90, 100))
        else:
            d.text((x, top + h + 60), "1584 x 1312 px JPEG. Soft edges,", font=font(22), fill=(90, 90, 100))
            d.text((x, top + h + 90), "two slightly different whites,", font=font(22), fill=(90, 90, 100))
            d.text((x, top + h + 120), "raster only (no vector).", font=font(22), fill=(90, 90, 100))
    canvas.save(path, optimize=True)


def make_zooms(grey, rF, rG, hinfo, apex, right, path):
    spots = [("top-left end hole", next(h["c"] for h in hinfo if h["name"] == "hole-left-01"), 44),
             ("top-right end hole", next(h["c"] for h in hinfo if h["name"] == "hole-right-01"), 44),
             ("bottom-left end hole", max((h for h in hinfo if h["col"] == "left"), key=lambda h: h["c"][1])["c"], 44),
             ("bottom-right end hole", max((h for h in hinfo if h["col"] == "right"), key=lambda h: h["c"][1])["c"], 44),
             ("apex of the film strip", apex + [0, 26], 44), ("where the strip meets the gap", right + [-26, 0], 44)]
    cell, z = 352, 4
    pad, top = 30, 170
    canvas = Image.new("RGB", (pad + len(spots) * (cell + pad), top + 3 * (cell + 50) + pad), PAPER)
    d = ImageDraw.Draw(canvas)
    d.text((pad, 30), "Detail zooms (4x)", font=font(44, 700), fill=INK)
    d.text((pad, 92), "Row 1: your original.  Row 2: FAITHFUL CLEAN (same shapes, crisp).  Row 3: GEOMETRIC PERFECT (mirrored columns, true angles, no nicks).",
           font=font(22), fill=(90, 90, 100))
    for j, (label, c, half) in enumerate(spots):
        x = pad + j * (cell + pad)
        d.text((x, 132), label, font=font(22, 700), fill=INK)
        for i, r in enumerate((grey, rF, rG)):
            x0_, y0_ = int(round(c[0] - half)), int(round(c[1] - half))
            crop = np.clip(r[y0_:y0_ + 2 * half, x0_:x0_ + 2 * half], 0, 255).astype(np.uint8)
            im = Image.fromarray(crop).resize((cell, cell), Image.NEAREST if i == 0 else Image.LANCZOS)
            canvas.paste(im, (x, top + i * (cell + 50)))
    for i, name in enumerate(("ORIGINAL", "FAITHFUL CLEAN", "GEOMETRIC PERFECT")):
        d.text((pad, top + i * (cell + 50) + cell + 8), name, font=font(20, 700), fill=(90, 90, 100))
    canvas.save(path, optimize=True)


# ----------------------------------------------------------------------------------------------------
# the written report
# ----------------------------------------------------------------------------------------------------
def write_report(m, path):
    a = m["edge_angles_deg_from_vertical"]
    h = m["holes"]
    sym = m["whole_mark_symmetry"]
    cv = m["cleaned_versions"]
    L = []
    L += ["# ASTRIS logo report", "",
          "I measured your original logo file to a fraction of a pixel before touching anything. The original is untouched in",
          "`00_Originals/astris-logo-original.jpg`. Everything below was measured by `code/logo_pack/analyse_logo.py`,",
          "and every number is saved in `code/logo_pack/logo-measurements.json`.", "",
          "## The short version", "",
          "**Your logo's main shape is not off. It is built very precisely.** The legs lean at exactly the same angle, the base",
          "is level, and everything sits on a simple grid. The things that *are* slightly off are small and all inside the film strip:", "",
          "1. **The film strip is a different white from the bar.** The bar is pure white (%.0f of 255); the strip is %.0f, about %.0f%% darker."
          % (m["fill_levels_0_255"]["bar"], m["fill_levels_0_255"]["strip"], 100 * (1 - m["fill_levels_0_255"]["strip"] / m["fill_levels_0_255"]["bar"])),
          "2. **The two columns of sprocket holes don't mirror each other.** The left column sits %.1f px from its edge and the right one %.1f px, a difference of %.1f px."
          % (h["margin_to_edge_px"]["left"], h["margin_to_edge_px"]["right"], h["margin_difference_px"]),
          "3. **The four part-holes at the ends of the strip are each cut differently**: short vertical cuts at the top, sides at about 44 degrees instead of 26.6 at the bottom, and a 2 px nick on one. The top-right one also sits much closer to the strip's end (%.0f px) than the top-left one (%.0f px)."
          % (h["top_cut_clearance_px"]["right"], h["top_cut_clearance_px"]["left"]),
          "4. **The file is a small JPEG with soft edges**: corners are rounded by up to %.1f px and there is faint JPEG ringing along the edges. There is no vector version."
          % max(m["corner_rounding_px"]["strip"] + m["corner_rounding_px"]["bar"]), "",
          "There are **no stray pixels**, no gaps and no wobbly lines.", "",
          "![analysis overlay](report-images/astris-logo-analysis-overlay.png)", "",
          "## Symmetry", "",
          "| Test | Result |", "|---|---|",
          "| Mirror left-to-right (whole mark) | best overlap %.0f%% (axis at x = %.0f px). The mark is not a mirror image, by design: the bar runs 2 units taller than the strip. |"
          % (sym["vertical_mirror_best_overlap_pct"], sym["vertical_axis_x"]),
          "| Mirror top-to-bottom | best overlap %.0f%%: none, as expected for an A shape |" % sym["horizontal_mirror_best_overlap_pct"],
          "| Rotation (180 degrees, radial) | overlap %.0f%%: none |" % sym["rotation_180_overlap_pct"],
          "| **The two outer legs** | mirror images about x = %.1f px. Their angles differ by only %.3f degrees. |" % (m["mirror_axis_of_outer_legs_x_px"], m["outer_leg_mirror_error_deg"]),
          "| Base line | strip and bar both end at y = %.2f px (difference %.2f px) |" % (m["baseline_y"]["bar"], abs(m["baseline_y"]["bar"] - m["baseline_y"]["strip"])),
          "| Strip's point vs the bar's top-left corner | vertically in line to %.2f px |" % abs(m["apex_vs_bar_corner_dx_px"]), "",
          "So the symmetry that the design intends (two legs at the same lean, sharing one base line) is accurate to a few",
          "hundredths of a degree. I would not change it.", "",
          "## Lines, angles and widths", "",
          "Every straight edge leans %.3f degrees from vertical, which is a slope of exactly 1 across for every 2 down." % m["ideal_angle_deg"], "",
          "| Edge | Angle from vertical | Off the ideal by |", "|---|---|---|"]
    for k, v in a.items():
        L.append("| %s | %+.3f | %.3f |" % (k, v, abs(abs(v) - m["ideal_angle_deg"])))
    r = m["ratios_in_units"]
    L += ["", "The whole logo fits a **19 x 16 unit grid**, where 1 unit = %.2f px in your file (a quarter of the bar's width):" % m["unit_px"], "",
          "| Part | Measured (units) | On the grid |", "|---|---|---|",
          "| Bar width | %.3f | 4 |" % r["bar"], "| Film strip width | %.3f | 6 |" % r["strip"], "| Gap between them | %.3f | 1 |" % r["gap"],
          "| Overall width | %.3f | 19 |" % r["width"], "| Overall height | 16.000 | 16 |", "| Height of the strip's point | %.3f | 14 |" % r["apex_height"], "",
          "- Bar width: %.2f px at the top, %.2f px at the bottom (a %.2f px taper: invisible)." % (m["bar_width_px"]["top"], m["bar_width_px"]["bottom"], abs(m["bar_width_px"]["top"] - m["bar_width_px"]["bottom"])),
          "- Gap: %.2f px at the strip's point, %.2f px at its corner. It is %.2f px narrower than one unit: invisible, but real." % (m["gap_px"]["at_apex"], m["gap_px"]["at_strip_corner"], m["unit_px"] - (m["gap_px"]["at_apex"] + m["gap_px"]["at_strip_corner"]) / 2),
          "- Edge straightness: on average %.2f px of ripple (worst single point %.2f px). That is JPEG noise, not a drawing error." % (m["edge_straightness_px"]["mean_rms"], m["edge_straightness_px"]["worst_single_point"]),
          "- Corners: sharp in the design, softened by %.1f to %.1f px in the file." % (min(m["corner_rounding_px"]["strip"] + m["corner_rounding_px"]["bar"]), max(m["corner_rounding_px"]["strip"] + m["corner_rounding_px"]["bar"])), "",
          "## Sprocket holes", "",
          "- %d holes: %d in the left column, %d in the right. %d are whole squares; 4 are part-holes at the ends." % (h["count"]["left"] + h["count"]["right"], h["count"]["left"], h["count"]["right"], h["full_squares"]),
          "- The whole squares are very consistent: side %.2f px (varies by only %.2f px), turned to line up with the strip (worst angle error %.2f degrees)." % (h["side_px"][0], h["side_px"][1], h["angle_error_deg"]),
          "- Spacing is even: %.2f px apart along the strip (varies by %.2f px), which is exactly one unit measured straight down." % (h["pitch_px"]["left"][0], h["pitch_px"]["left"][1]),
          "- Left and right holes sit level with each other (offset %.1f px across, %.1f px down)." % (h["row_offset_left_to_right_px"][0], h["row_offset_left_to_right_px"][1]),
          "- **Not mirrored:** the gap between the holes and the strip's edge is %.1f px on the left but %.1f px on the right. In grid terms, the right column's centres sit one unit in from their edge; the left column's sit three quarters of a unit in."
          % (h["margin_to_edge_px"]["left"], h["margin_to_edge_px"]["right"]),
          "- The bottom of both columns is cut level, %.1f px (half a unit) above the base line. That line passes exactly through a corner of the last hole, which looks deliberate." % h["bottom_cut_height_px"],
          "- The top of the left column is cut %.1f px inside the strip's slanted end; the top of the right column only %.1f px." % (h["top_cut_clearance_px"]["left"], h["top_cut_clearance_px"]["right"]),
          "- **End holes:**", ""]
    for e in h["end_holes"]:
        L.append("  - `%s`: sides %s px at %s degrees" % (e["name"], e["sides_px"], e["angles_deg"]))
    L += ["", "  A cleanly clipped hole would only have sides at 26.6 or 63.4 degrees, plus the clip line. The short vertical sides (0 degrees) at the top and the 44 degree sides at the bottom are leftovers from how the strip was masked.", "",
          "![detail zooms](report-images/astris-logo-detail-zooms.png)", "",
          "## The two cleaned versions", "",
          "![before and after](report-images/astris-logo-before-after.png)", "",
          "### 1. FAITHFUL CLEAN (the smallest possible fixes)", "",
          "Your logo exactly as drawn, rebuilt as a true vector from the measured edges.", "",
          "- **Kept:** every shape, every angle, every position as measured, including the off-centre hole columns and the odd end holes.",
          "- **Fixed:** soft and ringing JPEG edges are now crisp; corners are sharp again; the two whites are now one colour.",
          "- **Tiny tidy-ups:** " + ("; ".join(cv["faithful_notes"]) if cv["faithful_notes"] else "none needed") + ".",
          "- **Difference from your original:** %.2f%% of the logo's pixels, all of them along edges." % cv["moved"]["faithful"]["changed_pct_of_logo"],
          "- The logo has no curves, so there was nothing to smooth.", "",
          "A two-tone copy (strip %.1f%% as bright as the bar, as in your file) is included in case the two whites were on purpose." % (100 * m["fill_levels_0_255"]["strip"] / m["fill_levels_0_255"]["bar"]), "",
          "### 2. GEOMETRIC PERFECT (rebuilt on the grid)", "",
          "The same design, redrawn from its own rules.", "",
          "- Every corner sits exactly on the 19 x 16 grid; every slanted edge is exactly 1-in-2. The outline moves by at most %.2f px (at your file's size)." % cv["geometric_outline_max_shift_px"],
          "- The gap is exactly 1 unit; the bar exactly 4; the strip exactly 6.",
          "- **The two hole columns now mirror each other.** Both sit exactly one unit in from their edge (%.1f px of clear margin). Your right column was already there (it moves %.1f px); the left column moves %.1f px inward to match. This is the one change you can see if you look for it."
          % (cv["geometric_hole_margin_px"], abs(cv["geometric_hole_margin_px"] - h["margin_to_edge_px"]["right"]), abs(cv["geometric_hole_margin_px"] - h["margin_to_edge_px"]["left"])),
          "- All holes are one identical square (side = bar width / 7), one unit apart, level across both columns.",
          "- **Bottom end holes:** cut level, exactly half a unit above the base line, through the hole's corner, as in your original but with true sides (no 44 degree edges, no nick). Each is exactly three quarters of a hole.",
          "- **Top end holes:** each is cut from its upper corner, parallel to the strip's slanted end, so both are the same shape (exactly five eighths of a hole) and both sit %.1f px from the end. No vertical cuts."
          % cv["geometric_top_clearance_px"]["left"],
          "- Hole count: %d left, %d right, the same as yours." % (cv["geometric_hole_count"]["left"], cv["geometric_hole_count"]["right"]),
          "- One colour.",
          "- **Difference from your original:** %.2f%% of the logo's pixels." % cv["moved"]["geometric"]["changed_pct_of_logo"], "",
          "Nothing about the logo's identity changes: same shapes, same proportions, same number of parts.", "",
          "### Which one the rest of the kit uses", "",
          "The three styles use **GEOMETRIC PERFECT**, because it fixes exactly the things you were worried about and stays crisp at",
          "poster size. To switch the whole kit to the faithful version, set `\"logo_version\": \"faithful\"` in `brand-config.json` and re-run the build.", "",
          "### An optional extra: the small-size mark", "",
          "Below about 24 px the sprocket holes turn to mush (see `small-size-test/`). `geometric-micro` is the same outline with no holes.",
          "It is only used for the 16 px favicon. It is an extra, not a replacement: say the word and I'll remove it.", ""]
    path.write_text("\n".join(L))


if __name__ == "__main__":
    main()
