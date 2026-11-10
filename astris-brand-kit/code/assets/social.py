"""
Social templates in a style: YouTube thumbnail templates, Instagram highlight covers, post templates and story templates.
Everything that is yours to fill in is a dashed box with a [LABEL].
"""
from engine import lockup as L
from engine import type as T
from engine.core import Art, save_jpg, save_png
from engine.extras import ICONS, icon_mask, placeholder
from engine.paths import out
from engine.style import config, slug


# ----------------------------------------------------------------------------------------------------
# YouTube thumbnails, 1280 x 720
# ----------------------------------------------------------------------------------------------------
def thumbnail(style, layout):
    W, H = 1280, 720
    art = Art(style, W, H, scale=1.0, seed=f"{style.key}-thumb-{layout}", scheme="dark" if layout == "minimal" else "main")
    face = style.display
    if layout == "big-title":
        art.text("[BIG TITLE]", W / 2, 300, 250, anchor="mm")
        art.text("[one short line under it]", W / 2, 500, 44, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
        art.logo(92, 84, 76)
    elif layout == "subject-and-title":
        placeholder(art, 60, 60, 600, 660, "[YOUR SUBJECT]\ndrop a cut-out photo here", fill=0.10)
        s = T.fit_size("[TITLE]", face, 520)
        art.text("[TITLE]", 920, 300, min(s, 210), anchor="mm")
        art.text("[SECOND LINE]", 920, 450, 74, anchor="mm", tracking=0.04, shadow=False)
        art.logo(1190, 84, 70)
    else:   # minimal
        placeholder(art, 60, 60, 1220, 520, "[A STILL FROM THE FILM]", fill=0.08)
        role = "second" if style.key == "red" else "ink"
        art.text("[film title.]", 70, 618, 96, anchor="lm")
        art.logo(1040, 620, 76, role=role)
    return art.render()


# ----------------------------------------------------------------------------------------------------
# Instagram highlight covers, 1080 x 1920 (the icon sits inside the circle Instagram crops to)
# ----------------------------------------------------------------------------------------------------
def highlight(style, name):
    W, H = 1080, 1920
    art = Art(style, W, H, scale=1.0, seed=f"{style.key}-hl-{slug(name)}")
    px = 330
    m = icon_mask(name, px, face=style.display)
    art.add(m, (W - px) / 2, H / 2 - px / 2 - 34, size=260)
    art.text(name.lower() + ".", W / 2, H / 2 + px / 2 + 34, 46, tracking=0.14, anchor="mm", shadow=False)
    return art.render()


# ----------------------------------------------------------------------------------------------------
# Instagram posts (1080 x 1350) and stories (1080 x 1920)
# ----------------------------------------------------------------------------------------------------
def post(style, n):
    W, H = 1080, 1350
    scheme = {1: "main", 2: "main", 3: "dark", 4: "light", 5: "main", 6: "dark"}[n]
    art = Art(style, W, H, scale=1.0, seed=f"{style.key}-post-{n}", scheme=scheme)
    cx = W / 2
    logo_role = "second" if (scheme == "dark" and style.key == "red") else "ink"
    if n == 1:      # new film
        art.text("new film.", cx, 250, 64, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
        art.text("[FILM TITLE]", cx, 640, T.fit_size("[FILM TITLE]", style.display, 900), anchor="mm")
        art.text("[date or one short line]", cx, 900, 44, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
        art.logo(cx, 1160, 130)
    elif n == 2:    # a line worth sharing
        art.text("“", cx, 330, 300, anchor="mm", shadow=False)
        placeholder(art, 120, 440, 960, 900, "[A LINE FROM THE FILM,\nOR SOMETHING YOU WANT TO SAY]", text_size=40)
        art.text("[who said it]", cx, 990, 40, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
        art.logo(cx, 1180, 110)
    elif n == 3:    # behind the scenes
        placeholder(art, 70, 70, 1010, 1010, "[BEHIND-THE-SCENES PHOTO]", fill=0.08)
        art.text("behind the scenes.", 80, 1130, 84, anchor="lm")
        art.text("[film title]", 84, 1232, 40, tracking=L.TRACK_TAG, anchor="lm", shadow=False)
        art.logo(940, 1180, 120, role=logo_role)
    elif n == 4:    # out now
        art.text("out now.", cx, 520, T.fit_size("out now.", style.display, 820), anchor="mm")
        art.text("[FILM TITLE]", cx, 800, 80, tracking=0.04, anchor="mm", shadow=False)
        art.text("[where to watch it]", cx, 900, 40, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
        art.logo(cx, 1140, 120)
    elif n == 5:    # the brand card
        L.vertical(art, cx, H / 2 - 20, 420)
        art.text(style.tagline, cx, H - 150, 46, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
    else:           # thank you
        art.text("thank you", cx, 500, T.fit_size("thank you", style.display, 800), anchor="mm")
        art.text("for watching.", cx, 730, T.fit_size("for watching.", style.display, 800), anchor="mm")
        art.text("[cast and crew, or a short note]", cx, 930, 38, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
        art.logo(cx, 1150, 120, role=logo_role)
    return art.render()


def story(style, n):
    W, H = 1080, 1920
    scheme = {1: "main", 2: "dark", 3: "main", 4: "light"}[n]
    art = Art(style, W, H, scale=1.0, seed=f"{style.key}-story-{n}", scheme=scheme)
    cx = W / 2
    logo_role = "second" if (scheme == "dark" and style.key == "red") else "ink"
    # keep the top 250 px and bottom 340 px clear: Instagram's own buttons sit there
    if n == 1:      # new film
        art.logo(cx, 380, 120)
        art.text("new film.", cx, 560, 110, anchor="mm")
        placeholder(art, 90, 680, 990, 1186, "[POSTER OR STILL, 16:9]", fill=0.08)
        art.text("[FILM TITLE]", cx, 1300, 90, tracking=0.03, anchor="mm", shadow=False)
        art.text("[where to watch it]", cx, 1410, 40, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
    elif n == 2:    # coming soon
        art.text("coming", cx, 720, T.fit_size("coming", style.display, 760), anchor="mm")
        art.text("soon.", cx, 1010, T.fit_size("soon.", style.display, 760) * 0.8, anchor="mm")
        art.text("[FILM TITLE]  ·  [DATE]", cx, 1260, 44, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
        art.logo(cx, 1440, 120, role=logo_role)
    elif n == 3:    # behind the scenes
        art.text("behind the scenes.", cx, 340, 86, anchor="mm")
        placeholder(art, 90, 450, 990, 1450, "[PHOTO OR VIDEO]", fill=0.08)
        art.logo(cx, 1530, 96)
    else:           # questions
        art.text("ask us", cx, 560, T.fit_size("ask us", style.display, 700), anchor="mm")
        art.text("anything.", cx, 820, T.fit_size("anything.", style.display, 700), anchor="mm")
        placeholder(art, 150, 1010, 930, 1290, "[PUT THE QUESTION STICKER HERE]")
        art.logo(cx, 1470, 110)
    return art.render()


def build(style):
    k = style.key
    n = 0
    d = out(k, "social", "thumbnails")
    for layout in ("big-title", "subject-and-title", "minimal"):
        img = thumbnail(style, layout)
        save_png(img, d / f"astris-{k}-thumbnail-{layout}-master-1280x720.png")
        p = save_jpg(img, d / f"astris-{k}-thumbnail-{layout}-1280x720.jpg", 92)
        assert p.stat().st_size < 2e6
        n += 2
    d = out(k, "social", "instagram-highlight-covers")
    for i, name in enumerate(config()["instagram_highlights"], 1):
        save_png(highlight(style, name), d / f"astris-{k}-highlight-{i:02d}-{slug(name)}-1080x1920.png")
        n += 1
    d = out(k, "social", "instagram-posts")
    names = {1: "new-film", 2: "quote", 3: "behind-the-scenes", 4: "out-now", 5: "brand-card", 6: "thank-you"}
    for i in range(1, 7):
        save_png(post(style, i), d / f"astris-{k}-post-{i:02d}-{names[i]}-1080x1350.png")
        n += 1
    d = out(k, "social", "instagram-stories")
    names = {1: "new-film", 2: "coming-soon", 3: "behind-the-scenes", 4: "ask-us-anything"}
    for i in range(1, 5):
        save_png(story(style, i), d / f"astris-{k}-story-{i:02d}-{names[i]}-1080x1920.png")
        n += 1
    return [f"{n} social files"]
