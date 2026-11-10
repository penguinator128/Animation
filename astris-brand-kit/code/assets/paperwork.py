"""
Paperwork in a style, all generated from brand-config.json:
  business card (90 x 55 mm, print PDF with 3 mm bleed + crop marks, PNG previews)
  email signature (HTML + plain text + images + how-to)
  letterhead and invoice template (A4 PDF + PNG)
  press kit (one-page and multi-page PDF, boilerplate.txt, downloads list, logo files)
Anything in [SQUARE BRACKETS] is a placeholder: fill it in once in brand-config.json and re-run.
"""
import shutil

import numpy as np
from PIL import Image

from engine import lockup as L
from engine import type as T
from engine.core import Art, save_jpg, save_png, to_u8
from engine.paths import KIT, STYLE_DIRS, SUB, out
from engine.pdf import Doc, to_png_pages
from engine.style import config, films

DPI = 300
PX = DPI / 25.4


def tones(style):
    h, k = style.hex, style.key
    return {"paper": h["light"], "ink": h["dark"], "accent": h["signature"], "second": h.get("second", h["signature"]),
            "heading": h["dark"] if k == "yellow" else h["signature"], "soft": {"red": "#6B5750", "yellow": "#5E5A52", "wildcard": "#4A5278"}[k],
            "on_accent": h["dark"] if k == "yellow" else h["light"]}


def tf(style, w=400):
    return f"{style.text_family}-{w}"


# ====================================================================================================
# business card
# ====================================================================================================
def card_front(style):
    W, H = 1134, 720                      # 96 x 61 mm at 300 dpi = 90 x 55 mm card + 3 mm bleed all round
    art = Art(style, W, H, scale=1.0, seed=f"{style.key}-card-front")
    L.name_line(art, W / 2, H / 2 - 22, 700, tag_scale=0.22)
    return art.render()


def card_back(style):
    W, H = 1134, 720
    cfg = config()
    p, so = cfg["person"], cfg["social"]
    art = Art(style, W, H, scale=1.0, seed=f"{style.key}-card-back", scheme="light")
    m = 35 + 62                            # bleed + a 5 mm safe margin
    role = "ink"
    art.logo(m + 70, m + 62, 118, role=role)
    art.text(p["name"], m, 372, 62, anchor="ls", tracking=0.01, role=role)
    f5, f4 = style.text_face(500), style.text_face(400)
    art.text(p["role"], m + 2, 418, 25, face=f5, tracking=0.12, anchor="ls", role="second" if style.key == "red" else "ink", shadow=False, wear=0)
    y = 500
    for line in (p["email"], p["phone"], p["website"]):
        art.text(line, m + 2, y, 25, face=f4, tracking=0.02, anchor="ls", role="second" if style.key == "red" else "ink", shadow=False, wear=0)
        y += 40
    y = 540
    for line in (so["youtube"], so["instagram"]):
        art.text(line, W - m, y, 25, face=f4, tracking=0.02, anchor="rs", role="second" if style.key == "red" else "ink", shadow=False, wear=0)
        y += 40
    art.text(cfg["brand"]["name_lowercase"], W - m, m + 84, 44, anchor="rs", tracking=0.012, role=role, shadow=False)
    return art.render()


def business_card(style):
    k = style.key
    d = out(k, "paper", "business-card")
    front, back = card_front(style), card_back(style)
    save_png(front, d / f"astris-{k}-business-card-front-with-bleed-1134x720.png", dpi=DPI)
    save_png(back, d / f"astris-{k}-business-card-back-with-bleed-1134x720.png", dpi=DPI)
    b = 35                                 # 3 mm bleed in px
    save_png(front[b:-b, b:-b], d / f"astris-{k}-business-card-front-trimmed-1064x650.png", dpi=DPI)
    save_png(back[b:-b, b:-b], d / f"astris-{k}-business-card-back-trimmed-1064x650.png", dpi=DPI)
    # print PDF: each side on its own page, artwork with bleed, crop marks at the 90 x 55 mm trim
    slug_mm = 9.0
    doc = Doc(d / f"astris-{k}-business-card-print-90x55mm-3mm-bleed.pdf", 96 + 2 * slug_mm, 61 + 2 * slug_mm,
              title=f"ASTRIS PRODUCTIONS business card ({style.name}): 90 x 55 mm, 3 mm bleed, crop marks")
    for i, img in enumerate((front, back)):
        if i:
            doc.page()
        doc.image(img, slug_mm, slug_mm, 96, 61, quality=95, key=f"card{i}")
        doc.crop_marks(slug_mm + 3, slug_mm + 3, 90, 55)
    doc.save()
    # a simple preview: both sides on a neutral desk (an illustration)
    Wp, Hp = 2400, 1500
    desk = np.empty((Hp, Wp, 3), np.float32)
    desk[:] = np.array([0.20, 0.20, 0.22], np.float32)
    import cv2
    for img, (x, y) in ((front[b:-b, b:-b], (150, 190)), (back[b:-b, b:-b], (1186, 660))):
        h, w = img.shape[:2]
        sh = np.zeros((Hp, Wp), np.float32)
        sh[y + 22:y + h + 22, x + 16:x + w + 16] = 0.55
        sh = cv2.GaussianBlur(sh, (0, 0), 22)
        desk *= (1 - sh[..., None])
        desk[y:y + h, x:x + w] = img
    save_jpg(desk, d / f"astris-{k}-business-card-preview.jpg", 90)
    return 6


# ====================================================================================================
# email signature
# ====================================================================================================
def email_signature(style):
    k = style.key
    cfg = config()
    p, so, t = cfg["person"], cfg["social"], tones(style)
    d = out(k, "paper", "email-signature")
    (d / "images").mkdir(exist_ok=True)
    # the logo on the style's field, 2x for sharp screens (shown at 84 x 84)
    art = Art(style, 168, 168, scale=1.0, seed=f"{k}-sig")
    from assets.youtube import logo_fit
    cx, cy, h = logo_fit(style, 168, 0.66)
    art.logo(cx, cy, h, wear=0)
    logo_file = f"astris-{k}-signature-logo-168x168.png"
    save_png(art.render(), d / "images" / logo_file)
    font_stack = {"dm-sans": "'DM Sans', Arial, Helvetica, sans-serif", "inter": "Inter, Arial, Helvetica, sans-serif",
                  "space-grotesk": "'Space Grotesk', Arial, Helvetica, sans-serif"}[style.text_family]
    name_col, link_col = t["ink"], (t["ink"] if k == "yellow" else t["accent"])
    html = f"""<!-- ASTRIS PRODUCTIONS email signature, {style.name} style. Generated from brand-config.json by code/build.py paper.
     The image is loaded from a relative path: see README.md in this folder for how to host it. -->
<table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;font-family:{font_stack};color:{t['ink']};">
  <tr>
    <td style="padding:0 16px 0 0;vertical-align:top;">
      <img src="images/{logo_file}" width="84" height="84" alt="ASTRIS PRODUCTIONS" style="display:block;border:0;border-radius:8px;">
    </td>
    <td style="padding:0 0 0 16px;border-left:3px solid {t['accent']};vertical-align:top;">
      <table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
        <tr><td style="font-size:17px;line-height:22px;font-weight:bold;color:{name_col};padding:0 0 1px 0;">{p['name']}</td></tr>
        <tr><td style="font-size:12px;line-height:16px;color:{t['soft']};letter-spacing:1px;text-transform:uppercase;padding:0 0 8px 0;">{p['role']} &nbsp;&middot;&nbsp; ASTRIS PRODUCTIONS</td></tr>
        <tr><td style="font-size:13px;line-height:19px;color:{t['ink']};">{p['email']} &nbsp;&middot;&nbsp; {p['phone']}</td></tr>
        <tr><td style="font-size:13px;line-height:19px;color:{t['ink']};"><span style="color:{link_col};font-weight:bold;">{p['website']}</span> &nbsp;&middot;&nbsp; {so['youtube']} &nbsp;&middot;&nbsp; {so['instagram']}</td></tr>
        <tr><td style="font-size:12px;line-height:18px;color:{t['soft']};font-style:italic;padding:6px 0 0 0;">{style.tagline}</td></tr>
      </table>
    </td>
  </tr>
</table>
"""
    (d / f"astris-{k}-email-signature.html").write_text(html)
    txt = (f"{p['name']}\n{p['role']}  |  ASTRIS PRODUCTIONS\n{p['email']}  |  {p['phone']}\n{p['website']}  |  {so['youtube']}  |  {so['instagram']}\n\n{style.tagline}\n")
    (d / f"astris-{k}-email-signature.txt").write_text(txt)
    (d / "README.md").write_text(f"""# Email signature ({style.name})

| File | What it is |
|---|---|
| `astris-{k}-email-signature.html` | The signature: a small table with inline styles, so it survives Gmail and Outlook. |
| `astris-{k}-email-signature.txt` | Plain-text version, for mail apps that don't do HTML. |
| `images/{logo_file}` | The logo tile (168 x 168 px, shown at 84 x 84 so it is sharp on phones). |

Everything in [SQUARE BRACKETS] comes from `brand-config.json`. Fill in your details there once, then run
`python3 code/build.py paper` and every signature, card and letterhead updates.

## 1. Host the image

Email can't load a picture from your computer, so the logo has to live at a public web address.
Once this kit is pushed to GitHub, every file has one. The pattern is:

```
https://raw.githubusercontent.com/[YOUR-GITHUB-NAME]/[YOUR-REPO]/[BRANCH]/astris-brand-kit/{STYLE_DIRS[k].name}/{SUB['paper']}/email-signature/images/{logo_file}
```

Open the HTML file in a text editor and replace `images/{logo_file}` with that full address.
(The repo must be public for the picture to show. Any other image host works the same way.)
This image is a normal file in the repo, not a Git LFS file, so the raw link serves the real picture.

## 2. Paste it into your mail app

**Gmail:** open the HTML file in your browser, select the whole signature, copy. In Gmail go to Settings, See all settings,
General, Signature, Create new, and paste. Save changes at the bottom of the page.

**Outlook (desktop):** open the HTML file in your browser, select all, copy. In Outlook go to File, Options, Mail, Signatures,
New, and paste into the box. If the picture is missing, check step 1.

**Outlook on the web:** Settings, Mail, Compose and reply, then paste into the signature box.

**Apple Mail:** Mail, Settings, Signatures, add a new one, paste, and untick "Always match my default message font".

## Good to know

- Signatures can't carry custom fonts reliably: mail apps fall back to Arial if the brand font isn't installed. That is expected.
- Keep the picture under 100 KB (this one is) so it loads straight away.
""")
    return 4


# ====================================================================================================
# letterhead + invoice
# ====================================================================================================
def doc_header(doc, style, t, cfg):
    p = cfg["person"]
    doc.logo(style.logo, 18, 15, 13, t["accent"] if style.key != "yellow" else t["ink"])
    x = 18 + 13 * style.logo.aspect + 3.6
    doc.text(x, 24.2, cfg["brand"]["first_word"], "anton-400", 19, t["ink"], tracking=0.02)
    doc.text(x + 0.2, 28.2, cfg["brand"]["second_word"], "anton-400", 5.6, t["heading"], tracking=0.42)
    for i, line in enumerate((p["email"], p["phone"], p["website"])):
        doc.text(doc.w - 18, 18.5 + i * 4.6, line, tf(style), 8.2, t["soft"], anchor="r")
    if style.key == "yellow":
        doc.rect(18, 33.5, doc.w - 36, 1.5, t["accent"])
    else:
        doc.line(18, 34, doc.w - 18, 34, t["accent"], 1.2)
        if style.is_riso:
            doc.line(18.5, 34.6, doc.w - 17.5, 34.6, t["second"], 0.6)


def doc_footer(doc, style, t, cfg):
    p, so = cfg["person"], cfg["social"]
    y = doc.h - 14
    doc.line(18, y - 5, doc.w - 18, y - 5, t["soft"], 0.3)
    doc.text(18, y, f"ASTRIS PRODUCTIONS   ·   ABN {p['abn']}   ·   {p['address']}", tf(style), 7.2, t["soft"])
    doc.text(doc.w - 18, y, f"{so['youtube']}   ·   {so['instagram']}", tf(style), 7.2, t["soft"], anchor="r")
    doc.text(18, y + 4.4, style.tagline, tf(style, 500), 7.2, t["heading"])


def letterhead(style):
    k, cfg, t = style.key, config(), tones(style)
    d = out(k, "paper", "letterhead-and-invoice")
    path = d / f"astris-{k}-letterhead-a4.pdf"
    doc = Doc(path, 210, 297, title=f"ASTRIS PRODUCTIONS letterhead ({style.name})")
    doc_header(doc, style, t, cfg)
    doc_footer(doc, style, t, cfg)
    doc.save()
    png = to_png_pages(path, d / f"astris-{k}-letterhead-a4-2480x3508", 2480)
    png[0].rename(d / f"astris-{k}-letterhead-a4-2480x3508.png")
    # ---- invoice
    path = d / f"astris-{k}-invoice-template-a4.pdf"
    doc = Doc(path, 210, 297, title=f"ASTRIS PRODUCTIONS invoice template ({style.name})")
    doc_header(doc, style, t, cfg)
    p = cfg["person"]
    inv = cfg.get("invoice", {})
    doc.text(18, 56, inv.get("title", "INVOICE"), "anton-400", 30, t["heading"], tracking=0.02)
    f4, f5, f7 = tf(style), tf(style, 500), tf(style, 700)
    for i, (lab, val) in enumerate((("INVOICE NUMBER", "[INV-0001]"), ("DATE", "[DATE]"), ("DUE", "[DUE DATE]"))):
        doc.text(132, 48 + i * 6, lab, f5, 6.6, t["soft"], tracking=0.12)
        doc.text(doc.w - 18, 48 + i * 6, val, f5, 9, t["ink"], anchor="r")
    doc.text(18, 72, "BILL TO", f5, 6.6, t["soft"], tracking=0.12)
    for i, line in enumerate(("[CLIENT NAME]", "[CLIENT COMPANY]", "[CLIENT ADDRESS]", "[CLIENT EMAIL]")):
        doc.text(18, 78 + i * 5.2, line, f7 if i == 0 else f4, 9.5, t["ink"])
    doc.text(120, 72, "FOR", f5, 6.6, t["soft"], tracking=0.12)
    doc.text(120, 78, "[PROJECT OR FILM TITLE]", f7, 9.5, t["ink"])
    doc.text(120, 83.2, "[A LINE ABOUT THE WORK]", f4, 9.5, t["ink"])
    # table
    y0 = 106
    cols = [(18, "DESCRIPTION", "l"), (128, "QTY", "r"), (158, "RATE", "r"), (192, "AMOUNT", "r")]
    doc.rect(18, y0, 174, 8.5, t["accent"])
    for x, lab, an in cols:
        doc.text(x + (3 if an == "l" else 0) - (0 if an == "l" else 3), y0 + 5.7, lab, f7, 7, t["on_accent"], anchor=an, tracking=0.12)
    rows = 7
    for r in range(rows):
        y = y0 + 8.5 + (r + 1) * 9.5
        doc.line(18, y, 192, y, t["soft"], 0.25)
        if r < 2:
            doc.text(21, y - 3.3, "[DESCRIPTION OF WORK]", f4, 9, t["ink"])
            doc.text(125, y - 3.3, "[1]", f4, 9, t["ink"], anchor="r")
            doc.text(155, y - 3.3, "[0.00]", f4, 9, t["ink"], anchor="r")
            doc.text(189, y - 3.3, "[0.00]", f4, 9, t["ink"], anchor="r")
    yt = y0 + 8.5 + rows * 9.5 + 10
    for i, (lab, val, bold) in enumerate((("SUBTOTAL", "[0.00]", False), (inv.get("tax_label", "GST [IF REGISTERED]"), "[0.00]", False), (f"TOTAL ({inv.get('currency', 'AUD')})", "[0.00]", True))):
        y = yt + i * 7.5
        if bold:
            doc.rect(120, y - 5.6, 72, 8.6, t["accent"])
        doc.text(123, y, lab, f7 if bold else f5, 7.4, t["on_accent"] if bold else t["soft"], tracking=0.12)
        doc.text(189, y, val, f7 if bold else f4, 10 if bold else 9.5, t["on_accent"] if bold else t["ink"], anchor="r")
    # payment details
    yp = yt + 34
    doc.text(18, yp, "HOW TO PAY", f5, 6.6, t["soft"], tracking=0.12)
    for i, (lab, val) in enumerate((("Account name", "[ACCOUNT NAME]"), ("BSB", "[BSB]"), ("Account number", "[ACCOUNT NUMBER]"), ("Reference", "[INVOICE NUMBER]"))):
        doc.text(18, yp + 6.5 + i * 5.4, lab, f4, 9, t["soft"])
        doc.text(52, yp + 6.5 + i * 5.4, val, f5, 9, t["ink"])
    doc.text(120, yp, "FROM", f5, 6.6, t["soft"], tracking=0.12)
    for i, line in enumerate((p["name"], "ASTRIS PRODUCTIONS", f"ABN {p['abn']}", p["address"])):
        doc.text(120, yp + 6.5 + i * 5.4, line, f7 if i == 0 else f4, 9, t["ink"])
    doc.text(18, 268, inv.get("sign_off", "thank you."), "anton-400", 24, t["heading"])
    doc_footer(doc, style, t, cfg)
    doc.save()
    png = to_png_pages(path, d / f"astris-{k}-invoice-template-a4-2480x3508", 2480)
    png[0].rename(d / f"astris-{k}-invoice-template-a4-2480x3508.png")
    return 4


# ====================================================================================================
# press kit
# ====================================================================================================
def field_image(style, w, h, scheme="main", seed="bg", draw=None):
    art = Art(style, w, h, scheme=scheme, seed=f"{style.key}-{seed}-{w}x{h}")
    if draw:
        draw(art)
    return art.render()


def press_kit(style):
    k, cfg, t = style.key, config(), tones(style)
    p, so, b = cfg["person"], cfg["social"], cfg["brand"]
    d = out(k, "paper", "press-kit")
    f4, f5, f7 = tf(style), tf(style, 500), tf(style, 700)
    fl = films()
    # ---------------- one page
    path1 = d / f"astris-{k}-press-kit-one-page-a4.pdf"
    doc = Doc(path1, 210, 297, title=f"ASTRIS PRODUCTIONS press kit, one page ({style.name})")
    band = field_image(style, 2480, 780, seed="press-band", draw=lambda a: L.horizontal(a, 2480 / 2, 390, 300))
    doc.image(band, 0, 0, 210, quality=90, key="band")
    y = 78
    doc.text(18, y, "ABOUT", f7, 7, t["soft"], tracking=0.16)
    y = doc.para(18, y + 7, b["about_short"], f4, 10, t["ink"], 108)
    doc.text(18, y + 6, "FILMS", f7, 7, t["soft"], tracking=0.16)
    yy = y + 14
    for title, note in fl:
        doc.text(18, yy, title.upper(), "anton-400", 15, t["heading"], tracking=0.01)
        doc.text(18 + doc.width(title.upper(), "anton-400", 15, 0.01) + 3, yy, (f"({note})   " if note else "") + "[YEAR]  ·  [RUNTIME]", f4, 8.5, t["soft"])
        yy += 8.2
    # contact column
    x2 = 138
    doc.text(x2, 78, "CONTACT", f7, 7, t["soft"], tracking=0.16)
    for i, line in enumerate((p["name"], p["role"], p["email"], p["phone"], p["website"], so["youtube"], so["instagram"], p["location"])):
        doc.text(x2, 85 + i * 5.4, line, f7 if i == 0 else f4, 9.5, t["ink"])
    # stills
    ys = max(yy + 8, 150)
    doc.text(18, ys, "STILLS", f7, 7, t["soft"], tracking=0.16)
    sw = (174 - 2 * 5) / 3
    for i in range(3):
        doc.placeholder(18 + i * (sw + 5), ys + 4, sw, sw * 9 / 16, "[PLACEHOLDER]\nfilm still, 16:9", t["soft"], f4, 7.5)
    yb = ys + 4 + sw * 9 / 16 + 12
    doc.text(18, yb, "BOILERPLATE", f7, 7, t["soft"], tracking=0.16)
    yb = doc.para(18, yb + 7, "[PLACEHOLDER: the short paragraph a journalist can paste as-is. See boilerplate.txt.]", f4, 10, t["ink"], 174)
    doc.text(18, yb + 5, "LOGOS AND DOWNLOADS", f7, 7, t["soft"], tracking=0.16)
    doc.para(18, yb + 12, "Logo files are in the logos folder beside this PDF. Posters, banners and the full kit are listed in downloads-list.md.", f4, 9, t["ink"], 174)
    doc_footer(doc, style, t, cfg)
    doc.save()
    # ---------------- multi page
    path2 = d / f"astris-{k}-press-kit-full-a4.pdf"
    doc = Doc(path2, 210, 297, title=f"ASTRIS PRODUCTIONS press kit ({style.name})")
    cover = field_image(style, 1654, 2339, seed="press-cover", draw=lambda a: (L.vertical(a, 1654 / 2, 2339 * 0.42, 520),
                        a.text("press kit.", 1654 / 2, 2339 * 0.80, 150, anchor="mm"), a.text(style.tagline, 1654 / 2, 2339 * 0.87, 42, tracking=L.TRACK_TAG, anchor="mm", shadow=False)))
    doc.image(cover, 0, 0, 210, 297, quality=88, key="cover")

    def head(title, n):
        doc.page()
        doc.logo(style.logo, 18, 15, 9, t["accent"] if k != "yellow" else t["ink"])
        doc.text(doc.w - 18, 22, f"ASTRIS PRODUCTIONS  ·  PRESS KIT  ·  {n}", f5, 6.6, t["soft"], anchor="r", tracking=0.14)
        doc.text(18, 52, title, "anton-400", 34, t["heading"], tracking=0.01)
        if k == "yellow":
            doc.rect(18, 57, 40, 1.6, t["accent"])
        else:
            doc.line(18, 58, 58, 58, t["accent"], 1.4)
    head("about.", 2)
    y = doc.para(18, 76, b["about_long"], f4, 11, t["ink"], 174)
    doc.text(18, y + 10, "THE SHORT VERSION", f7, 7, t["soft"], tracking=0.16)
    y = doc.para(18, y + 17, b["about_short"], f4, 11, t["ink"], 174)
    y += 10
    for i, (lab, val) in enumerate((("Founded", "[YEAR]"), ("Based in", p["location"]), ("Makes", "[SHORT FILMS / DOCUMENTARIES / ...]"), ("Team", "[WHO IS ASTRIS]"))):
        doc.line(18, y + i * 10 - 6, 192, y + i * 10 - 6, t["soft"], 0.25)
        doc.text(18, y + i * 10, lab.upper(), f7, 7, t["soft"], tracking=0.16)
        doc.text(70, y + i * 10, val, f4, 11, t["ink"])
    doc_footer(doc, style, t, cfg)
    head("films.", 3)
    y = 74
    bh = (297 - 74 - 30) / max(4, len(fl)) - 4
    for title, note in fl[:6]:
        sw_ = min(70, bh * 16 / 9)
        doc.placeholder(18, y, sw_, sw_ * 9 / 16, "[PLACEHOLDER]\nstill", t["soft"], f4, 7.5)
        x = 18 + sw_ + 8
        doc.text(x, y + 8, title.upper(), "anton-400", 20, t["heading"], tracking=0.01)
        doc.text(x, y + 14.5, (f"({note})   " if note else "") + "[YEAR]  ·  [RUNTIME]  ·  [GENRE]", f5, 8.5, t["soft"])
        doc.para(x, y + 21.5, "[PLACEHOLDER: one or two sentences about this film. Do not add awards or quotes unless they are real.]", f4, 9.5, t["ink"], 192 - x, max_lines=3)
        y += bh + 4
    doc_footer(doc, style, t, cfg)
    head("stills and downloads.", 4)
    sw = (174 - 5) / 2
    for i in range(4):
        doc.placeholder(18 + (i % 2) * (sw + 5), 72 + (i // 2) * (sw * 9 / 16 + 5), sw, sw * 9 / 16, "[PLACEHOLDER]\nhigh-resolution still, 16:9", t["soft"], f4, 8)
    y = 72 + 2 * (sw * 9 / 16 + 5) + 10
    doc.text(18, y, "WHAT YOU CAN DOWNLOAD", f7, 7, t["soft"], tracking=0.16)
    y += 8
    for lab, where in (("Logos", "logos/ beside this PDF: black, white and colour, PNG and SVG"), ("Posters", f"{SUB['paper']}/posters/"),
                       ("Banner and profile picture", f"{SUB['social']}/"), ("The whole kit", "downloads/ at the top of the kit")):
        doc.text(18, y, lab, f7, 10, t["ink"])
        doc.text(70, y, where, f4, 10, t["ink"])
        y += 7
    doc_footer(doc, style, t, cfg)
    head("contact.", 5)
    for i, line in enumerate((p["name"], p["role"], p["email"], p["phone"], p["website"], so["youtube"], so["instagram"], p["location"])):
        doc.text(18, 78 + i * 7.2, line, f7 if i == 0 else f4, 13 if i == 0 else 12, t["ink"])
    y = 150
    doc.text(18, y, "BOILERPLATE", f7, 7, t["soft"], tracking=0.16)
    doc.para(18, y + 8, "[PLACEHOLDER: the short paragraph a journalist can paste as-is. Write it once in boilerplate.txt.]", f4, 11, t["ink"], 174)
    doc.text(18, 250, "thank you.", "anton-400", 30, t["heading"])
    doc_footer(doc, style, t, cfg)
    doc.save()
    (d / "previews").mkdir(exist_ok=True)
    for path, stem in ((path1, f"astris-{k}-press-kit-one-page-preview"), (path2, f"astris-{k}-press-kit-full-preview-page")):
        for pg in to_png_pages(path, d / "previews" / stem, 1240):
            Image.open(pg).convert("RGB").save(pg.with_suffix(".jpg"), quality=88)
            pg.unlink()
    (d / "boilerplate.txt").write_text(
        "ASTRIS PRODUCTIONS: boilerplate\n================================\n\n"
        "[PLACEHOLDER: replace everything between the lines with your own words. Aim for about 50 words that a journalist can paste as-is.]\n\n"
        "--------------------------------------------------------------\n"
        "ASTRIS PRODUCTIONS is [WHAT YOU ARE: an independent film production company / a filmmaking collective / ...] based in "
        f"{p['location']}. Founded in [YEAR] by [NAME(S)], it makes [WHAT YOU MAKE]. Recent work includes "
        + ", ".join(tt for tt, _ in fl) + ".\n"
        "--------------------------------------------------------------\n\n"
        f"Press contact: {p['name']}, {p['email']}, {p['phone']}\nWebsite: {p['website']}\n\n"
        "Rules for this text: only facts. No awards, festival selections, quotes or numbers unless they are real and you can point to them.\n")
    # logo files for the press
    ld = d / "logos"
    ld.mkdir(exist_ok=True)
    src = STYLE_DIRS[k] / SUB["logos"]
    n = 0
    for layout in ("wide", "stacked", "icon"):
        for way in ("full-colour", "black", "white"):
            for sub, ext in (("png-4096", "-4096.png"), ("svg", ".svg")):
                f = src / sub / f"astris-{k}-logo-{layout}-{way}{ext}"
                if f.exists():
                    shutil.copyfile(f, ld / f.name)
                    n += 1
    (d / "downloads-list.md").write_text(f"""# Press downloads ({style.name})

Everything a journalist, festival or venue might ask for, and where it lives in the kit.

| What | Where | Notes |
|---|---|---|
| Logos (PNG 4096 px + SVG) | `logos/` in this folder | wide, stacked and icon; full colour, black, white |
| Every logo version | `../../{SUB['logos']}/` | all layouts and colourways, 4096 px and 512 px |
| Plain logo, no style | `../../../01_Logo-Pack-Bare-Bones/` | vector, PDF, up to 8192 px |
| Film posters | `../posters/` | one per film, A3 and 2:3 |
| Channel banner and profile picture | `../../{SUB['social']}/` | upload-ready |
| About text | `boilerplate.txt` | fill in the placeholders first |
| Stills | [PLACEHOLDER: add a `stills/` folder here with your film stills] | name them `astris-[film]-still-01.jpg` |

Press contact: {p['name']}, {p['email']}
""")
    return 6 + n


def build(style):
    n = business_card(style) + email_signature(style) + letterhead(style) + press_kit(style)
    return [f"{n} paperwork files"]
