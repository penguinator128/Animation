# ASTRIS PRODUCTIONS: four 4K studio intros

All four are rendered frame by frame from code (every frame is a pure function of its time `t`), piped as raw
RGB into ffmpeg and muxed with a soundtrack that is synthesised in numpy/scipy.

| File | Length | Idea |
|---|---|---|
| `output/astris-1-go-crazy.mp4` | 10.0 s | "A star is born": hyperspace into a charging stellar core, bursts, shockwaves, light ribbons, lightning, flares, shake; an implosion and a held breath of silence; a rainbow shockwave, a white flash, and the logo slams in. 2.8 s hold. |
| `output/astris-2-3d-reveal.mp4` | 10.0 s | Real-time 3D (three.js in headless Chromium): iridescent shards cut from the logo, rings and pearls orbit around the camera, assemble centre-out, fuse; the camera pulls all the way out into purple light, with volumetric rays pouring through the sprocket holes. |
| `output/astris-3-style-switcher.mp4` | 10.0 s | Ten art directions, fast to slow (2 → 22 frames): pop yellow, 8-bit, neon, paper-cut, blueprint, leaves, cyan HUD, glass, gold, chrome. Then a flowing full rainbow, a hard landing on clean white, and the rainbow drains and drips off as the camera pulls out. |
| `output/astris-4-quick-ident.mp4` | 3.0 s | One streak of white light races down the bar's axis, snaps into the A, and splits like a prism: a rainbow band sweeps across the film strip, leaving white. Text is in by 1.4 s. |

Each MP4 has its sound baked in, and the same mix is next to it as a 24-bit / 48 kHz stereo WAV.

**Specs:** 3840×2160, 24 fps, H.264 High (CRF 15, preset slow), yuv420p, BT.709-tagged; AAC 320 kb/s, 48 kHz stereo.
Audio is mastered to a −1.5 dBFS peak (true-peak checked) with a natural reverb ring-out at the end.

## Rendering

```bash
pip install numpy scipy opencv-python-headless pillow fonttools shapely
npm install                       # three.js for intro 2 (Chromium comes from Playwright)
./render_all.sh                   # all four, or e.g. ./render_all.sh 1 4
python3 intro3_style_switcher.py --test 0,20,118,239   # full-size test frames -> test-frames/
```

On a 4-core machine the 2D intros take 3–5 minutes each. Intro 2 takes about 20 minutes because its 3D is
rendered in software WebGL.

## Swapping the logo

`common.py` has `LOGO_PATH` at the very top. Leave it empty to auto-detect `logo.svg` / `logo.png` /
`logo.jpg` next to these scripts (or in the repo root), falling back to `../assets/astris-logo-source.jpg`.
The logo is traced into exact polygons, so its real shape and proportions are kept at any size. If nothing is
found, a simple star placeholder is used and a warning is printed. For intro 2, re-run
`python3 intro2_geometry.py` after changing the logo to re-cut the 3D shards.

## Files

- `common.py`: logo tracing and drawing, vector lettering from the font outlines, the shared lockup, bloom /
  grain / vignette, the parallel renderer → ffmpeg
- `sound.py`: synth kit (rumble, sub builds, whooshes, impacts, shimmers, chimes, pads, stings, reverb,
  mastering, 24-bit WAV writer)
- `intro1_go_crazy.py`, `intro3_style_switcher.py`, `intro4_quick_ident.py`: one script per intro
- `intro2_3d_reveal.py` + `intro2_scene.html` + `intro2_render3d.js` + `intro2_geometry.py`: intro 2
  (Python composites the three.js frames, adds the atmosphere, volumetric rays and type)
- `fonts/`: Syncopate Bold (Apache 2.0) for ASTRIS, Montserrat Medium (SIL OFL 1.1) for PRODUCTIONS
