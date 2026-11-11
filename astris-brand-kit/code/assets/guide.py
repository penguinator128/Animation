"""
The brand guide for a style: A4 landscape PDF + a PNG of every page.
Build it last: the mood board and a few pages use pictures the other steps make.

Usage: python3 code/build.py guide [--style red]
"""
import subprocess

import numpy as np
from PIL import Image

from engine import lockup as L
from engine import type as T
from engine.core import Art, hex_rgb
from engine.paths import KIT, STYLE_DIRS, SUB, out
from engine.pdf import MM, Doc, rgb as pdf_rgb, to_png_pages
from engine.style import config

PW, PH = 297.0, 210.0
BW = 74.0                       # the colour band down the left of every page
X0, X1 = 92.0, 281.0            # the text column
CW = X1 - X0
PAGES = ["cover", "our story", "how we sound", "mood", "colour", "type", "grain", "the logo", "layout", "motion and sound", "in premiere", "where things are"]

SOUND = {"red": "warm analogue thuds, soft vinyl crackle, gentle tape hiss and a friendly low chime",
         "yellow": "clapperboard snaps, finger clicks, a sunny marimba pluck and a light chime",
         "wildcard": "print-press thunks, paper slaps, rubber stamps and a soft mallet chime"}
MOOD = {"red": "warm  ·  analogue  ·  hand-pressed  ·  friendly  ·  a little funny",
        "yellow": "sunny  ·  bright  ·  confident  ·  clapperboard  ·  friendly",
        "wildcard": "handmade  ·  two inks  ·  paper  ·  zine  ·  friendly"}


def tones(style):
    h, k = style.hex, style.key
    return dict(page=h["light"], ink=h["dark"], head=h["dark"] if k == "yellow" else h["signature"], accent=h["signature"],
                rule=h.get("second", h["signature"]), soft={"red": "#7A645C", "yellow": "#6A655C", "wildcard": "#5A6288"}[k],
                tile={"red": "#EAD3C8", "yellow": "#E6DDCB", "wildcard": "#E5D9C2"}[k])


def cmyk(hexcol):
    r, g, b = hex_rgb(hexcol)
    k = 1 - max(r, g, b)
    if k >= 0.999:
        return 0, 0, 0, 100
    return tuple(int(round(v * 100)) for v in ((1 - r - k) / (1 - k), (1 - g - k) / (1 - k), (1 - b - k) / (1 - k), k))


def contrast(a, b):
    def lum(hx):
        c = np.asarray(hex_rgb(hx), np.float64)
        c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        return float(c @ [0.2126, 0.7152, 0.0722])
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def thumb(path, max_px=1100):
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    im = im.convert("RGB")
    im.thumbnail((max_px, max_px), Image.LANCZOS)
    return im


def frame_of(path, t, w=960):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={w}:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    h = len(raw) // (w * 3)
    return Image.fromarray(np.frombuffer(raw, np.uint8).reshape(h, w, 3))


def band(style, n, title):
    """The colour band for a page: number, section name, small logo. Drawn with the same ink and grain as everything else."""
    W, H = 583, 1654
    k = style.key
    art = Art(style, W, H, scheme="dark" if k == "wildcard" else "main", scale=1.0, seed=f"{k}-guide-band-{n}")
    art.text(f"{n:02d}", 58, 190, 170, anchor="ls", shadow=False)
    size = min(118.0, T.fit_size(title + ".", style.display, 467, L.TRACK_MAIN))
    words = (title + ".").split(" ")
    if len(title) > 9 and len(words) > 1:
        half = (len(words) + 1) // 2
        lines = [" ".join(words[:half]), " ".join(words[half:])]
        size = min(118.0, min(T.fit_size(l, style.display, 467, L.TRACK_MAIN) for l in lines))
    else:
        lines = [title + "."]
    y = H - 300 - (len(lines) - 1) * size * 0.98
    for l in lines:
        art.text(l, 58, y, size, tracking=L.TRACK_MAIN, anchor="ls", shadow=False)
        y += size * 0.98
    art.logo(58 + 84 * style.logo.aspect / 2, H - 150, 84)
    return art.render()


class Guide:
    def __init__(self, style):
        self.st, self.k, self.t = style, style.key, tones(style)
        self.cfg = config()
        self.tf = lambda w=400: f"{style.text_family}-{w}"
        self.base = STYLE_DIRS[self.k]
        d = out(self.k, "guide")
        self.path = d / f"astris-{self.k}-brand-guide-a4-landscape.pdf"
        self.doc = Doc(self.path, PW, PH, title=f"ASTRIS PRODUCTIONS brand guide: style {style.number}, {style.name}")
        self.n = 0

    # ---- page furniture ---------------------------------------------------------------------------------
    def start(self, title):
        doc, t = self.doc, self.t
        if self.n:
            doc.page()
        self.n += 1
        doc.fill(t["page"])
        doc.image(band(self.st, self.n, title), 0, 0, BW, PH, quality=88, key=f"band{self.n}")
        doc.text(X1, 14, f"ASTRIS PRODUCTIONS   ·   BRAND GUIDE   ·   STYLE {self.st.number}: {self.st.name.upper()}", self.tf(500), 6.2, t["soft"], anchor="r", tracking=0.16)
        doc.text(X1, PH - 10, f"{self.n:02d} / {len(PAGES):02d}", self.tf(500), 6.2, t["soft"], anchor="r", tracking=0.16)

    def h1(self, s, y=34.0, x=X0):
        self.doc.text(x, y, s, "anton-400", 30, self.t["head"], tracking=0.01)
        return y + 9

    def h2(self, s, x, y, size=13):
        self.doc.text(x, y, s, "anton-400", size, self.t["head"], tracking=0.01)
        return y + size * 0.50

    def lab(self, s, x, y, colour=None, anchor="l"):
        self.doc.text(x, y, s.upper(), self.tf(700), 6.2, colour or self.t["soft"], tracking=0.16, anchor=anchor)
        return y + 5

    def p(self, s, x, y, w, size=9.2, colour=None, weight=400, leading=1.5, max_lines=None):
        return self.doc.para(x, y, s, self.tf(weight), size, colour or self.t["ink"], w, leading=leading, max_lines=max_lines)

    def bullets(self, items, x, y, w, size=9.0, gap=1.6):
        for it in items:
            self.doc.circle(x + 1.1, y - 1.1, 0.75, self.t["rule"])
            y = self.p(it, x + 5, y, w - 5, size) + gap
        return y

    def rule(self, x0, y, x1, width=0.6):
        self.doc.line(x0, y, x1, y, self.t["rule"], width)

    def pic(self, im, x, y, w, h=None, key=None, quality=88):
        return self.doc.image(im, x, y, w, h, quality=quality, key=key or f"p{self.n}-{x:.0f}-{y:.0f}")

    def f(self, *parts):
        return self.base.joinpath(*parts)

    # ---- pages ----------------------------------------------------------------------------------------------
    def cover(self):
        doc, st, k = self.doc, self.st, self.k
        self.n += 1
        W, H = 2339, 1654

        def draw(art):
            L.vertical(art, W * 0.5, H * 0.43, 430)
            art.tag = "main"
            art.text("brand guide.", W / 2, H * 0.800, 120, anchor="mm")
            art.text(f"style {st.number}: {st.name.lower()}.   {st.tagline}", W / 2, H * 0.885, 34, tracking=L.TRACK_TAG, anchor="mm", shadow=False)
        art = Art(st, W, H, seed=f"{k}-guide-cover")
        draw(art)
        doc.image(art.render(), 0, 0, PW, PH, quality=90, key="cover")

    def story(self):
        b, p = self.cfg["brand"], self.cfg["person"]
        self.start("our story")
        y = self.h1("our story.")
        y = self.lab("this page is yours to write", X0, y + 6)
        y = self.p(b["about_long"], X0, y + 2, 118, size=11) + 6
        y = self.lab("the short version", X0, y + 2)
        y = self.p(b["about_short"], X0, y + 2, 118, size=11) + 8
        self.rule(X0, y, X0 + 118)
        y += 8
        for lab, val in (("Founded", "[YEAR]"), ("Based in", p["location"]), ("We make", "[SHORT FILMS / DOCUMENTARIES / ...]"), ("Who we are", "[NAMES AND ROLES]")):
            self.lab(lab, X0, y)
            self.doc.text(X0 + 30, y, val, self.tf(500), 10, self.t["ink"])
            y += 8
        x = X0 + 130
        self.doc.rect(x, 44, X1 - x, 118, colour=self.t["tile"], radius=3)
        yy = self.lab("three prompts to get you going", x + 7, 55)
        yy = self.bullets(["How did Astris start? One real moment is better than a mission statement.",
                           "What do you care about when you make a film? Say it the way you would to a friend.",
                           "What are you making right now?"], x + 7, yy + 3, X1 - x - 14, size=9.2, gap=2.4)
        self.lab("one rule", x + 7, yy + 5)
        self.p("Only true things. No awards, festivals, quotes or numbers unless they are real and you can point to them.", x + 7, yy + 11, X1 - x - 14, size=9.2)
        self.p("Fill these in once in brand-config.json. The press kit and the website preview pick them up from there.", X0, 186, CW, size=8, colour=self.t["soft"])

    def voice(self):
        t = self.t
        self.start("how we sound")
        y = self.h1("how we sound.")
        y = self.p("ASTRIS talks like a friend who is glad you came. Warm first, clear second, funny third.", X0, y + 5, CW, size=11.5, weight=500) + 4
        cols = [("welcoming.", "Talk to one person, not a crowd. Say hello before anything else."),
                ("warm.", "Plain words and short sentences. If it sounds like a press release, write it again."),
                ("a little funny.", "A small smile, never a joke at someone's expense. One wink a page is plenty."),
                ("honest.", "No hype and nothing made up. If we don't know yet, we say so.")]
        cw = (CW - 3 * 5) / 4
        for i, (hd, tx) in enumerate(cols):
            x = X0 + i * (cw + 5)
            self.h2(hd, x, y + 8, 15)
            self.p(tx, x, y + 15, cw, size=8.6)
        y += 44
        self.rule(X0, y, X1)
        half = (CW - 8) / 2
        self.lab("say it like this", X0, y + 8)
        self.lab("not like this", X0 + half + 8, y + 8)
        rows = [("new film out friday. bring snacks.", "DON'T MISS OUR EPIC NEW RELEASE!!!"),
                ("thanks for watching. stay for the credits.", "Smash that like button and hit the bell."),
                ("we're still editing. it'll be worth it.", "Release date TBA due to post-production delays.")]
        yy = y + 16
        for good, bad in rows:
            self.doc.text(X0, yy, good, "anton-400", 12.5, t["ink"], tracking=0.01)
            self.doc.text(X0 + half + 8, yy, bad, self.tf(400), 9.5, t["soft"])
            w = self.doc.width(bad, self.tf(400), 9.5)
            self.doc.line(X0 + half + 8, yy - 1.2, X0 + half + 8 + w, yy - 1.2, t["soft"], 0.4)
            yy += 9
        yy += 2
        self.rule(X0, yy, X1)
        self.lab("small rules", X0, yy + 8)
        self.bullets(["The name and the supporting line are lowercase and end with a full stop: astris productions.",
                      "No exclamation marks in headlines. The full stop does the work.",
                      "We invite people in. We never nag them to press buttons."], X0, yy + 14, half, size=8.6, gap=1.2)
        self.lab("supporting lines (this style uses the one in bold)", X0 + half + 8, yy + 8)
        tl = self.cfg["taglines"]
        for i, line in enumerate(tl):
            cx = X0 + half + 8 + (i % 2) * (half / 2)
            cy = yy + 14 + (i // 2) * 4.9
            on = line == self.st.tagline
            self.doc.text(cx, cy, line, self.tf(700 if on else 400), 8.4, t["ink"] if on else t["soft"])

    def mood(self):
        k = self.k
        self.start("mood")
        self.h1("mood.")
        gap = 4.0
        h1 = (CW - gap) / (16 / 9 + 1)
        y = 42.0
        self.pic(thumb(self.f(SUB["social"], "banner", f"astris-{k}-banner-a-2560x1440.png")), X0, y, h1 * 16 / 9, h1, "mb1")
        self.pic(thumb(self.f(SUB["social"], "profile", f"astris-{k}-profile-800x800.png"), 800), X0 + h1 * 16 / 9 + gap, y, h1, h1, "mb2")
        y2 = y + h1 + gap
        posters = sorted(self.f(SUB["paper"], "posters").glob("*-a3-*.jpg"))
        covers = sorted(self.f(SUB["social"], "instagram-highlight-covers").glob("*.png"))
        ratios = [3508 / 4961, 1.5, 1080 / 1920]
        h2 = (CW - 2 * gap) / sum(ratios)
        x = X0
        for im, r, key in ((thumb(posters[0], 900), ratios[0], "mb3"), (thumb(self.f(SUB["merch"], "mock-ups", f"astris-{k}-mockup-tshirt-illustration.jpg")), ratios[1], "mb4"),
                           (thumb(covers[0], 800), ratios[2], "mb5")):
            self.pic(im, x, y2, h2 * r, h2, key)
            x += h2 * r + gap
        yb = y2 + h2 + 9
        self.doc.text(X0, yb, MOOD[k], "anton-400", 13, self.t["head"], tracking=0.02)
        self.p(f"The feeling: {self.st.cfg['feel']}. Every picture on this page is a real file from this kit.", X0, yb + 7, CW, size=8.2, colour=self.t["soft"])

    def colour(self):
        st, t, doc = self.st, self.t, self.doc
        self.start("colour")
        y = self.h1("colour.")
        keys = list(st.hex)
        prop = st.cfg.get("proportions", {})
        n = len(keys)
        gap = 5.0
        sw = (CW - (n - 1) * gap) / n
        ys = y + 6
        for i, key in enumerate(keys):
            x = X0 + i * (sw + gap)
            hx = st.hex[key]
            doc.rect(x, ys, sw, 44, colour=hx, radius=2.5, stroke="#00000022" if False else None)
            if key == "light":
                doc.rect(x, ys, sw, 44, stroke=t["soft"], width=0.3, radius=2.5)
            dark_text = contrast(hx, "#FFFFFF") < 3
            col = st.hex["dark"] if dark_text else "#FFFFFF"
            doc.text(x + 4, ys + 38, st.colour_names[key], "anton-400", 11, col, tracking=0.01)
            r, g, b = [int(round(v * 255)) for v in hex_rgb(hx)]
            c, m, yv, kk = cmyk(hx)
            yy = ys + 51
            for lab, val in (("HEX", hx.upper()), ("RGB", f"{r}  {g}  {b}"), ("CMYK", f"{c}  {m}  {yv}  {kk}"), ("SHARE", f"about {prop.get(key, '?')} %")):
                self.lab(lab, x, yy)
                doc.text(x + 14, yy, val, self.tf(500), 8.4, t["ink"])
                yy += 5.2
        yb = ys + 78
        self.lab("how much of each", X0, yb)
        x = X0
        for key in sorted(keys, key=lambda q: -prop.get(q, 0)):
            w = CW * prop.get(key, 0) / 100.0
            doc.rect(x, yb + 3, w, 9, colour=st.hex[key])
            x += w
        doc.rect(X0, yb + 3, CW, 9, stroke=t["soft"], width=0.3)
        yb += 22
        half = (CW - 8) / 2
        self.lab("pairs that read well (contrast, higher is easier to read)", X0, yb)
        pairs = {"red": [("light", "signature"), ("light", "dark"), ("signature", "light"), ("dark", "light")],
                 "yellow": [("dark", "signature"), ("signature", "dark"), ("dark", "light"), ("light", "dark")],
                 "wildcard": [("signature", "light"), ("light", "signature"), ("dark", "light"), ("light", "dark")]}[self.k]
        px = X0
        pw_ = (half - 9) / 4
        for fg, bg in pairs:
            doc.rect(px, yb + 3, pw_, 15, colour=st.hex[bg], radius=1.5, stroke=t["soft"], width=0.25)
            doc.text(px + pw_ / 2, yb + 12.4, "Aa", "anton-400", 15, st.hex[fg], anchor="m")
            doc.text(px + pw_ / 2, yb + 22.5, f"{contrast(st.hex[fg], st.hex[bg]):.1f} : 1", self.tf(500), 7, t["soft"], anchor="m")
            px += pw_ + 3
        rules = {"red": ["Red is the field. Cream is the lettering. Warm black is for small type and dark versions.",
                         "Use the cream, not pure white: white on this red looks cold and cheap.",
                         "One red only. No tints, no gradients, no second accent colour."],
                 "yellow": ["Yellow is the field. Near-black is the lettering.",
                            "Never put yellow lettering on white or on the off-white. It disappears. Yellow type only ever sits on black.",
                            "The off-white is for paper and quiet backgrounds, always with black type."],
                 "wildcard": ["Cream paper is the field. Blue is the lettering. Coral sits behind it as a soft offset shadow.",
                              "Two inks only. Where they overlap you get a deep violet-brown: let it happen, don't correct it.",
                              "The blue-black is for small type only. Coral is never used for body text."]}[self.k]
        self.lab("rules", X0 + half + 8, yb)
        self.bullets(rules, X0 + half + 8, yb + 7, half, size=8.6, gap=1.2)
        self.p("CMYK values are worked out from the screen colours as a starting point. Ask your printer for a proof before a big run.", X0, 190, CW, size=7.4, colour=t["soft"])

    def type_(self):
        st, t, doc = self.st, self.t, self.doc
        text_name = {"dm-sans": "DM Sans", "inter": "Inter", "space-grotesk": "Space Grotesk"}[st.text_family]
        self.start("type")
        y = self.h1("type.")
        # the lockup, annotated
        ys = y + 4
        doc.rect(X0, ys, CW, 46, colour=t["tile"], radius=3)
        name = self.cfg["brand"]["name_lowercase"]
        size = 36.0
        w = doc.width(name, "anton-400", size, 0.012)
        cx = X0 + CW * 0.33
        doc.text(cx, ys + 26, name, "anton-400", size, t["ink"], anchor="m", tracking=0.012)
        doc.text(cx, ys + 34.5, st.tagline, "anton-400", size * 0.20, t["ink"], anchor="m", tracking=0.16)
        ax = X0 + CW * 0.70
        for yy, hd, tx in ((ys + 12, "the main line", "Anton, lowercase, ends with a full stop. Tracking +12."), (ys + 29, "the supporting line", "Anton at one fifth of the main size. Tracking +160. Centred under it.")):
            self.lab(hd, ax, yy)
            self.p(tx, ax, yy + 5, X1 - ax - 5, size=8.2)
        doc.line(cx + w / 2 + 3, ys + 19, ax - 3, ys + 11, t["rule"], 0.5)
        doc.line(cx + doc.width(st.tagline, "anton-400", size * 0.2, 0.16) / 2 + 3, ys + 33.5, ax - 3, ys + 28, t["rule"], 0.5)
        yt = ys + 55
        self.lab("the family", X0, yt)
        rows = [("Display", "Anton Regular", "anton-400", 17, "Names, titles, big friendly lines. Never for paragraphs."),
                ("Labels", f"{text_name} Bold, capitals", self.tf(700), 8.5, "Small labels and buttons. Tracking +120 to +160."),
                ("Reading", f"{text_name} Regular", self.tf(400), 10.5, "Anything longer than a line: captions, credits, emails."),
                ("Emphasis", f"{text_name} Medium", self.tf(500), 10.5, "A name inside a sentence, or a line that matters.")]
        yy = yt + 4
        for role, fname, face, sz, use in rows:
            doc.line(X0, yy, X1, yy, t["soft"], 0.25)
            self.lab(role, X0, yy + 7)
            doc.text(X0 + 24, yy + 7.6, fname.upper() if role == "Labels" else fname, face, sz, t["ink"], tracking=0.14 if role == "Labels" else 0.0)
            self.p(use, X0 + 100, yy + 7, CW - 100, size=8.4)
            yy += 11.5
        doc.line(X0, yy, X1, yy, t["soft"], 0.25)
        yy += 7
        half = (CW - 8) / 2
        self.lab("sizes that work together", X0, yy)
        self.bullets(["Supporting line = main line x 0.20.", "PRODUCTIONS under ASTRIS = 0.27 of its size, tracked out to the same width.",
                      "On a 1920 x 1080 title: main line about 170 px, supporting line about 34 px."], X0, yy + 6, half, size=8.4, gap=0.8)
        self.lab("getting the fonts", X0 + half + 8, yy)
        self.bullets(["Both are free for commercial use (SIL Open Font License). The files are in code/fonts, with their licences.",
                      "On Creative Cloud? Look in Adobe Fonts first: fonts you activate there show up in Premiere and Photoshop by themselves.",
                      "Full names, weights, sources and stand-ins: fonts.md at the top of the kit."], X0 + half + 8, yy + 6, half, size=8.4, gap=0.8)

    def grain(self):
        st, t, k = self.st, self.t, self.k
        self.start("grain")
        y = self.h1("grain.")
        y = self.p("Every picture in this style has fine, even film grain, and lettering that looks pressed on with ink. It is what makes a flat colour feel warm.", X0, y + 5, CW, size=10.5, weight=500) + 5
        cw = (CW - 2 * 5) / 3
        specs = [("right", st.grain_amount, st.grain_sigma, 0.0, "Fine and even. You can see it at 100 %, and you never notice a pattern."),
                 ("too little", 0.012, st.grain_sigma, 0.0, "Flat and digital. The warmth is gone."),
                 ("too much, and blotchy", 0.17, 2.4, 0.07, "Coarse, cloudy and dirty. Grain should never make patches.")]
        from engine.core import apply_grain, grain_field, soft_noise, rng_for
        for i, (name, amt, sig, blot, note) in enumerate(specs):
            art = Art(st, 620, 400, scale=1.0, seed=f"{k}-grain-demo", grain=False)
            art.text("astris.", 310, 215, 190, anchor="mm")
            img = art.render(grain=False)
            g = grain_field(400, 620, f"demo{i}", sig)
            if blot:
                img = img * (1 + blot * soft_noise(400, 620, rng_for("blot"), 60)[..., None])
            img = np.clip(apply_grain(img, g, amt, st.grain_lift), 0, 1)
            x = X0 + i * (cw + 5)
            self.pic(img, x, y, cw, cw * 400 / 620, f"grain{i}", quality=93)
            yy = y + cw * 400 / 620 + 6
            mark = "✓  " if i == 0 else "✕  "
            self.doc.text(x, yy, name, "anton-400", 12, t["head"] if i == 0 else t["soft"], tracking=0.01)
            self.p(note, x, yy + 5.5, cw, size=8.4)
        y += cw * 400 / 620 + 24
        self.rule(X0, y, X1)
        half = (CW - 8) / 2
        self.lab("the recipe", X0, y + 8)
        rec = [f"Strength: about {st.grain_amount * 100:.1f} % on flat colour. Softness: about {st.grain_sigma} px on a 1440 px tall picture, scaled up for bigger ones.",
               "Monochrome, no colour speckle. No clouds, no vignette, no scratches on the graphics themselves.",
               "Lettering: a hair of ink bleed, a slightly uneven edge, and the odd pinhole. Still easy to read at small sizes."]
        if k == "wildcard":
            rec.append("Risograph extras: paper fibres, the coral plate 1 to 3 px out of register, and a light speckle in each ink.")
        self.bullets(rec, X0, y + 14, half, size=8.4, gap=1.0)
        self.lab("where it comes from", X0 + half + 8, y + 8)
        self.bullets(["Graphics in this kit: already baked in. Don't add more.",
                      f"Video: the grain loops in {SUB['premiere']}/overlays, blend mode Overlay, 60 to 75 %.",
                      f"Photos and thumbnails: the tiles in {SUB['textures']}/textures, blend mode Overlay.",
                      "In video the grain changes every frame. A frozen texture over moving pictures looks like a dirty window."], X0 + half + 8, y + 14, half, size=8.4, gap=1.0)

    def logo_at(self, cx, cy, h, colour, sx=1.0, rot=0.0, outline=False):
        doc, lg = self.doc, self.st.logo
        c = doc.c
        c.saveState()
        c.translate(cx * MM, (PH - cy) * MM)
        c.rotate(rot)
        c.scale(sx, 1.0)
        w = h * lg.aspect
        for name, o, hs in lg.polys(0, 0, h):
            p = c.beginPath()
            for poly in [o] + hs:
                p.moveTo((poly[0][0] - w / 2) * MM, (h / 2 - poly[0][1]) * MM)
                for q in poly[1:]:
                    p.lineTo((q[0] - w / 2) * MM, (h / 2 - q[1]) * MM)
                p.close()
            if outline:
                c.setStrokeColorRGB(*pdf_rgb(colour))
                c.setLineWidth(0.7)
                c.drawPath(p, stroke=1, fill=0)
            else:
                c.setFillColorRGB(*pdf_rgb(colour))
                c.drawPath(p, stroke=0, fill=1, fillMode=0)
        c.restoreState()

    def logo(self):
        st, t, k, doc = self.st, self.t, self.k, self.doc
        self.start("the logo")
        y = self.h1("the logo.")
        y += 3
        self.lab("four layouts, one mark", X0, y)
        gap = 4.0
        ims = [(lay, thumb(self.f(SUB["logos"], "png-512", f"astris-{k}-logo-{lay}-on-colour-512.png"), 512)) for lay in ("wide", "stacked", "icon", "wordmark")]
        hh = 30.0
        x = X0
        for lay, im in ims:
            w = hh * im.width / im.height
            if w > 62:
                w, h_ = 62, 62 * im.height / im.width
            else:
                h_ = hh
            self.pic(im, x, y + 3 + (hh - h_) / 2, w, h_, f"lg-{lay}")
            self.lab(lay, x, y + hh + 9)
            x += w + gap
        y += hh + 16
        self.rule(X0, y, X1)
        # clear space
        self.lab("room to breathe", X0, y + 8)
        lh = 24.0
        lw = lh * st.logo.aspect
        m = lh * 4 / 16
        bx, by = X0 + 2 + m, y + 13 + m
        doc.rect(bx - m, by - m, lw + 2 * m, lh + 2 * m, stroke=t["rule"], width=0.5, dash=([2, 1.6], 0))
        self.logo_at(bx + lw / 2, by + lh / 2, lh, t["ink"])
        doc.line(bx - m, by + lh + m + 2.5, bx, by + lh + m + 2.5, t["rule"], 0.6)
        doc.text(bx - m / 2, by + lh + m + 6.5, "x", self.tf(700), 7, t["ink"], anchor="m")
        tx = X0 + lw + 2 * m + 12
        tw_ = (X1 - tx - 8) / 2
        self.p("Keep a clear margin all round, as wide as the logo's bar (x). Nothing else goes inside it: no type, and not the edge of the frame.", tx, y + 14, tw_, size=8.4)
        self.lab("smallest sizes", tx + tw_ + 8, y + 8)
        self.p("Full logo with its sprocket holes: 96 px or 20 mm wide, and up. Smaller than that, use the small-size mark from the logo pack (no holes), down to 16 px.", tx + tw_ + 8, y + 14, tw_, size=8.4)
        # don'ts
        y2 = y + 13 + lh + 2 * m + 12
        self.rule(X0, y2, X1)
        self.lab("please don't", X0, y2 + 8)
        bad_col = {"red": "#3A8F5C", "yellow": st.hex["signature"], "wildcard": "#3A8F5C"}[k]
        donts = [("stretch it", dict(sx=1.45)), ("tilt it", dict(rot=-18)), ("outline it", dict(outline=True)),
                 ("yellow on light" if k == "yellow" else "recolour it", dict(colour=bad_col)), ("crowd it", dict(crowd=True))]
        dw = CW * 0.62
        tw = (dw - 4 * 3) / 5
        for i, (name, kw) in enumerate(donts):
            x = X0 + i * (tw + 3)
            doc.rect(x, y2 + 12, tw, 22, colour="#FFFFFF" if (k == "yellow" and "yellow" in name) else t["tile"], radius=1.5,
                     stroke=t["soft"] if (k == "yellow" and "yellow" in name) else None, width=0.25)
            col = kw.pop("colour", t["ink"])
            crowd = kw.pop("crowd", False)
            self.logo_at(x + tw / 2 - (4.5 if crowd else 0), y2 + 23 - (1.5 if crowd else 0), 11.5, col, **kw)
            if crowd:
                doc.text(x + tw / 2 - 1.5, y2 + 27, "FILMS!", "anton-400", 9, t["ink"])
            doc.line(x + 2.5, y2 + 31.5, x + tw - 2.5, y2 + 14.5, t["rule"], 0.7)
            doc.text(x + tw / 2, y2 + 39, name, self.tf(500), 6.8, t["ink"], anchor="m")
        x0 = X0 + dw + 8
        self.lab("and also", x0, y2 + 8)
        self.bullets(["No shadows, glows, bevels or gradients.", "On a busy photo, put it on a tile of the style's colour.",
                      "Don't redraw it. Use the files: SVG for print, PNG for screens."], x0, y2 + 15, X1 - x0, size=8.2, gap=0.8)

    def layout(self):
        k = self.k
        self.start("layout")
        y = self.h1("layout.")
        y = self.p("One flat field of colour. One thing in the middle. Lots of room around it. If a layout feels empty, it is probably right.", X0, y + 5, CW, size=10.5, weight=500) + 4
        gap = 4.0
        w = (CW - 2 * gap) / 3
        for i, v in enumerate("abc"):
            x = X0 + i * (w + gap)
            self.pic(thumb(self.f(SUB["social"], "banner", f"astris-{k}-banner-{v}-2560x1440.png"), 900), x, y, w, w * 9 / 16, f"ly{v}")
            self.lab({"a": "A  name + supporting line", "b": "B  logo only", "c": "C  wordmark only"}[v], x, y + w * 9 / 16 + 6)
        y += w * 9 / 16 + 14
        self.rule(X0, y, X1)
        iw = 76.0
        self.pic(thumb(self.f(SUB["social"], "banner", f"astris-{k}-banner-safe-area-guide-2560x1440.jpg"), 1000), X0, y + 8, iw, iw * 9 / 16, "lysafe")
        yy = y + 8 + iw * 9 / 16 + 6
        self.lab("the YouTube banner", X0, yy)
        self.p("Upload 2560 x 1440. Only the middle 1546 x 423 shows on every screen, so the name stays inside it.", X0, yy + 5, iw, size=8.2)
        x0 = X0 + iw + 12
        self.lab("the rules", x0, y + 12)
        self.bullets(["Centre the one focal point, and leave generous empty space on every side of it.",
                      "One signature colour, one light, one dark. Nothing else.",
                      "The supporting line is always tiny, always directly under the main line, always the same family.",
                      "Profile pictures: the logo centred on the same field and grain. It must still read at 98 px in a circle.",
                      "Thumbnails: keep the bottom-right corner clear. YouTube puts the video length there."], x0, y + 18, X1 - x0, size=8.4, gap=1.3)

    def motion(self):
        k, st = self.k, self.st
        self.start("motion and sound")
        y = self.h1("motion and sound.")
        v = self.f(SUB["video"])
        clips = [("A  pop, 2 s", f"astris-{k}-intro-a-pop-2s-4k24.mp4", (0.42, 0.50, 1.9), "For shorts and quick cuts. The logo stamps on, the name lands."),
                 ("B  type, 4 s", f"astris-{k}-intro-b-type-4s-4k24.mp4", (1.0, 2.5, 3.9), "For everyday videos. The name arrives, then the line, then the logo."),
                 ("C  slow, 7 s", f"astris-{k}-intro-c-slow-7s-4k24.mp4", (1.6, 3.1, 6.9), "For films. The logo draws itself and a chime rings out.")]
        y += 4
        gap = 2.5
        fw = (CW - 46 - 2 * gap) / 3
        for name, fn, times, note in clips:
            self.h2(name, X0, y + 6, 12)
            self.p(note, X0, y + 11.5, 42, size=7.8)
            for j, tm in enumerate(times):
                self.pic(frame_of(v / fn, tm), X0 + 46 + j * (fw + gap), y, fw, fw * 9 / 16, f"mo-{fn[:22]}-{j}")
            y += fw * 9 / 16 + 4
        y += 2
        self.rule(X0, y, X1)
        half = (CW - 8) / 2
        self.lab("how things move", X0, y + 8)
        self.bullets(["Quick and soft: things arrive in a few frames and settle with a small bounce.", "Every intro ends on a held, still lockup you can cut away from.",
                      "The grain is alive in every frame. The colour field never moves.", "Also in the folder: a 5 s title logo (on colour and transparent) and a 10 s end card."],
                     X0, y + 14, half, size=8.2, gap=0.8)
        self.lab("how it sounds", X0 + half + 8, y + 8)
        self.bullets([f"The palette: {SOUND[k]}.", "The signature: two notes, the second a fourth above the first. It is in every intro, in this style's own voice.",
                      f"All sounds are 48 kHz, 24-bit, and peak at -1 dB. They live in {SUB['sound']}."], X0 + half + 8, y + 14, half, size=8.2, gap=0.8)

    def premiere(self):
        k = self.k
        self.start("in premiere")
        y = self.h1("in premiere.")
        half = (CW - 10) / 2
        steps = [("Start a sequence", "3840 x 2160 (or 1920 x 1080), 24 fps. Everything here is made for that."),
                 ("Bring the kit in", f"File, Import. Take {SUB['video']}, {SUB['premiere']} and {SUB['sound']} from this style's folder."),
                 ("Open with an intro", "A for shorts, B for everyday videos, C for films. Sound is already on the clip."),
                 ("Add the grain", "Put a grain loop on the top track. Effect Controls, Opacity, Blend Mode: Overlay. Opacity 60 to 75 %."),
                 ("Give it the colour", f"Lumetri Color, Creative, Look, Browse. Pick astris-{k}-look-1-natural. Turn Intensity down to taste."),
                 ("Name people", "Drop a lower third above the footage. Your own names: edit brand-config.json, then run the build line in PREMIERE-README."),
                 ("Titles of your own", "Essential Graphics, font Anton, lowercase with a full stop. Tracking 12. Supporting line at a fifth of the size, tracking 160."),
                 ("Mark it", "Corner bug PNG on the top track, bottom right, Opacity 70 %. Or use the 10 s clip that fades itself."),
                 ("End it", "The 10 s end card has two empty frames. In YouTube's end screen editor, put your two video suggestions over them."),
                 ("Export", "H.264, Match Source. 4K: VBR 2 pass, 40 to 60 Mbps. 1080p: 16 to 20 Mbps. Audio AAC, 48 kHz, 320 kbps.")]
        y0 = y + 6
        for i, (hd, tx) in enumerate(steps):
            x = X0 + (i // 5) * (half + 10)
            yy = y0 + (i % 5) * 24.5
            self.doc.text(x, yy + 6.2, f"{i + 1:02d}", "anton-400", 17, self.t["rule"])
            self.h2(hd.lower() + ".", x + 13, yy + 3.5, 11.5)
            self.p(tx, x + 13, yy + 8.6, half - 13, size=8.2)
        yb = y0 + 5 * 24.5 + 2
        self.doc.rect(X0, yb - 1, CW, 18, colour=self.t["tile"], radius=2)
        self.p("One honest note: there are no .mogrt templates in this kit. Those can only be made inside After Effects or Premiere. You get rendered clips with transparency instead, "
               "which work like any other clip, and a one-line command to re-render the lower thirds with your own names.", X0 + 5, yb + 5.8, CW - 10, size=8.0)

    def files(self):
        k = self.k
        self.start("where things are")
        y = self.h1("where things are.")
        rows = [(SUB["guide"], "This guide, as a PDF and as pictures."), (SUB["logos"], "The logo in this style's colours: four layouts, five colourways, and layers for animating."),
                (SUB["social"], "YouTube banner and profile picture, thumbnail templates, Instagram covers and posts."),
                (SUB["video"], "Three intros, the animated title logo and the end card. 4K, with sound."),
                (SUB["premiere"], "Corner bug, lower thirds and overlay loops, with a how-to."),
                (SUB["sound"], "Whooshes, impacts, clicks, chimes and the stingers from every video."),
                (SUB["merch"], "Stickers, cap, hoodie, T-shirt, tote, bottle wrap, phone wallpapers and drawn mock-ups."),
                (SUB["paper"], "Posters, business card, email signature, invoice, press kit, clapperboard, presents card."),
                (SUB["web"], "Favicons, sharing image, hero mock-ups, design tokens and a preview page."),
                (SUB["textures"], "Seamless grain and paper tiles, and three colour looks for footage.")]
        y += 4
        for name, what in rows:
            self.doc.line(X0, y, X1, y, self.t["soft"], 0.25)
            self.doc.text(X0, y + 6.6, name, self.tf(700), 8.6, self.t["ink"])
            self.p(what, X0 + 62, y + 6.6, CW - 62, size=8.6)
            y += 10.6
        self.doc.line(X0, y, X1, y, self.t["soft"], 0.25)
        y += 9
        half = (CW - 8) / 2
        self.lab("to change the words", X0, y)
        self.p("Names, contact details, film titles and supporting lines all live in brand-config.json and films.txt at the top of the kit. Change them there, run the build, and every card, poster and signature updates. code/README.md shows how.", X0, y + 6, half, size=8.4)
        self.lab("anything in [square brackets]", X0 + half + 8, y)
        self.p("is a placeholder waiting for you. Nothing about Astris has been made up in this kit: no awards, quotes, numbers or contact details.", X0 + half + 8, y + 6, half, size=8.4)

    def build(self):
        self.cover()
        self.story()
        self.voice()
        self.mood()
        self.colour()
        self.type_()
        self.grain()
        self.logo()
        self.layout()
        self.motion()
        self.premiere()
        self.files()
        self.doc.save()
        d = self.path.parent / "pages"
        d.mkdir(exist_ok=True)
        pages = to_png_pages(self.path, d / "tmp-page", 2339)
        made = []
        for i, pg in enumerate(pages):
            name = PAGES[i].replace(" ", "-")
            dst = d / f"astris-{self.k}-brand-guide-page-{i + 1:02d}-{name}.png"
            from engine.core import save_png
            save_png(np.asarray(Image.open(pg).convert("RGB")), dst, max_err=1.3)       # indexed where that is lossless to the eye
            pg.unlink()
            made.append(dst.name)
        return made


def build(style):
    g = Guide(style)
    made = g.build()
    size = g.path.stat().st_size / 1e6
    return [f"{g.path.name}  {size:.1f} MB, {len(made)} pages"]
