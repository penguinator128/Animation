"""
ASTRIS PRODUCTIONS - bare-bones logo pack, step 2: EXPORT the two cleaned versions (no style, just the logo).

For FAITHFUL CLEAN and GEOMETRIC PERFECT:
  svg/      black, white, single-colour (uses currentColor) [+ two-tone for the faithful version]
  pdf/      black, white (true vector)
  png/      transparent, 512 / 1024 / 2048 / 4096 / 8192 px wide, in black, white and a neutral single colour
  1-bit/    pure black-and-white, no grey pixels (stamps, embroidery, laser)
  previews/ on-dark and on-light
  *-layered.svg   every part in a named group, for animation
plus small-size-test/ (16-64 px) and the optional no-holes small-size mark.

Usage: python3 code/logo_pack/build_logo_pack.py        (run analyse_logo.py first)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas as pdfcanvas

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.logo import Logo, fmt, path_d, svg_paths          # noqa: E402
from engine.paths import FONTS, LOGO_PACK                      # noqa: E402

SIZES = [512, 1024, 2048, 4096, 8192]
NEUTRAL = (128, 128, 128)                # the "single colour" proof: a mid grey that reads on light and on dark
VERSIONS = [("faithful", "faithful-clean", "FAITHFUL CLEAN"), ("geometric", "geometric-perfect", "GEOMETRIC PERFECT")]
U = 100.0                                # 1 logo unit = 100 SVG units -> the geometric logo is exactly 1900 x 1600


def font(size, weight=500):
    return ImageFont.truetype(str(FONTS / f"dm-sans-{weight}.ttf"), size)


def rgba(mask, colour):
    a = np.clip(mask * 255 + 0.5, 0, 255).astype(np.uint8)
    out = np.empty(mask.shape + (4,), np.uint8)
    out[..., 0], out[..., 1], out[..., 2], out[..., 3] = colour[0], colour[1], colour[2], a
    return Image.fromarray(out, "RGBA")


def svg_doc(logo, fill, title, two_tone=None):
    w, h = logo.w * U, logo.h * U
    paths = svg_paths(logo, U)
    body = []
    for name, d in paths.items():
        f = fill
        if two_tone and name in two_tone:
            f = two_tone[name]
        body.append(f'  <path id="{name}" fill="{f}" fill-rule="evenodd" d="{d}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(w)} {fmt(h)}" width="{fmt(w)}" height="{fmt(h)}">\n'
            f'  <title>{title}</title>\n' + "\n".join(body) + "\n</svg>\n")


def layered_svg(logo, title):
    w, h = logo.w * U, logo.h * U
    L = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(w)} {fmt(h)}" width="{fmt(w)}" height="{fmt(h)}">',
         f'  <title>{title} (layered for animation)</title>',
         '  <!-- Every part is its own named group. "film-strip" is the strip with its holes cut out, as normally shown.',
         '       The hidden group "extras-for-animation" holds the strip as a solid shape and every sprocket hole as its own',
         '       shape: show film-strip-solid, then animate the holes in the background colour (or use them as a matte)',
         '       to make them punch in one by one. Holes are numbered from the top of each column. -->',
         '  <g id="astris-logo" fill="#000000">']
    for name, o, hs in logo.polys(0, 0, logo.h * U):
        d = " ".join([path_d(o)] + [path_d(q) for q in hs])
        L.append(f'    <g id="{name}">')
        L.append(f'      <path id="{name}-shape" fill-rule="evenodd" d="{d}"/>')
        L.append('    </g>')
    L.append('  </g>')
    L.append('  <g id="extras-for-animation" display="none">')
    for part in logo.parts:
        if not part["holes"]:
            continue
        o = np.asarray(part["outer"]) * U
        L.append(f'    <path id="{part["name"]}-solid" fill="#000000" d="{path_d(o)}"/>')
        L.append('    <g id="sprocket-holes" fill="#ffffff">')
        for hname, grp in (("left", [q for q in part["holes"] if "left" in q["name"]]), ("right", [q for q in part["holes"] if "right" in q["name"]])):
            L.append(f'      <g id="holes-{hname}-column">')
            for q in grp:
                L.append(f'        <path id="{q["name"]}" d="{path_d(np.asarray(q["pts"]) * U)}"/>')
            L.append('      </g>')
        L.append('    </g>')
    L.append('  </g>')
    L.append('</svg>')
    return "\n".join(L) + "\n"


def pdf_doc(logo, path, colour, title):
    """True vector PDF: one filled path per part (even-odd), nothing else. 1 logo unit = 50 pt."""
    s = 50.0
    W, H = logo.w * s, logo.h * s
    c = pdfcanvas.Canvas(str(path), pagesize=(W, H))
    c.setTitle(title)
    c.setAuthor("ASTRIS PRODUCTIONS")
    c.setFillColorRGB(*[v / 255 for v in colour])
    for name, o, hs in logo.polys(0, 0, H):
        p = c.beginPath()
        for poly in [o] + hs:
            p.moveTo(poly[0][0], H - poly[0][1])
            for q in poly[1:]:
                p.lineTo(q[0], H - q[1])
            p.close()
        c.drawPath(p, stroke=0, fill=1, fillMode=0)          # 0 = even-odd
    c.showPage()
    c.save()


def build_version(key, folder, label):
    logo = Logo(key)
    base = LOGO_PACK / folder
    for sub in ("svg", "pdf", "png", "1-bit", "previews"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    stem = f"astris-logo-{key}"
    made = []
    # ---- vector
    (base / "svg" / f"{stem}-black.svg").write_text(svg_doc(logo, "#000000", f"ASTRIS logo, {label}, black"))
    (base / "svg" / f"{stem}-white.svg").write_text(svg_doc(logo, "#ffffff", f"ASTRIS logo, {label}, white"))
    (base / "svg" / f"{stem}-single-colour.svg").write_text(svg_doc(logo, "currentColor", f"ASTRIS logo, {label}, single colour (takes the colour of its surroundings; edit fill to taste)"))
    if key == "faithful":
        tone = logo.geo["tones"]["film-strip"]
        g = int(round(255 * tone))
        (base / "svg" / f"{stem}-two-tone-as-original.svg").write_text(
            svg_doc(logo, "#ffffff", f"ASTRIS logo, {label}, two-tone as in the original file (for dark backgrounds)",
                    two_tone={"film-strip": f"#{g:02x}{g:02x}{g:02x}"}))
    (base / f"{stem}-layered.svg").write_text(layered_svg(logo, f"ASTRIS logo, {label}"))
    pdf_doc(logo, base / "pdf" / f"{stem}-black.pdf", (0, 0, 0), f"ASTRIS logo, {label}, black")
    pdf_doc(logo, base / "pdf" / f"{stem}-white.pdf", (255, 255, 255), f"ASTRIS logo, {label}, white (on a transparent page)")
    # ---- PNG, transparent
    for n in SIZES:
        m = logo.tight(n)
        for cname, col in (("black", (0, 0, 0)), ("white", (255, 255, 255)), ("single-colour", NEUTRAL)):
            p = base / "png" / f"{stem}-{cname}-{n}.png"
            rgba(m, col).save(p, optimize=True)
            made.append(p)
        if n == 4096:
            # 1-bit: every pixel is fully black or fully white (and a transparent-background version)
            hard = m > 0.5
            Image.fromarray(np.where(hard, 0, 255).astype(np.uint8)).convert("1").save(base / "1-bit" / f"{stem}-1bit-black-on-white-4096.png", optimize=True)
            Image.fromarray(np.where(hard, 255, 0).astype(np.uint8)).convert("1").save(base / "1-bit" / f"{stem}-1bit-white-on-black-4096.png", optimize=True)
            pal = Image.fromarray(hard.astype(np.uint8), "P")
            pal.putpalette([255, 255, 255, 0, 0, 0])
            pal.save(base / "1-bit" / f"{stem}-1bit-black-on-transparent-4096.png", transparency=0, optimize=True)
        if n == 1024:
            hard = m > 0.5
            Image.fromarray(np.where(hard, 0, 255).astype(np.uint8)).convert("1").save(base / "1-bit" / f"{stem}-1bit-black-on-white-1024.png", optimize=True)
    # ---- previews
    for pname, bg, fg in (("on-dark", (17, 17, 17), (255, 255, 255)), ("on-light", (245, 245, 243), (0, 0, 0))):
        W, H = 2400, 1600
        lw = 1100
        m = logo.tight(lw)
        im = Image.new("RGB", (W, H), bg)
        im.paste(rgba(m, fg), ((W - m.shape[1]) // 2, (H - m.shape[0]) // 2), rgba(m, fg))
        im.save(base / "previews" / f"{stem}-{pname}-2400x1600.png", optimize=True)
    return logo


def small_size_sheet(logos):
    """Each version at 16-64 px: shown at real size and magnified 6x, on light and on dark."""
    sizes = [16, 24, 32, 48, 64]
    rows = [("FAITHFUL CLEAN", logos["faithful"]), ("GEOMETRIC PERFECT", logos["geometric"]), ("optional small-size mark (no holes)", logos["geometric-micro"])]
    Z = 6
    colw = [s * Z + 70 for s in sizes]
    W = 380 + sum(colw) + 60
    rowh = 64 * Z * 16 // 19 + 150
    top = 190
    half = top + len(rows) * rowh + 30
    sheet = Image.new("RGB", (W, half * 2 - 60), (245, 245, 243))
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, half - 30, W, half * 2], fill=(17, 17, 17))
    out_dir = LOGO_PACK / "small-size-test"
    (out_dir / "tiny-pngs").mkdir(parents=True, exist_ok=True)
    for block, (bg, fg, ink) in enumerate((((245, 245, 243), (0, 0, 0), (30, 30, 34)), ((17, 17, 17), (255, 255, 255), (235, 235, 238)))):
        y0 = block * (half - 30)
        if block == 0:
            d.text((40, 36), "Small-size test", font=font(46, 700), fill=ink)
            d.text((40, 100), "Each size is shown at its real size (small, left) and enlarged 6x so you can see every pixel.", font=font(22), fill=(110, 110, 118))
        x = 380
        for s, cw in zip(sizes, colw):
            d.text((x + 34, y0 + top - 44), f"{s} px", font=font(24, 700), fill=ink)
            x += cw
        for r, (label, logo) in enumerate(rows):
            yy = y0 + top + r * rowh
            d.text((40, yy + 40), label.split(" (")[0], font=font(24, 700), fill=ink)
            if "(" in label:
                d.text((40, yy + 74), "(" + label.split(" (")[1], font=font(20), fill=(120, 120, 128))
            x = 380
            for s, cw in zip(sizes, colw):
                m = logo.tight(s, ss=8)
                tile = rgba(m, fg)
                sheet.paste(tile, (x, yy + 6), tile)
                big = tile.resize((tile.width * Z, tile.height * Z), Image.NEAREST)
                sheet.paste(big, (x + 34, yy + 6), big)
                if block == 0:
                    tile.save(out_dir / "tiny-pngs" / f"astris-logo-{logo.version}-black-{s}.png", optimize=True)
                else:
                    tile.save(out_dir / "tiny-pngs" / f"astris-logo-{logo.version}-white-{s}.png", optimize=True)
                x += cw
    sheet.save(out_dir / "astris-logo-small-size-test.png", optimize=True)
    # the optional small-size mark as vector too
    micro = logos["geometric-micro"]
    (out_dir / "astris-logo-small-size-mark-black.svg").write_text(svg_doc(micro, "#000000", "ASTRIS logo, optional small-size mark (no sprocket holes), black"))
    (out_dir / "astris-logo-small-size-mark-white.svg").write_text(svg_doc(micro, "#ffffff", "ASTRIS logo, optional small-size mark (no sprocket holes), white"))
    (out_dir / "astris-logo-small-size-mark-single-colour.svg").write_text(svg_doc(micro, "currentColor", "ASTRIS logo, optional small-size mark, single colour"))


def main():
    logos = {}
    for key, folder, label in VERSIONS:
        logos[key] = build_version(key, folder, label)
        print("built", folder)
    logos["geometric-micro"] = Logo("geometric-micro")
    small_size_sheet(logos)
    print("built small-size-test")


if __name__ == "__main__":
    main()
