# ASTRIS PRODUCTIONS — brand package

Everything here is made from code. Every video frame is a pure function of its time `t`, rendered at 4K, piped
straight into ffmpeg, and muxed with a soundtrack that is synthesised in numpy/scipy (no samples, no stock).
The logo is traced from `assets/astris-logo-source.jpg` into exact polygons, so its real shape and proportions
are kept everywhere.

`output/MANIFEST.txt` lists every file with its duration, size and the checks it passed.

## What's in `output/`

| Folder | What |
|---|---|
| `videos/` | 4 hero intros, 11 idents, the idents master (+ `timestamps.txt`), 5 bonus idents |
| `audio/` | the soundtrack of every video as a 24-bit / 48 kHz stereo WAV (same mix as in the MP4) |
| `stills/2000/`, `stills/150/` | one badge-style logo per video, 2000×2000 and 150×150, transparent, no text |
| `stills/stills-overview.png` | contact sheet of all badges (with each real 150 px file shown 1:1) |
| `banners/` | YouTube banners, 2560×1440 PNG, all under 6 MB, logo + type inside the 1546×423 safe area |
| `profiles/` | matching profile pictures, 1600×1600 + 800×800, everything important inside the circle |
| `previews/` | each banner on TV / desktop / tablet / phone (+ channel-page mock-ups); each profile in its circle at real sizes |

**Video spec:** 3840×2160, 24 fps, H.264 High (CRF 15, preset slow), yuv420p, BT.709; AAC 320 kb/s, 48 kHz
stereo. Audio is mastered to −1.5 dBFS peak (true-peak checked) and always rings out to silence.

### Hero intros
| File | Length | Idea |
|---|---|---|
| `astris-hero-1-go-crazy.mp4` | 10.0 s | "A star is born": hyperspace into a charging stellar core, the biggest hit lands on the logo reveal, 2.8 s hold |
| `astris-hero-2-3d-reveal.mp4` | 10.0 s | three.js: iridescent shards with a rainbow shimmer assemble the logo; the 3D type stands up in the scene as the camera pulls out into purple light and volumetric rays |
| `astris-hero-3-style-switcher.mp4` | 10.0 s | ten art directions, fast to slow, then rainbow, then clean white |
| `astris-hero-4-quick-ident.mp4` | 3.0 s | one streak of light snaps into the A and splits like a prism |

### Idents (in the master in this order, 0.583 s of black between each)
| # | Length | Look | Type |
|---|---|---|---|
| 01 mini switcher | 5.75 s | comic, ink, lava, circuit, balloon, wood, marble, holo foil → rainbow → white | Syncopate / Montserrat |
| 02 scribble | 6.4 s | graphite pencil on cream paper, hand-lettered caps, underline + doodle star | Hershey single-stroke |
| 03 graffiti | 5.0 s | night brick wall under a lamp, spray tag with drips and a rainbow fade | Big Shoulders Stencil |
| 04 fly-through | 9.0 s | three.js: a slow flight through giant gold letters, pull back to the lockup | Playfair Display / Cormorant |
| 05 rainbow prism | 4.2 s | a white beam hits a glass logo and fans into a spectrum, folds back to white | Italiana |
| 06 glitch | 3.0 s | pixel sort, datamosh, RGB tear, locks in clean | Rubik Mono One / Space Mono |
| 07 ink & water | 7.0 s | a real fluid sim: rainbow inks bloom in backlit water and gather into the logo | Cormorant Garamond |
| 08 cutout | 4.0 s | stop-motion on twos, paper pieces on a cutting mat, hopping letters | Luckiest Guy / Lilita One |
| 09 16mm (retro) | 6.0 s | countdown leader, burn-in, gate weave, dust, halation, light leak, deco frame | Abril Fatface / Rokkitt |
| 10 70s sunburst (retro) | 5.0 s | spinning sunburst, five stripes swirl into the logo, print misregistration | Shrikhand / Righteous |
| 11 80s synthwave (retro) | 5.0 s | neon grid, cut sun, chrome emblem, VHS tracking + CRT | Orbitron / Mr Dafoe |

Rainbow shows up in 01 (a full-spectrum style), 03 (the spray fade), 05 (the prism fan) and 07 (the inks), each in a
different way, and again in the bonus 02, 03, 04 and 05.

### Bonus idents (not in the master)
| File | Length | Idea |
|---|---|---|
| `astris-bonus-01.mp4` | 5.5 s | neon sign: cold glass tubes sputter to life in a dark room, light spills over the bricks, transformer buzz |
| `astris-bonus-02.mp4` | 7.0 s | constellation: stars ignite at the logo's corners and connect, sprocket holes become tiny stars, rainbow aurora |
| `astris-bonus-03.mp4` | 7.0 s | fireworks: three bursts, then a rainbow sphere that hangs and gathers into the logo; a fuse lights the type |
| `astris-bonus-04.mp4` | 6.0 s | arcade: INSERT COIN, the 8-bit logo levels up (4 → 8 → 16 → 64 → 256 colours) until the CRT snaps to HD |
| `astris-bonus-05.mp4` | 6.5 s | soap bubbles with real thin-film colours merge into one big bubble around the logo, then pop |

### Banners and profile pictures
`1-retro-grainy` (16mm), `2-retro-vhs` (synthwave), `3-retro-70s`, `4-surprise-constellation` (the logo as a star
chart under a rainbow aurora), and bonus `rainbow-collage`, `neon`, `blueprint`. Each banner has a matching profile
picture. The safe-area and circle checks are measured from the actual drawn shapes, not guessed.

## Re-rendering (`code/`)

```bash
pip install numpy scipy opencv-python-headless pillow fonttools shapely
npm install                                # three.js for the 3D pieces (hero 2, ident 04, 3D stills); needs Playwright + Chromium
python3 ident05_prism.py --test 10,40,100  # full-size test frames -> code/test-frames/
python3 ident05_prism.py                   # render one video (+ its WAV)
./queue.sh                                 # render everything listed in queue.txt, one job at a time
python3 master.py                          # join the 11 idents -> astris-idents-master.mp4 + timestamps.txt
python3 stills.py && python3 banners.py && python3 previews.py
python3 checks.py                          # verify everything, write output/MANIFEST.txt
python3 review.py ../output/videos/astris-ident-05.mp4   # contact sheet from a finished MP4
```

2D pieces take 2–8 minutes each on 4 cores; the 3D ones (software WebGL) 20–40 minutes.

**The master** stream-copies every ident's picture (no frame is re-encoded). Its audio track is rebuilt
sample-exactly from the original WAV masters and encoded once, because stream-copying AAC across files shifts the
sound by the encoder's start-up padding at every join. So nothing is encoded twice, and every join is in sync
(checked: the picture is bit-identical to each ident, and each ident's sound lands at 0 samples offset).
`python3 master.py --parts DIR` also writes the master as self-contained pieces for places with an upload size
limit, built the same way: `part1of3-a` (idents 01–02), `part1of3-b` (03–04), `part2of3` (05–08), `part3of3` (09–11).
Played back to back they are exactly the master.

**Swapping the logo:** `code/common.py` has `LOGO_PATH` at the very top. Leave it empty to auto-detect
`logo.svg` / `logo.png` / `logo.jpg` next to the scripts or in the repo root, falling back to
`assets/astris-logo-source.jpg`; a star placeholder is used (with a warning) if nothing is found. For the 3D pieces,
re-run `python3 geometry3d.py` and `python3 ident04_geometry.py` after changing it.

## Code map
- `common.py` logo tracing, vector lettering, lockup, finishing (bloom, grain, vignette), the renderer → ffmpeg
- `kit.py` fonts, flexible lockups, paper/film/print/CRT textures, metal shading, runners for 2D and 3D pieces
- `sound.py`, `sfx.py` synthesiser, effects, reverb, mastering, WAV writer
- `hero*.py`, `ident*.py`, `bonus*.py` one script per video; `*_scene.html` + `render3d.js` for three.js scenes
- `stills.py`, `banners.py`, `previews.py`, `master.py`, `checks.py`, `review.py`
- `fonts/` all open-licensed (SIL OFL / Apache 2.0), licences in `fonts/licenses/`
