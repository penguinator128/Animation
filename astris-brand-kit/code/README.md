# code: how the kit is made (and made again)

Every file in the three style folders and the logo pack was made by the scripts in this folder.
Nothing was drawn by hand, so anything can be made again: change the words, run a command, and the files update.

## The one file to edit

**`../brand-config.json`** holds every word and colour the kit uses:

| Section | What it controls |
|---|---|
| `brand` | The name, the lowercase line ("astris productions."), the "presents" line, the about text, the end-card line |
| `person` | Your name, role, email, phone, website, location, address and ABN (business cards, signatures, letterhead, invoice, press kit) |
| `social` | Your YouTube, Instagram, TikTok and Letterboxd handles |
| `invoice` | The invoice title, tax line and currency |
| `taglines` | The twelve supporting lines (each style's own line is under `styles`) |
| `lower_thirds` | The names and titles on the three lower thirds |
| `instagram_highlights` | The names of the twelve highlight covers |
| `styles` | Each style's colours, fonts, supporting line, grain and ink settings |
| `logo_version` | `"geometric"` (used now) or `"faithful"` |

**`../films.txt`** lists the films, one per line. A note in brackets after a title, like `Ocean (working title)`,
appears small under the title on the poster. Lines starting with `#` are ignored.

Anything still in [SQUARE BRACKETS] shows up as a placeholder on the artwork, so nothing unfinished goes out by accident.

## Setting up (once)

You need **Python 3.10 or newer**, **ffmpeg**, and **poppler** (for `pdftoppm`):

- macOS (with Homebrew): `brew install python ffmpeg poppler`
- Windows: install Python from python.org, and ffmpeg and poppler from their websites (add both to your PATH)
- Linux: `sudo apt install python3-pip ffmpeg poppler-utils`

Then the Python packages:

```bash
pip install numpy scipy pillow opencv-python-headless fonttools brotli uharfbuzz shapely reportlab pypdf
```

The fonts are already here (`fonts/`), so nothing else needs installing. Run every command from the kit's top folder.

## Making things

```bash
python3 code/build.py list                            # every step and what it makes
python3 code/build.py paper                           # one step, all three styles
python3 code/build.py paper --style red               # one step, one style
python3 code/build.py premiere --style red lower-thirds   # one part of a step
```

| Step | What it makes | Time (all styles) |
|---|---|---|
| `youtube` | Banners A-D with masters, safe-area guide, device previews, profile pictures | 2 min |
| `logos` | Logo files in the style's colours, and the animation-ready layers | 3 min |
| `social` | Thumbnail templates, Instagram highlight covers, posts and stories | 1 min |
| `posters` | One poster per film in films.txt, A3 and 2:3 | 3 min |
| `stickers` | Twelve stickers with cut lines, and the A4 sheet | 2 min |
| `paper` | Business card, email signature, letterhead, invoice, press kit | 20 s |
| `film` | Clapperboard (stills and the 3 s clap) and the "presents" card | 8 min |
| `merch` | Cap, hoodie, T-shirt, tote, bottle wrap, wallpapers, mock-ups | 4 min |
| `web` | Favicons, sharing image, hero mock-ups, tokens, preview page | 15 s |
| `textures` | Seamless textures and the .cube colour looks | 1 min |
| `sound` | The sound pack | 1 min |
| `intros` | Intros A, B and C, the title logo (on colour and transparent) and the end card | 25 min |
| `premiere` | Corner bug, lower thirds, overlay loops, PREMIERE-README | 12 min |
| `guide` | The brand guide (build this after the others: it shows their pictures) | 2 min |
| `overview` | `overview.png` for each style and `compare-styles.png` (also last) | 2 min |

Times are from a 4-core machine. The videos are the slow part.

### After changing your details

```bash
python3 code/build.py paper        # business cards, signature, letterhead, invoice, press kit
python3 code/build.py posters      # if films.txt changed
python3 code/build.py premiere lower-thirds   # if the lower-third names changed
python3 code/make_docs.py          # refresh the READMEs and MANIFEST.md
python3 code/make_zips.py          # refresh the zips in downloads/
```

### Other scripts

| Script | What it does |
|---|---|
| `logo_pack/analyse_logo.py` | Measures your original logo and writes `logo-report.md`, its pictures, and the geometry the kit is built from |
| `logo_pack/build_logo_pack.py` | Makes every file in `01_Logo-Pack-Bare-Bones/` |
| `analyse_reference.py` | Measures a style reference picture (put it at `00_Originals/reference-style.png`) |
| `make_docs.py` | Writes `MANIFEST.md` and the generated READMEs |
| `make_zips.py` | Makes the zips in `downloads/`, each under 100 MB |
| `check_kit.py` | The final checks: every file opens, sizes and lengths are right, no sound clips, no file over 100 MB |

## How it fits together

| Folder | What is in it |
|---|---|
| `engine/` | The shared design engine. `logo.py` (logo geometry), `type.py` (lettering, shaped with HarfBuzz), `core.py` (canvas, grain, ink, the risograph print), `lockup.py` (the name and logo arrangements), `style.py` (reads brand-config.json), `video.py` (4K video, motion blur, live grain), `sound.py` and `sfx.py` (sound), `pdf.py` (PDFs with real text), `printart.py` (merch artwork), `extras.py` (placeholders, icons), `paths.py` (folders) |
| `assets/` | One module per kind of asset, each with a `build(style)` function |
| `logo_pack/` | The logo analysis and the bare-bones pack |
| `fonts/` | The fonts and their licences |
| `_work/` | Scratch files while building (not kept in git) |

Two ideas run through everything:

- **One system, three settings.** Every asset is drawn once, in code, and the style only changes the colours, fonts, grain and ink.
  That is why the three styles line up exactly.
- **Grain and ink are part of the drawing.** Lettering is "pressed" (a hair of bleed, a slightly uneven edge, the odd pinhole)
  and fine film grain is laid over every picture. In video the grain is alive: three unrelated grain textures take turns,
  so every frame has fresh grain without anything appearing to slide or tremble.
