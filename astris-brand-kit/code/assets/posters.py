"""
Film posters: one per film in films.txt, in two sizes (A3 at 300 dpi = 3508 x 4961, and 2:3 digital = 4000 x 6000).
Four layouts take turns so a wall of posters doesn't repeat. Titles come from films.txt; taglines and credits are
clearly marked placeholders (nothing about your films is invented here).
"""
from engine import lockup as L
from engine import type as T
from engine.core import Art, save_jpg
from engine.extras import placeholder
from engine.paths import out
from engine.style import config, films, slug

SIZES = [("a3", 3508, 4961), ("2x3", 4000, 6000)]
CREDITS = "[PLACEHOLDER: CREDITS]\nwritten and directed by [NAME]   ·   produced by [NAME]   ·   starring [NAMES]\nmusic by [NAME]   ·   [RELEASE DATE]"


def title_block(art, lines, cx, cy, max_w, max_h, role="ink", line_gap=0.16, **kw):
    """Big stacked title, every line the same size, fitted to max_w x max_h and centred on (cx, cy)."""
    face = art.style.display
    size = min(T.fit_size(l, face, max_w, 0.01) for l in lines)
    cap = face.cap * size
    total = len(lines) * cap + (len(lines) - 1) * cap * line_gap
    if total > max_h:
        size *= max_h / total
        cap = face.cap * size
        total = len(lines) * cap + (len(lines) - 1) * cap * line_gap
    y = cy - total / 2
    for l in lines:
        art.text(l, cx, y + cap, size, tracking=0.01, anchor="ms", role=role, **kw)
        y += cap * (1 + line_gap)
    return cy - total / 2, cy + total / 2, size


def poster(style, title, note, variant, W, H):
    k = style.key
    scheme = {0: "main", 1: "dark", 2: "main", 3: "light"}[variant]
    art = Art(style, W, H, scheme=scheme, seed=f"{k}-poster-{slug(title)}-{W}")
    s = art.s
    cx = W / 2
    lines = title.upper().split()
    if len(lines) > 3:
        half = (len(lines) + 1) // 2
        lines = [" ".join(lines[:half]), " ".join(lines[half:])]
    tf = style.text_face(500)
    logo_role = "second" if (scheme == "dark" and k == "red") else "ink"
    presents = config()["brand"]["presents_line"]
    # ---- top: logo + "ASTRIS PRODUCTIONS presents"
    top = H * 0.068
    art.logo(cx, top, 130 * s, role=logo_role)
    art.text(presents.split(" presents")[0], cx, top + 128 * s, 42 * s, tracking=0.30, anchor="mm", shadow=False)
    art.text("presents", cx, top + 186 * s, 32 * s, face=tf, tracking=0.34, anchor="mm", shadow=False)
    # ---- the one focal point: the title
    if variant == 2:
        # a big disc with the title on it. Flat styles: the title is cut out of the disc.
        # Risograph: the disc is the second ink and the title overprints it, so the overlap goes deep violet-brown.
        r = W * 0.37
        cy = H * 0.19 + r
        role = "ink" if style.is_riso else "field"
        kw = dict(shadow=False, knockout=False) if style.is_riso else {}
        art.circle(cx, cy, r, role="second" if style.is_riso else "ink", size=r, wear=0.6)
        y0, y1, size = title_block(art, lines, cx, cy - (26 * s if note else 0), r * 1.50, r * 1.0, role=role, **kw)
        if note:
            art.text(f"({note})", cx, y1 + 84 * s, 42 * s, face=tf, tracking=0.22, anchor="mm", role=role, **kw)
        end_y = cy + r
    else:
        cy = H * 0.445
        y0, y1, size = title_block(art, lines, cx, cy, W * 0.80, H * 0.34)
        end_y = y1
        if variant == 3 and not style.is_riso:
            # a bar of the supporting colour under the title (never coloured type on a light field for the yellow style)
            art.rect(cx - W * 0.40, y1 + 64 * s, cx + W * 0.40, y1 + 64 * s + 32 * s, role="second" if k == "yellow" else "ink", wear=0.5)
            end_y = y1 + 96 * s
        if note:
            art.text(f"({note})", cx, end_y + 96 * s, 44 * s, face=tf, tracking=0.22, anchor="mm", shadow=False)
            end_y += 130 * s
    # ---- placeholders: tagline + credits (clearly marked: nothing about the film is invented)
    credits_y = H * 0.815
    pw, ph = W * 0.62, 104 * s
    ty = min(max(end_y + 70 * s, H * 0.70), credits_y - ph - 40 * s)
    placeholder(art, cx - pw / 2, ty, cx + pw / 2, ty + ph, "[PLACEHOLDER: THE FILM'S TAGLINE]", text_size=32 * s)
    cw = W * 0.80
    placeholder(art, cx - cw / 2, credits_y, cx + cw / 2, credits_y + 232 * s, CREDITS, text_size=29 * s)
    # ---- foot: the name
    art.text(config()["brand"]["name_lowercase"], cx, H * 0.962, 56 * s, tracking=L.TRACK_MAIN, anchor="mm", shadow=False)
    return art.render()


def build(style):
    k = style.key
    d = out(k, "paper", "posters")
    made = []
    for i, (title, note) in enumerate(films()):
        for tag, W, H in SIZES:
            img = poster(style, title, note, i % 4, W, H)
            p = save_jpg(img, d / f"astris-{k}-poster-{i + 1:02d}-{slug(title)}-{tag}-{W}x{H}.jpg", 90, dpi=300 if tag == "a3" else None)
            made.append(f"{p.name}  {p.stat().st_size / 1e6:.1f} MB")
    return made
