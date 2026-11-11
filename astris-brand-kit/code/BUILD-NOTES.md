# Build notes

The working log of decisions made while building the kit. For how to run things, see `README.md` in this folder.

## Decisions

- **Missing inputs.** `reference-style.png` and `me.jpg` were not provided (the brief arrived as text only).
  Style 1 (Red) follows the written description; photo profile pictures were skipped. `analyse_reference.py` is ready for the screenshot.
- **Logo.** The GEOMETRIC PERFECT version is used everywhere (`logo_version` in brand-config.json). It is the original design on its
  own 19 x 16 unit grid, every slant at 26.565 degrees (1 across for every 2 up). See `01_Logo-Pack-Bare-Bones/logo-report.md`.
- **Fonts.** Anton for display in all styles. Text: DM Sans (red), Inter (yellow), Space Grotesk (wildcard). League Gothic is the stand-in for Anton.
  All SIL OFL 1.1, converted from the @fontsource packages (Latin subset).
- **Supporting lines.** red "welcome in.", yellow "pull up a chair.", wildcard "made with friends." (twelve options in taglines.txt).
- **Grain.** Unit-variance noise, softened by 0.55 px at a 1440 px design scale (scaled with the canvas), applied partly in proportion to
  the colour and partly evenly: about 7.5 % on flat colour (6 % for the risograph style). Video uses 0.85 of that, because moving grain reads stronger.
- **Ink.** Lettering is "pressed": a hair of blur, a slightly uneven edge from smooth noise, and sparse pinholes.
- **Risograph (wildcard).** Two plates that multiply on a paper texture. The blue lettering knocks the coral out beneath it; the coral
  shadow sits down-right and its plate is 2 px out of register. The dark scheme is a blue flood with the lettering left as bare paper.
- **Yellow.** Never yellow lettering on white or off-white. Full-colour logos sit on a yellow tile; the dark alternates are black with yellow.
- **Files.** Flat colour + grain is saved as 8-bit indexed PNG where that is lossless to the eye (about a third of the size).
  Big composites (posters, mock-ups) are JPEG. Every file is under 100 MB.
- **Names.** `astris-{style}-{thing}-{variant}-{size or length}.{ext}`, lowercase with dashes.
- **Nothing invented.** Every unknown is a [PLACEHOLDER] that comes from brand-config.json.

## Motion (second version, after feedback that the first videos felt shaky)

- No camera shake, no exposure flashes, no rubbery overshoot. Entrances use ease-out curves (cubic to quint), moves use smooth in-out curves.
- **Motion blur.** Each moving layer is sampled up to 17 times across a 180-degree shutter and averaged. Wipes get an analytic blur:
  the edge is spread over the distance it travels during the shutter.
- **Live grain without trembling.** The first version shifted one grain texture a few pixels every frame; the eye reads that as the picture
  jittering. Now three unrelated grain textures take turns, each moved somewhere new every time it returns: no frame's grain is a shifted copy
  of the frame before. x264 runs with `scenecut=0:bframes=0:ref=4` so it can find each texture three frames back
  (without `scenecut=0` every frame looks like a new scene and a 2 s clip is 87 MB; with it, 11 MB).
- Each intro ends on a held, still lockup. Intro C has a slow 3 % push-in. The end card barely moves (a 6 px float over 10 s) so YouTube's
  end-screen elements sit cleanly on top of it.

## Engine map

- `engine/paths.py` folders, `logo.py` geometry + rasterising, `type.py` HarfBuzz shaping, masks and SVG outlines, `core.py` the Art canvas
  (grain, press, risograph, saving), `style.py` brand-config -> Style, `lockup.py` the name and logo arrangements, `video.py` clips,
  motion blur, live grain and encoding, `sound.py` / `sfx.py` synthesis, `pdf.py` reportlab pages, `printart.py` merch artwork, `extras.py`.
- `assets/*.py`: one module per kind of asset, each with `build(style)`. Run through `build.py`.
- `make_docs.py` (READMEs + MANIFEST), `make_preview.py` (gallery), `make_zips.py` (downloads), `check_kit.py` (final checks).
