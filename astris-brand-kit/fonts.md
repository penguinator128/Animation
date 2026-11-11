# Fonts

Every font in this kit is **free for commercial use**. All of them are released under the
**SIL Open Font License, version 1.1 (OFL)**, which lets you use them in videos, print, merch and on the web
without paying or crediting anyone. The only thing the licence forbids is selling the font files on their own.

The font files are in `code/fonts/` (TrueType, `.ttf`), and each font's full licence text is in `code/fonts/licenses/`.

## The fonts this kit uses

| Role | Font (exact name) | Weights used | Where it is used | Source | Licence |
|---|---|---|---|---|---|
| Display, all three styles | **Anton** | Regular (400) | The name, titles, supporting lines, posters, stickers, intros | Google Fonts: `fonts.google.com/specimen/Anton`. Project: `github.com/googlefonts/AntonFont`. Copyright 2020 The Anton Project Authors | SIL OFL 1.1 |
| Text, Style 1 Red | **DM Sans** | Regular (400), Medium (500), Bold (700) | Small labels, business card, letterhead, invoice, press kit, lower thirds | Google Fonts: `fonts.google.com/specimen/DM+Sans`. Project: `github.com/googlefonts/dm-fonts`. Copyright 2014 The DM Sans Project Authors | SIL OFL 1.1 |
| Text, Style 2 Yellow | **Inter** | Regular (400), Medium (500), Semi Bold (600), Bold (700) | The same jobs, in the yellow style | Google Fonts: `fonts.google.com/specimen/Inter`. Project: `github.com/rsms/inter`. Copyright 2016 The Inter Project Authors | SIL OFL 1.1 |
| Text, Style 3 Wildcard | **Space Grotesk** | Regular (400), Medium (500), Bold (700) | The same jobs, in the risograph style | Google Fonts: `fonts.google.com/specimen/Space+Grotesk`. Project: `github.com/floriankarsten/space-grotesk`. Copyright 2020 The Space Grotesk Project Authors | SIL OFL 1.1 |

Why these: Anton is bold, condensed and friendly, with a proper lowercase (the brand line is lowercase).
Each style then gets a plain, very readable partner for small text, so the three styles feel related but not identical.

## Stand-ins (also in `code/fonts/`, also SIL OFL 1.1)

These were tried while designing. They are there in case you ever need a substitute.

| Font | Weight | Good for | Source |
|---|---|---|---|
| **League Gothic** | Regular (400) | The closest stand-in for Anton: a little lighter and narrower | `github.com/theleagueof/league-gothic` (also on Google Fonts) |
| **Oswald** | Medium (500), Bold (700) | A softer condensed headline | `github.com/googlefonts/OswaldFont` |
| **Bebas Neue** | Regular (400) | Capitals only (it has no lowercase), so not for the main line | `github.com/dharmatype/Bebas-Neue` |
| **Archivo Narrow** | Bold (700) | Condensed labels | `github.com/Omnibus-Type/ArchivoNarrow` |
| **Archivo Black** | Regular (400) | A wide, heavy alternative | `github.com/Omnibus-Type/ArchivoBlack` |
| **DM Serif Display** | Regular (400) | An occasional serif, for a film title that needs one | `github.com/googlefonts/dm-fonts` |

## How to get them onto your computer

**Option 1: install the files in this kit.** Open `code/fonts/`, double-click a `.ttf`, and press Install
(Font Book on a Mac, the Install button on Windows). Restart Premiere or Photoshop afterwards.

**Option 2: Adobe Fonts.** If you have Creative Cloud, look for the same names at `fonts.adobe.com`.
A font you activate there appears in Premiere Pro, After Effects and Photoshop by itself, on every computer you sign in to.
If a name is not in Adobe Fonts, use option 1 or 3: the result is the same.

**Option 3: Google Fonts.** Search for the name at `fonts.google.com` and download the family.
Do this if you need letters beyond English and Western European languages (see the note below).

## Two honest notes

- The `.ttf` files here were converted from the `.woff2` files in the `@fontsource` packages on npm
  (`@fontsource/anton`, `@fontsource/dm-sans`, `@fontsource/inter`, `@fontsource/space-grotesk` and so on).
  Those packages carry the same fonts as Google Fonts. They are the **Latin subset**: English, plus the accents used
  in Western European languages. For Greek, Cyrillic, Vietnamese and so on, download the full family from Google Fonts.
- Fonts in an email signature cannot be relied on. Mail apps fall back to Arial when the brand font is not installed
  on the reader's computer. That is normal, and the signature is designed to still look right.

## How the type is set (short version)

- **The main line:** Anton, lowercase, ending in a full stop. Tracking +12 (0.012 em).
- **The supporting line:** Anton at one fifth of the main line's size, tracking +160, centred directly underneath.
- **ASTRIS over PRODUCTIONS:** PRODUCTIONS is 0.27 of the size of ASTRIS and is tracked out to the same width.
- **Small labels:** the style's text font in Bold capitals, tracking +120 to +160.
- **Anything you read for more than a second:** the style's text font, Regular.

The brand guide in each style folder (`01_Brand-Guide`) shows all of this on its "type" page.
