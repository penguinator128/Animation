"""
The ASTRIS lockups, drawn the same way in every asset and every style.

    name_line(art, cx, y, width)            "astris productions." with the tiny supporting line under it
    stacked(art, cx, cy, width)             ASTRIS big, PRODUCTIONS small and tracked out to the same width
    vertical(art, cx, cy, logo_h)           logo above the stacked wordmark
    horizontal(art, cx, cy, logo_h)         logo beside the stacked wordmark
All return the box they occupy: (x0, y0, x1, y1).
"""
from . import type as T
from .style import config

TRACK_MAIN = 0.012
TRACK_TAG = 0.16


def brand():
    return config()["brand"]


def name_line(art, cx, y_mid, width, tagline=True, role="ink", tag_role=None, text=None, tag_text=None, tag_scale=0.20):
    """Lowercase name with a full stop, centred on (cx, y_mid = middle of the x-height), `width` px wide."""
    face = art.style.display
    main = text or brand()["name_lowercase"]
    size = T.fit_size(main, face, width, TRACK_MAIN)
    x0, yb, w = art.text(main, cx, y_mid, size, tracking=TRACK_MAIN, anchor="mm", role=role)
    top, bottom = yb - face.asc * 0.80 * size, yb + face.desc * 0.55 * size
    if tagline:
        tsize = size * tag_scale
        ty = yb + size * 0.36
        art.text(tag_text or art.style.tagline, cx, ty, tsize, tracking=TRACK_TAG, anchor="mt", role=tag_role or role, shadow=False)
        bottom = ty + face.cap * tsize * 1.05
    return (cx - w / 2, top, cx + w / 2, bottom), size


def stacked_sizes(face, width, ratio=0.27):
    b = brand()
    s1 = T.fit_size(b["first_word"], face, width, 0.02)
    s2 = s1 * ratio
    n = len(b["second_word"])
    w0 = T.text_width(b["second_word"], face, s2, 0.0)
    track = max(0.0, (width - w0) / ((n - 1) * s2))
    return s1, s2, track


def stacked(art, cx, cy, width, role="ink", second_role=None, ratio=0.27, gap=0.20):
    """ASTRIS over PRODUCTIONS, centred on (cx, cy). Returns (box, size of the big word)."""
    face = art.style.display
    b = brand()
    s1, s2, track = stacked_sizes(face, width, ratio)
    cap1, cap2 = face.cap * s1, face.cap * s2
    g = gap * cap1
    total = cap1 + g + cap2
    top = cy - total / 2
    art.text(b["first_word"], cx, top + cap1, s1, tracking=0.02, anchor="ms", role=role)
    art.text(b["second_word"], cx, top + total, s2, tracking=track, anchor="ms", role=second_role or role, shadow=False)
    return (cx - width / 2, top, cx + width / 2, top + total), s1


def vertical(art, cx, cy, logo_h, role="ink", logo_role=None, gap=0.26, word_ratio=1.0, second_role=None):
    """Logo above the stacked wordmark, the whole group centred on (cx, cy)."""
    face = art.style.display
    lw = logo_h * art.style.logo.aspect
    width = lw * word_ratio
    s1, s2, track = stacked_sizes(face, width)
    words_h = face.cap * s1 * 1.20 + face.cap * s2
    g = gap * logo_h
    total = logo_h + g + words_h
    top = cy - total / 2
    art.logo(cx, top + logo_h / 2, logo_h, role=logo_role or role)
    box, _ = stacked(art, cx, top + logo_h + g + words_h / 2, width, role=role, second_role=second_role)
    return (cx - max(lw, width) / 2, top, cx + max(lw, width) / 2, top + total)


def horizontal(art, cx, cy, logo_h, role="ink", logo_role=None, gap=0.34, second_role=None, lowercase=False, tagline=False):
    """Logo on the left, wordmark on the right, the group centred on (cx, cy)."""
    face = art.style.display
    lw = logo_h * art.style.logo.aspect
    g = gap * logo_h
    if lowercase:
        main = brand()["name_lowercase"]
        size = logo_h * 0.52
        ww = T.text_width(main, face, size, TRACK_MAIN)
        x0 = cx - (lw + g + ww) / 2
        art.logo(x0 + lw / 2, cy, logo_h, role=logo_role or role)
        y_mid = cy - (size * 0.10 if tagline else 0)
        name_line(art, x0 + lw + g + ww / 2, y_mid, ww, tagline=tagline, role=role, tag_role=second_role, tag_scale=0.24)
        return (x0, cy - logo_h / 2, x0 + lw + g + ww, cy + logo_h / 2)
    cap_total = logo_h * 0.86
    s1 = cap_total / (face.cap * (1 + 0.20 + 0.27))
    ww = T.text_width(brand()["first_word"], face, s1, 0.02)
    x0 = cx - (lw + g + ww) / 2
    art.logo(x0 + lw / 2, cy, logo_h, role=logo_role or role)
    stacked(art, x0 + lw + g + ww / 2, cy, ww, role=role, second_role=second_role)
    return (x0, cy - logo_h / 2, x0 + lw + g + ww, cy + logo_h / 2)
