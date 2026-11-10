"""
Logo files in a style's colours (clean and flat: no grain), in four layouts and five colourways,
plus the animation-ready set (separate layers + layered SVG).

Layouts:    wide (icon beside the wordmark), stacked (icon above), icon, wordmark
Colourways: full-colour, single-colour, black, white, on-colour (opaque, on the style's field)
"""
import cv2
import numpy as np
from PIL import Image
from shapely.affinity import translate
from shapely.geometry import Polygon
from shapely.ops import unary_union

from engine import type as T
from engine.core import hex_rgb
from engine.logo import fmt, path_d, raster_polys
from engine.lockup import brand, stacked_sizes
from engine.paths import out

U = 100.0                      # 1 logo unit = 100 layout units
LAYOUTS = ["wide", "stacked", "icon", "wordmark"]
COLOURWAYS = ["full-colour", "single-colour", "black", "white", "on-colour"]


def palette(style, way):
    """Colour of each role (icon, word1, word2, shadow, tile, background) for a colourway. None = not drawn."""
    h, k = style.hex, style.key
    if way == "black":
        return dict(icon="#000000", word1="#000000", word2="#000000")
    if way == "white":
        return dict(icon="#FFFFFF", word1="#FFFFFF", word2="#FFFFFF")
    if way == "single-colour":
        c = h["signature"]
        return dict(icon=c, word1=c, word2=c)
    if way == "on-colour":
        if k == "red":
            return dict(icon=h["light"], word1=h["light"], word2=h["light"], background=h["signature"])
        if k == "yellow":
            return dict(icon=h["dark"], word1=h["dark"], word2=h["dark"], background=h["signature"])
        return dict(icon=h["signature"], word1=h["signature"], word2=h["signature"], shadow=h["second"], background=h["light"])
    # full colour
    if k == "red":
        return dict(icon=h["signature"], word1=h["dark"], word2=h["signature"])
    if k == "yellow":                       # yellow never sits on a light background on its own: it gets a black partner
        return dict(icon=h["dark"], word1=h["dark"], word2=h["dark"], tile=h["signature"])
    return dict(icon=h["signature"], word1=h["signature"], word2=h["signature"], shadow=h["second"])


def spec(style, layout, tile=False):
    """Geometry of a lockup in layout units: {'size': (w, h), 'icon': (x, y, height) or None,
    'words': [(role, text, size, tracking, x_left, baseline)], 'tile': (x0, y0, x1, y1, radius) or None}."""
    lg, face, b = style.logo, style.display, brand()
    ih = lg.h * U
    iw = lg.w * U
    words, icon, tl = [], None, None

    def stack(x_left, top, width):
        s1, s2, track = stacked_sizes(face, width)
        cap1, cap2 = face.cap * s1, face.cap * s2
        w1 = T.text_width(b["first_word"], face, s1, 0.02)
        words.append(("word1", b["first_word"], s1, 0.02, x_left + (width - w1) / 2, top + cap1))
        words.append(("word2", b["second_word"], s2, track, x_left, top + cap1 * 1.20 + cap2))
        return cap1 * 1.20 + cap2

    if layout == "icon":
        if tile:
            side = ih * 1.55
            tl = (0, 0, side, side, side * 0.19)
            icon = ((side - iw) / 2, (side - ih) / 2 - ih * 0.012, ih)
            W, H = side, side
        else:
            icon, W, H = (0, 0, ih), iw, ih
    elif layout == "wordmark":
        width = 3800.0
        pad = 300.0 if tile else 0.0
        hh = stack(pad, pad, width)
        W, H = width + 2 * pad, hh + 2 * pad
        if tile:
            tl = (0, 0, W, H, H * 0.14)
    elif layout == "stacked":
        if tile:
            side = ih * 1.55
            tl = (0, 0, side, side, side * 0.19)
            icon = ((side - iw) / 2, (side - ih) / 2 - ih * 0.012, ih)
            hh = stack(0, side + ih * 0.30, side)
            W, H = side, side + ih * 0.30 + hh
        else:
            icon = (0, 0, ih)
            hh = stack(0, ih + ih * 0.26, iw)
            W, H = iw, ih + ih * 0.26 + hh
    else:   # wide
        if tile:
            side = ih * 1.55
            tl = (0, 0, side, side, side * 0.19)
            icon = ((side - iw) / 2, (side - ih) / 2 - ih * 0.012, ih)
            block_h, x_text = side * 0.62, side + side * 0.26
        else:
            icon = (0, 0, ih)
            block_h, x_text = ih * 0.86, iw + ih * 0.34
        s1 = block_h / (face.cap * (1 + 0.20 + 0.27))
        width = T.text_width(b["first_word"], face, s1, 0.02)
        full_h = side if tile else ih
        hh = stack(x_text, (full_h - block_h) / 2, width)
        W, H = x_text + width, full_h
    return {"size": (W, H), "icon": icon, "words": words, "tile": tl}


def shadow_offset(sp):
    ref = sp["icon"][2] * 0.55 if sp["icon"] else sp["words"][0][2]
    off = 0.030 * ref
    return off, off * 0.9


def render(style, layout, way, width_px, pad_frac=0.0):
    """RGBA uint8 image of a lockup at a pixel width (the lockup itself; padding only for on-colour)."""
    pal = palette(style, way)
    sp = spec(style, layout, tile=bool(pal.get("tile")))
    W, H = sp["size"]
    pad = pad_frac * max(W, H)
    k = width_px / (W + 2 * pad)
    w, h = int(round(width_px)), int(round((H + 2 * pad) * k))
    ox, oy = pad * k, pad * k
    rgb = np.zeros((h, w, 3), np.float32)
    alpha = np.zeros((h, w), np.float32)

    def over(mask, hexcol):
        nonlocal rgb, alpha
        c = hex_rgb(hexcol)
        rgb = rgb * (1 - mask[..., None]) + c * mask[..., None]
        alpha = alpha + mask * (1 - alpha)

    if pal.get("background"):
        over(np.ones((h, w), np.float32), pal["background"])
    if sp["tile"]:
        x0, y0, x1, y1, r = [v * k for v in sp["tile"]]
        m = np.zeros((h, w), np.float32)
        from engine.core import rounded_mask
        tm = rounded_mask(int(round(y1 - y0)), int(round(x1 - x0)), r)
        yy, xx = int(round(oy + y0)), int(round(ox + x0))
        m[yy:yy + tm.shape[0], xx:xx + tm.shape[1]] = tm[: h - yy, : w - xx]
        over(m, pal["tile"])
    ss = 4 if width_px <= 2048 else 2
    sdx, sdy = [v * k for v in shadow_offset(sp)]
    masks = {}
    if sp["icon"]:
        ix, iy, ih = sp["icon"]
        masks["icon"] = style.logo.mask((h, w), ox + ix * k, oy + iy * k, ih * k, ss=ss)
        masks["icon_solid"] = style.logo.mask((h, w), ox + ix * k, oy + iy * k, ih * k, ss=ss, holes=False)
    for role, text, size, track, x, base in sp["words"]:
        tm, (tx, ty) = T.text_mask(text, style.display, size * k, track, ss=2 if size * k > 300 else 3)
        m = np.zeros((h, w), np.float32)
        px, py = int(round(ox + x * k + tx)), int(round(oy + base * k + ty))
        y0, x0 = max(0, py), max(0, px)
        y1, x1 = min(h, py + tm.shape[0]), min(w, px + tm.shape[1])
        m[y0:y1, x0:x1] = tm[y0 - py:y1 - py, x0 - px:x1 - px]
        masks[role] = np.maximum(masks.get(role, 0), m)
    if pal.get("shadow"):
        Mx = np.float32([[1, 0, sdx], [0, 1, sdy]])
        for role in ("icon", "word1"):                          # the small word stays clean so it reads
            if role in masks:
                sh = cv2.warpAffine(masks[role], Mx, (w, h), flags=cv2.INTER_LINEAR)
                if role == "icon":
                    sh = sh * (1 - masks["icon_solid"])
                over(sh, pal["shadow"])
    for role in ("icon", "word1", "word2"):
        if role in masks:
            over(masks[role], pal[role])
    a8 = np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8)
    out8 = np.clip(rgb / np.maximum(alpha, 1e-6)[..., None] * 255 + 0.5, 0, 255).astype(np.uint8)
    out8[a8 == 0] = 255 if way == "white" else 0
    if way == "white":
        out8[a8 == 0] = 255
    return Image.fromarray(np.dstack([out8, a8]), "RGBA")


def svg(style, layout, way, title):
    pal = palette(style, way)
    sp = spec(style, layout, tile=bool(pal.get("tile")))
    W, H = sp["size"]
    pad = 0.08 * max(W, H) if pal.get("background") else 0.0
    L = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{fmt(-pad)} {fmt(-pad)} {fmt(W + 2 * pad)} {fmt(H + 2 * pad)}">', f"  <title>{title}</title>"]
    if pal.get("background"):
        L.append(f'  <rect id="background" x="{fmt(-pad)}" y="{fmt(-pad)}" width="{fmt(W + 2 * pad)}" height="{fmt(H + 2 * pad)}" fill="{pal["background"]}"/>')
    if sp["tile"]:
        x0, y0, x1, y1, r = sp["tile"]
        L.append(f'  <rect id="tile" x="{fmt(x0)}" y="{fmt(y0)}" width="{fmt(x1 - x0)}" height="{fmt(y1 - y0)}" rx="{fmt(r)}" fill="{pal["tile"]}"/>')
    sdx, sdy = shadow_offset(sp)
    icon_paths, word_paths = [], []
    if sp["icon"]:
        ix, iy, ih = sp["icon"]
        polys = style.logo.polys(ix, iy, ih)
        if pal.get("shadow"):
            shapes = [Polygon(o, hs) for _, o, hs in polys]
            solid = unary_union([Polygon(o) for _, o, hs in polys])
            sh = unary_union([translate(s, sdx, sdy) for s in shapes]).difference(solid)
            geoms = list(sh.geoms) if hasattr(sh, "geoms") else [sh]
            d = " ".join(path_d(list(g.exterior.coords)[:-1], 2) + "".join(" " + path_d(list(r_.coords)[:-1], 2) for r_ in g.interiors) for g in geoms if not g.is_empty)
            L.append(f'  <path id="logo-shadow" fill="{pal["shadow"]}" fill-rule="evenodd" d="{d}"/>')
        L.append(f'  <g id="logo" fill="{pal["icon"]}">')
        for name, o, hs in polys:
            d = " ".join([path_d(o)] + [path_d(q) for q in hs])
            L.append(f'    <path id="{name}" fill-rule="evenodd" d="{d}"/>')
        L.append("  </g>")
    if sp["words"]:
        if pal.get("shadow"):
            L.append(f'  <g id="wordmark-shadow" fill="{pal["shadow"]}">')
            for role, text, size, track, x, base in sp["words"]:
                if role != "word1":
                    continue
                d, _ = T.text_svg(text, style.display, size, track, x + sdx, base + sdy)
                L.append(f'    <path d="{d}"/>')
            L.append("  </g>")
        L.append('  <g id="wordmark">')
        for role, text, size, track, x, base in sp["words"]:
            d, _ = T.text_svg(text, style.display, size, track, x, base)
            L.append(f'    <path id="{text.lower()}" fill="{pal[role]}" d="{d}"/>')
        L.append("  </g>")
    L.append("</svg>")
    return "\n".join(L) + "\n"


def layer_png(mask, hexcol):
    c = (hex_rgb(hexcol) * 255 + 0.5).astype(np.uint8)
    a8 = np.clip(mask * 255 + 0.5, 0, 255).astype(np.uint8)
    arr = np.empty(mask.shape + (4,), np.uint8)
    arr[..., :3] = c
    arr[..., 3] = a8
    return Image.fromarray(arr, "RGBA")


def animation_ready(style):
    """Clean hi-res logo + every part as its own transparent PNG on the same canvas, + layered SVGs."""
    k = style.key
    base = out(k, "logos", "animation-ready")
    lg = style.logo
    made = 0
    ink = {"red": style.hex["light"], "yellow": style.hex["dark"], "wildcard": style.hex["signature"]}[k]
    for cname, col in (("style-colour", ink), ("white", "#FFFFFF")):
        # ---- icon canvas, 4096 wide
        d1 = base / f"icon-layers-{cname}"
        (d1 / "holes").mkdir(parents=True, exist_ok=True)
        w = 4096
        h = int(round(w / lg.aspect))
        shape = (h, w)
        hh = float(h)
        layer_png(lg.mask(shape, 0, 0, hh, ss=2), col).save(base / f"astris-{k}-logo-animation-ready-{cname}-4096.png", optimize=True)
        for i, part in enumerate(lg.parts, 1):
            layer_png(lg.mask(shape, 0, 0, hh, parts=[part["name"]], ss=2), col).save(d1 / f"astris-{k}-layer-{i:02d}-{part['name']}.png", optimize=True)
            made += 1
            if part["holes"]:
                layer_png(lg.mask(shape, 0, 0, hh, parts=[part["name"]], ss=2, holes=False), col).save(d1 / f"astris-{k}-layer-{i:02d}-{part['name']}-solid-no-holes.png", optimize=True)
                polys = lg.polys(0, 0, hh, [part["name"]])
                layer_png(raster_polys(polys, shape, ss=2, only_holes=True), col).save(d1 / f"astris-{k}-layer-{i:02d}-{part['name']}-holes-only.png", optimize=True)
                for j, hole in enumerate(part["holes"]):
                    layer_png(raster_polys(polys, shape, ss=2, only_holes=[j]), col).save(d1 / "holes" / f"astris-{k}-{hole['name']}.png", optimize=True)
                    made += 1
        # ---- stacked lockup canvas, 4096 wide: logo parts + each word
        d2 = base / f"lockup-layers-{cname}"
        d2.mkdir(parents=True, exist_ok=True)
        sp = spec(style, "stacked")
        W, H = sp["size"]
        kk = 4096 / W
        shape = (int(round(H * kk)), 4096)
        ix, iy, ih = sp["icon"]
        for i, part in enumerate(lg.parts, 1):
            layer_png(lg.mask(shape, ix * kk, iy * kk, ih * kk, parts=[part["name"]], ss=2), col).save(d2 / f"astris-{k}-lockup-layer-{i:02d}-{part['name']}.png", optimize=True)
        for i, (role, text, size, track, x, basey) in enumerate(sp["words"], len(lg.parts) + 1):
            tm, (tx, ty) = T.text_mask(text, style.display, size * kk, track, ss=2)
            m = np.zeros(shape, np.float32)
            px, py = int(round(x * kk + tx)), int(round(basey * kk + ty))
            y0, x0 = max(0, py), max(0, px)
            y1, x1 = min(shape[0], py + tm.shape[0]), min(shape[1], px + tm.shape[1])
            m[y0:y1, x0:x1] = tm[y0 - py:y1 - py, x0 - px:x1 - px]
            layer_png(m, col).save(d2 / f"astris-{k}-lockup-layer-{i:02d}-word-{text.lower()}.png", optimize=True)
            made += 1
    # ---- layered SVGs
    (base / f"astris-{k}-logo-layered.svg").write_text(layered_svg(style, "icon", ink))
    (base / f"astris-{k}-lockup-layered.svg").write_text(layered_svg(style, "stacked", ink))
    return made


def layered_svg(style, layout, col):
    sp = spec(style, layout)
    W, H = sp["size"]
    lg = style.logo
    ix, iy, ih = sp["icon"]
    L = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(W)} {fmt(H)}">',
         f"  <title>ASTRIS {'logo' if layout == 'icon' else 'lockup'}, {style.name} style, layered for animation</title>",
         "  <!-- Every part is a named group. 'extras-for-animation' (hidden) holds the strip without holes and each",
         "       sprocket hole as its own shape, numbered from the top of each column. -->",
         f'  <g id="logo" fill="{col}">']
    polys = lg.polys(ix, iy, ih)
    for name, o, hs in polys:
        d = " ".join([path_d(o)] + [path_d(q) for q in hs])
        L += [f'    <g id="{name}">', f'      <path id="{name}-shape" fill-rule="evenodd" d="{d}"/>', "    </g>"]
    L.append("  </g>")
    if sp["words"]:
        L.append(f'  <g id="wordmark" fill="{col}">')
        for role, text, size, track, x, base in sp["words"]:
            L.append(f'    <g id="word-{text.lower()}">')
            glyphs, _ = T.shape(text, style.display, size, track)
            for n, (ch, gname, gx) in enumerate(glyphs, 1):
                d, _ = T.text_svg(ch, style.display, size, 0.0, x + gx, base)
                L.append(f'      <path id="{text.lower()}-{n:02d}-{ch.lower()}" d="{d}"/>')
            L.append("    </g>")
        L.append("  </g>")
    L.append('  <g id="extras-for-animation" display="none">')
    for (name, o, hs), part in zip(polys, lg.parts):
        if hs:
            L.append(f'    <path id="{name}-solid" fill="{col}" d="{path_d(o)}"/>')
            L.append('    <g id="sprocket-holes" fill="#808080">')
            for q, hole in zip(hs, part["holes"]):
                L.append(f'      <path id="{hole["name"]}" d="{path_d(q)}"/>')
            L.append("    </g>")
    L += ["  </g>", "</svg>"]
    return "\n".join(L) + "\n"


def build(style):
    k = style.key
    n = 0
    for layout in LAYOUTS:
        for way in COLOURWAYS:
            name = f"astris-{k}-logo-{layout}-{way}"
            pad = 0.08 if way == "on-colour" else 0.0
            for size, sub in ((4096, "png-4096"), (512, "png-512")):
                render(style, layout, way, size, pad).save(out(k, "logos", sub) / f"{name}-{size}.png", optimize=True)
            (out(k, "logos", "svg") / f"{name}.svg").write_text(svg(style, layout, way, f"ASTRIS PRODUCTIONS logo, {style.name} style, {layout}, {way}"))
            n += 3
    m = animation_ready(style)
    return [f"{n} logo files + {m} animation layers"]
