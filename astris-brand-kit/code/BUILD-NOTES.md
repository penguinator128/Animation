# Build notes (working log, kept up to date while the kit is being made)

## Decisions
- Reference screenshot (reference-style.png) and me.jpg were NOT provided -> red style built from the written brief; photo profiles skipped.
- Logo: GEOMETRIC PERFECT is used across the kit (`logo_version` in brand-config.json). 19 x 16 unit grid; see 01_Logo-Pack-Bare-Bones/logo-report.md.
- Display font: Anton (all styles). Text fonts: DM Sans (red), Inter (yellow), Space Grotesk (wildcard). League Gothic is the documented alternative.
- Taglines: red "welcome in.", yellow "pull up a chair.", wildcard "made with friends."
- Grain: amount 0.075 (wildcard 0.06), sigma 0.55 px at 1440-px design scale, scales with canvas (Art.s = min(w,h)/1440, min 1).
- Flat-colour + grain stills are saved as 8-bit indexed PNG (256 colours) = lossless here, ~1/3 size. Big composite previews are JPG.
- Wildcard = two-ink risograph: blue lettering knocks out coral shadow (offset down-right), plates multiply, coral plate misregistered 2 px,
  "dark" scheme = blue flood with paper knock-out lettering.
- Video: live grain = a tileable grain texture shifted randomly each frame (motion-compensable -> small files at CRF 16).
- File naming: astris-{style}-{asset}-{variant}-{size}.{ext}

## Engine map
- engine/paths.py (folders), logo.py (geometry + raster), type.py (HarfBuzz shaping, masks, SVG outlines), core.py (Art canvas, grain, press, riso, save),
  style.py (config -> Style), lockup.py (name_line, stacked, vertical, horizontal)
- assets/*.py: one module per asset group, each with build(style). Run via: python3 code/build.py <step> [--style x]

## Status
- [x] 01 logo pack   - [x] banners + profiles (assets/youtube.py)
- [ ] logos  [ ] guide  [ ] intros/title/end card  [ ] stickers  [ ] business card  [ ] email signature  [ ] IG covers  [ ] posters
- [ ] merch  [ ] press kit/letterhead/invoice  [ ] clapper/presents  [ ] website  [ ] premiere (bug, lower thirds, overlays)  [ ] sound  [ ] textures/LUTs
- [ ] overviews, compare-styles, preview.html, READMEs, MANIFEST, zips, checks, push
