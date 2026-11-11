# ASTRIS PRODUCTIONS: brand kit

Everything for ASTRIS PRODUCTIONS in one folder: **three complete looks to choose from**, a plain logo pack,
and the code that made all of it, so any of it can be made again with new words.

## Start here

1. **`compare-styles.png`**: the three styles side by side.
2. **`overview.png`** inside each style folder: everything in that style on one sheet.
3. **`preview.html`**: a gallery of the whole kit. Open it in a web browser (it works offline, straight from the folder).
4. **The brand guide** in each style's `01_Brand-Guide/` folder: twelve pages on how the style works.

## What is in this folder

| Folder or file | What it is |
|---|---|
| [`00_Originals/`](00_Originals/) | Your logo exactly as you sent it. Never edited. |
| [`01_Logo-Pack-Bare-Bones/`](01_Logo-Pack-Bare-Bones/) | Just the logo, no styling: an analysis report, a faithful clean version and a geometric perfect version, in every format. |
| [`02_Style-1-Red/`](02_Style-1-Red/) | **Style 1, Red.** Brick red field, cream lettering. Warm, analogue, a little funny. |
| [`03_Style-2-Yellow/`](03_Style-2-Yellow/) | **Style 2, Yellow.** Golden yellow field, near-black lettering. Sunny and confident. |
| [`04_Style-3-Wildcard/`](04_Style-3-Wildcard/) | **Style 3, Wildcard.** A two-ink risograph print: ultramarine and hot coral on cream paper. Handmade, like a zine. |
| [`code/`](code/) | The scripts that made everything. Change `brand-config.json`, run them again, and everything updates. |
| [`downloads/`](downloads/) | The kit as zip files (each under 100 MB, so some come in parts). |
| `brand-config.json` | Every word and colour the kit uses: name, taglines, contact details, socials, film titles, colours, fonts. |
| `films.txt` | The film titles the posters are made from. Edit it freely. |
| `taglines.txt` | Twelve supporting lines to choose from, and which style uses which. |
| `fonts.md` | Every font: exact name, weights, where to get it, and its licence (all free for commercial use). |
| `MANIFEST.md` | Every file in the kit, with its size and details. |
| `compare-styles.png`, `preview.html` | The comparison sheet and the gallery. |

## The three styles

All three share one system: one flat field of colour, one thing in the middle, plenty of room around it,
fine even film grain, and lettering that looks pressed on with ink.
The main line is **astris productions.** (lowercase, with a full stop), with a very small supporting line beneath it.

| | Style 1: Red | Style 2: Yellow | Style 3: Wildcard |
|---|---|---|---|
| Field | Brick Red `#C23A3A` | Golden Yellow `#F2B705` | Cream Paper `#F1E8D6` |
| Lettering | Cream Pink `#F4E3DA` | Near Black `#141210` | Ultramarine Ink `#2C46B8`, with Hot Coral Ink `#FF5E4D` behind as a soft offset shadow |
| Dark | Warm Black `#1A1210` | Near Black `#141210` (Warm Off-White `#F2EBDD` is the light) | Ink Blue-Black `#14182E` |
| Fonts | Anton + DM Sans | Anton + Inter | Anton + Space Grotesk |
| Supporting line | welcome in. | pull up a chair. | made with friends. |
| Sounds like | warm thuds, vinyl crackle, tape hiss, a low chime | clapperboard snaps, finger clicks, a sunny marimba | print-press thunks, paper slaps, stamps, a mallet chime |

Every style folder has the same ten sections:

| Section | What is in it |
|---|---|
| `01_Brand-Guide` | The guide as an A4 landscape PDF, and a picture of each page |
| `02_Logos` | The logo in the style's colours: 4 layouts x 5 colourways, PNG and SVG, plus layers for animating |
| `03_YouTube-and-Social` | Banners, profile pictures, thumbnail templates, Instagram highlight covers, posts and stories |
| `04_Intros-and-Video` | Three short intros (2, 4 and 7 s), the animated title logo (5 s, also transparent) and the end card (10 s), all 4K with sound |
| `05_Premiere-Assets` | Corner bug, three lower thirds, grain / dust / light-leak overlays, and a how-to |
| `06_Sound` | The style's sound pack (48 kHz, 24-bit WAV) and the soundtrack of every video |
| `07_Merch` | Stickers with cut lines, cap, hoodie, T-shirt, tote, bottle wrap, phone wallpapers and mock-ups |
| `08_Film-and-Paperwork` | Film posters, business card, email signature, letterhead, invoice, press kit, clapperboard and the "presents" card |
| `09_Website` | Favicons, sharing image, hero mock-ups, design tokens and a preview page |
| `10_Textures-and-LUTs` | Seamless grain and paper textures, and three colour looks (.cube) for footage |

## Your details: the [SQUARE BRACKETS]

Anything written in **[SQUARE BRACKETS]** is a placeholder waiting for you: your name, email, phone, website,
socials, ABN, address, film taglines, credits and the "about" text. Nothing about Astris has been made up:
there are no invented awards, quotes, numbers or contact details anywhere in the kit.

To fill them in, edit `brand-config.json` (and `films.txt` for the film titles), then run the build again.
Every business card, email signature, letterhead, invoice, press kit, poster, lower third and Instagram cover updates by itself.
[`code/README.md`](code/README.md) shows how, step by step.

## Things worth knowing

- **The style reference screenshot didn't come through.** The brief mentioned `reference-style.png`, but the message arrived as text only.
  Style 1 (Red) is built from your written description of it: the colours, the grain, the centred layout.
  If you add the picture to `00_Originals/`, `python3 code/analyse_reference.py` will measure its colours and grain so the red can be matched to it.
- **No photo profile pictures.** These needed `me.jpg`, which wasn't included, so they were skipped. Everything else is complete.
- **The logo used everywhere is the "geometric perfect" version.** It is your design, redrawn on its own exact grid.
  `01_Logo-Pack-Bare-Bones/logo-report.md` explains every change. To use the faithful version instead, set `"logo_version": "faithful"` in `brand-config.json` and rebuild.
- **The videos are deliberately calm.** Smooth easing, real motion blur, no camera shake or flashes, and every one ends on a still, held lockup you can cut away from.
- **No .mogrt files.** Motion Graphics Templates can only be made inside Adobe's own apps. The Premiere folder has rendered clips with transparency instead, plus instructions.
- **The merch mock-ups are drawings**, not photos of real products, and they say so.
- **Fonts:** all free for commercial use (SIL Open Font License). See `fonts.md`.

## How the files are stored on GitHub

Videos, sounds, zips and the biggest pictures are stored with **Git LFS** (Large File Storage). On github.com they open and
download like any other file. If you copy the repository with git on a computer, run `git lfs install` once first,
or those files arrive as small text pointers instead of the real thing.

No single file is larger than 100 MB. The zips in `downloads/` are split into parts to stay under that limit; each part opens on its own.

<!-- large-files:start -->
## Large files

These 31 files are 20 MB or more (985.8 MB together). All of them are stored with Git LFS, and every one is under 100 MB.
The zip parts in `downloads/` are up to 95 MB each.

| File | Size | Details |
|---|---|---|
| `03_Style-2-Yellow/04_Intros-and-Video/astris-yellow-end-card-10s-4k24.mp4` | 64.1 MB | 10.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `03_Style-2-Yellow/04_Intros-and-Video/astris-yellow-intro-c-slow-7s-4k24.mp4` | 58.2 MB | 7.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `04_Style-3-Wildcard/04_Intros-and-Video/astris-wildcard-end-card-10s-4k24.mp4` | 49.6 MB | 10.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `04_Style-3-Wildcard/04_Intros-and-Video/astris-wildcard-title-logo-alpha-5s-4k24-prores4444.mov` | 44.3 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent, sound 48 kHz |
| `04_Style-3-Wildcard/04_Intros-and-Video/astris-wildcard-intro-c-slow-7s-4k24.mp4` | 44.2 MB | 7.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `02_Style-1-Red/04_Intros-and-Video/astris-red-end-card-10s-4k24.mp4` | 43.2 MB | 0.0 s |
| `04_Style-3-Wildcard/08_Film-and-Paperwork/clapperboard/astris-wildcard-clapperboard-clap-alpha-3s-4k24-prores4444.mov` | 42.0 MB | 3.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent, sound 48 kHz |
| `04_Style-3-Wildcard/05_Premiere-Assets/corner-bug/astris-wildcard-bug-10s-4k24-prores4444.mov` | 37.7 MB | 10.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `03_Style-2-Yellow/05_Premiere-Assets/corner-bug/astris-yellow-bug-10s-4k24-prores4444.mov` | 33.0 MB | 10.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `03_Style-2-Yellow/08_Film-and-Paperwork/clapperboard/astris-yellow-clapperboard-clap-alpha-3s-4k24-prores4444.mov` | 32.5 MB | 3.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent, sound 48 kHz |
| `04_Style-3-Wildcard/08_Film-and-Paperwork/clapperboard/astris-wildcard-clapperboard-clap-3s-4k24.mp4` | 32.0 MB | 3.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `02_Style-1-Red/05_Premiere-Assets/corner-bug/astris-red-bug-10s-4k24-prores4444.mov` | 31.8 MB | 10.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `04_Style-3-Wildcard/05_Premiere-Assets/lower-thirds/astris-wildcard-lower-third-2-line-5s-4k24-prores4444.mov` | 31.6 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `02_Style-1-Red/04_Intros-and-Video/astris-red-title-logo-alpha-5s-4k24-prores4444.mov` | 29.4 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent, sound 48 kHz |
| `02_Style-1-Red/08_Film-and-Paperwork/clapperboard/astris-red-clapperboard-clap-alpha-3s-4k24-prores4444.mov` | 29.1 MB | 3.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent, sound 48 kHz |
| `04_Style-3-Wildcard/04_Intros-and-Video/astris-wildcard-intro-b-type-4s-4k24.mp4` | 28.4 MB | 4.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `04_Style-3-Wildcard/08_Film-and-Paperwork/presents-card/astris-wildcard-presents-card-3s-4k24.mp4` | 27.8 MB | 3.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `04_Style-3-Wildcard/04_Intros-and-Video/astris-wildcard-title-logo-5s-4k24.mp4` | 26.2 MB | 5.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `03_Style-2-Yellow/04_Intros-and-Video/astris-yellow-title-logo-alpha-5s-4k24-prores4444.mov` | 26.1 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent, sound 48 kHz |
| `03_Style-2-Yellow/08_Film-and-Paperwork/presents-card/astris-yellow-presents-card-3s-4k24.mp4` | 25.8 MB | 3.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `03_Style-2-Yellow/05_Premiere-Assets/lower-thirds/astris-yellow-lower-third-2-line-5s-4k24-prores4444.mov` | 24.7 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `04_Style-3-Wildcard/05_Premiere-Assets/lower-thirds/astris-wildcard-lower-third-1-bar-5s-4k24-prores4444.mov` | 24.3 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `04_Style-3-Wildcard/08_Film-and-Paperwork/presents-card/astris-wildcard-presents-card-dark-3s-4k24.mp4` | 23.6 MB | 3.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `04_Style-3-Wildcard/05_Premiere-Assets/lower-thirds/astris-wildcard-lower-third-3-stack-5s-4k24-prores4444.mov` | 23.5 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `03_Style-2-Yellow/05_Premiere-Assets/lower-thirds/astris-yellow-lower-third-1-bar-5s-4k24-prores4444.mov` | 22.8 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `02_Style-1-Red/04_Intros-and-Video/astris-red-intro-c-slow-7s-4k24.mp4` | 22.4 MB | 7.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `03_Style-2-Yellow/05_Premiere-Assets/lower-thirds/astris-yellow-lower-third-3-stack-5s-4k24-prores4444.mov` | 22.2 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `02_Style-1-Red/05_Premiere-Assets/lower-thirds/astris-red-lower-third-1-bar-5s-4k24-prores4444.mov` | 21.9 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `03_Style-2-Yellow/04_Intros-and-Video/astris-yellow-title-logo-5s-4k24.mp4` | 21.6 MB | 5.0 s, 3840 x 2160, 24 fps, H.264, sound 48 kHz |
| `02_Style-1-Red/05_Premiere-Assets/lower-thirds/astris-red-lower-third-3-stack-5s-4k24-prores4444.mov` | 21.4 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
| `02_Style-1-Red/05_Premiere-Assets/lower-thirds/astris-red-lower-third-2-line-5s-4k24-prores4444.mov` | 20.6 MB | 5.0 s, 3840 x 2160, 24 fps, ProRes 4444, transparent |
<!-- large-files:end -->
