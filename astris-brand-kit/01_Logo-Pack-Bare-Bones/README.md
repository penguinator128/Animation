# 01 · Logo pack (bare bones)

Just the ASTRIS logo, cleaned up and perfected. No colours, no grain, no styling.
Your original file is untouched in `../00_Originals/`.

**Start with [`logo-report.md`](logo-report.md).** It shows what I measured, what was (and wasn't) off, and exactly what each cleaned version changes.

## The two versions

| Folder | What it is | Use it when |
|---|---|---|
| `faithful-clean/` | Your logo exactly as drawn, rebuilt as a crisp vector. Smallest possible fixes. | You want nothing about the artwork to move. |
| `geometric-perfect/` | The same design redrawn on its own grid: exact angles, mirrored hole columns, clean end holes. | Everywhere else. **This is the one the three styles use.** |

## What's inside each version

| Folder / file | Contents |
|---|---|
| `svg/` | True vector: black, white, and single-colour (uses `currentColor`, so it takes whatever colour you give it). The faithful set also has a two-tone copy that keeps your original's two whites. |
| `pdf/` | True vector PDF: black and white. |
| `png/` | Transparent background at 512, 1024, 2048, 4096 and 8192 px wide, in black, white and a neutral mid-grey "single colour" proof. |
| `1-bit/` | Pure black-and-white with no grey pixels at all, for stamps, embroidery and laser cutting. |
| `previews/` | The logo on dark and on light, 2400 x 1600. |
| `astris-logo-*-layered.svg` | Every part in its own named group (`bar`, `film-strip`, and each sprocket hole), for animation. |

`small-size-test/` shows both versions at 16, 24, 32, 48 and 64 px, real size and enlarged.
It also holds an optional small-size mark (same outline, no sprocket holes) for uses under about 24 px.

## Good to know

- **No wide or stacked layouts here.** Your logo file has no wordmark, so this pack is the icon only. Lockups with "ASTRIS PRODUCTIONS" are in each style's `02_Logos/` folder.
- **"Single colour"** means one flat colour of your choice. The PNGs are a neutral grey (#808080) so they show on any background; recolour the SVG to anything.
- The PNG and SVG files are cropped tight to the artwork. Leave clear space around the logo of at least one bar-width.

## Re-making this pack

```bash
python3 code/logo_pack/analyse_logo.py      # measures the original, writes the report + geometry
python3 code/logo_pack/build_logo_pack.py   # exports every file in this folder
```

To analyse a different logo file, change `LOGO_PATH` at the top of `code/logo_pack/analyse_logo.py`.
