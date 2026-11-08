"""
Exports the traced logo for the intro 2 three.js scene:
  - the logo pieces (outer contour + sprocket holes), exact
  - the logo fractured into ~46 Voronoi shards (Lloyd-relaxed so they're evenly sized), clipped to the real
    shape so they reassemble into exactly the logo.
Units: logo height = 1, centred, y up (three.js convention).
"""
import json

import numpy as np
from shapely.geometry import MultiPoint, MultiPolygon, Point, Polygon
from shapely.ops import unary_union, voronoi_diagram

import common as C

OUT = C.ROOT / "intro2_geometry.json"


def build(n_shards=46, seed=7):
    logo = C.Logo()
    pieces = []
    polys = []
    for k in range(len(logo.pieces)):
        pp = logo.piece_polys(k)
        outer = [(float(x), float(-y)) for x, y in pp[0]]
        holes = [[(float(x), float(-y)) for x, y in h] for h in pp[1:]]
        pieces.append({"outer": outer, "holes": holes})
        polys.append(Polygon(outer, holes).buffer(0))
    shape = unary_union(polys)
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
    cells = voronoi_diagram(MultiPoint(pts), envelope=env)
    shards = []
    for c in cells.geoms:
        g = c.intersection(shape)
        geoms = g.geoms if isinstance(g, MultiPolygon) else [g]
        for s in geoms:
            if s.geom_type != "Polygon" or s.area < 1e-5:
                continue
            s = s.simplify(0.0004, preserve_topology=True)
            shards.append({
                "outer": [(float(x), float(y)) for x, y in list(s.exterior.coords)[:-1]],
                "holes": [[(float(x), float(y)) for x, y in list(h.coords)[:-1]] for h in s.interiors],
                "c": [float(s.centroid.x), float(s.centroid.y)],
                "area": float(s.area),
            })
    data = {"pieces": pieces, "shards": shards, "aspect": logo.aspect}
    OUT.write_text(json.dumps(data))
    print(f"[intro2] exported {len(pieces)} pieces and {len(shards)} shards -> {OUT.name}")
    return data


if __name__ == "__main__":
    build()
