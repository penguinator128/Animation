"""
Geometry export for the three.js scenes (hero 2, the fly-through ident, 3D stills).
Units: logo height = 1, origin at the logo centre, y up (three.js convention).

  pieces : the traced logo, exact (outer contour + sprocket holes)
  shards : the logo fractured into ~46 Lloyd-relaxed Voronoi shards (hero 2 assembles them)
  text   : ASTRIS / PRODUCTIONS glyphs laid out exactly like the shared 2D lockup, one entry per letter
"""
import json

import numpy as np
from shapely.geometry import MultiPoint, MultiPolygon, Point, Polygon
from shapely.ops import unary_union, voronoi_diagram

import common as C


def _poly_json(p):
    return {"outer": [(float(x), float(y)) for x, y in list(p.exterior.coords)[:-1]],
            "holes": [[(float(x), float(y)) for x, y in list(h.coords)[:-1]] for h in p.interiors]}


def logo_pieces(logo):
    pieces, polys = [], []
    for k in range(len(logo.pieces)):
        pp = logo.piece_polys(k)
        outer = [(float(x), float(-y)) for x, y in pp[0]]
        holes = [[(float(x), float(-y)) for x, y in h] for h in pp[1:]]
        pieces.append({"outer": outer, "holes": holes})
        polys.append(Polygon(outer, holes).buffer(0))
    return pieces, unary_union(polys)


def shards(shape, n_shards=46, seed=7):
    minx, miny, maxx, maxy = shape.bounds
    rng = np.random.default_rng(seed)
    pts = []
    while len(pts) < n_shards:
        p = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
        if shape.contains(p):
            pts.append(p)
    env = shape.envelope.buffer(0.5)
    for _ in range(3):                                # Lloyd relaxation -> even shards
        cells = voronoi_diagram(MultiPoint(pts), envelope=env)
        new = []
        for c in cells.geoms:
            g = c.intersection(shape)
            if not g.is_empty:
                new.append(g.centroid if shape.contains(g.centroid) else g.representative_point())
        pts = new
    out = []
    for c in voronoi_diagram(MultiPoint(pts), envelope=env).geoms:
        g = c.intersection(shape)
        for s in (g.geoms if isinstance(g, MultiPolygon) else [g]):
            if s.geom_type != "Polygon" or s.area < 1e-5:
                continue
            s = s.simplify(0.0004, preserve_topology=True)
            d = _poly_json(s)
            d.update({"c": [float(s.centroid.x), float(s.centroid.y)], "area": float(s.area)})
            out.append(d)
    return out


def glyph_polys(contours_px, to_lu):
    """Font contours (even-odd) -> shapely polygons with holes, in logo units."""
    geom = None
    for c in contours_px:
        p = Polygon([to_lu(x, y) for x, y in c]).buffer(0)
        if p.is_empty:
            continue
        geom = p if geom is None else geom.symmetric_difference(p)
    if geom is None:
        return []
    return [g for g in (geom.geoms if hasattr(geom, "geoms") else [geom]) if g.area > 1e-7]


def lockup_text(lock):
    """Every letter of ASTRIS / PRODUCTIONS where the 2D lockup puts it (S = 1), in logo units."""
    lcx, lcy, lh = lock.logo_xy(1.0)

    def to_lu(x, y):
        return ((x - lcx) / lh, -(y - lcy) / lh)

    out = {}
    for which in ("astris", "prod"):
        letters = []
        for polys in lock.word_polys(which, 1.0):
            gp = glyph_polys(polys, to_lu)
            if not gp:
                continue
            u = unary_union(gp)
            minx, miny, maxx, maxy = u.bounds
            letters.append({"polys": [_poly_json(g) for g in gp], "c": [float(u.centroid.x), float(u.centroid.y)],
                            "base": float(miny), "bbox": [float(minx), float(miny), float(maxx), float(maxy)]})
        out[which] = letters
    return out


def lockup2_text(lock2, logo_c, logo_h, names=("astris", "prod")):
    """Like lockup_text, for a kit.Lockup2 (any fonts): letters in logo units, y up."""
    def to_lu(x, y):
        return ((x - logo_c[0]) / logo_h, -(y - logo_c[1]) / logo_h)

    out = {}
    for i, which in enumerate(names):
        letters = []
        for L in lock2.line(i):
            gp = glyph_polys(L["polys"], to_lu)
            if not gp:
                continue
            u = unary_union(gp)
            minx, miny, maxx, maxy = u.bounds
            letters.append({"polys": [_poly_json(g) for g in gp], "c": [float(u.centroid.x), float(u.centroid.y)],
                            "base": float(miny), "bbox": [float(minx), float(miny), float(maxx), float(maxy)]})
        out[which] = letters
    return out


def build(path, with_shards=True):
    logo = C.Logo()
    lock = C.Lockup(logo)
    pieces, shape = logo_pieces(logo)
    data = {"pieces": pieces, "aspect": logo.aspect, "text": lockup_text(lock)}
    if with_shards:
        data["shards"] = shards(shape)
    path.write_text(json.dumps(data))
    n = sum(len(v) for v in data["text"].values())
    print(f"[geometry] {len(pieces)} logo pieces, {len(data.get('shards', []))} shards, {n} letters -> {path.name}")
    return data


if __name__ == "__main__":
    build(C.ROOT / "hero2_geometry.json")
