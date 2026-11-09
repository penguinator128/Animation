# ASTRIS brand package: progress log

Working notes so an overnight run can always resume. Code: `brand/code/`. Outputs: `brand/output/`.

## Plan (in the user's priority order)
1. Hero intros (videos/astris-hero-1..4) - heroes 1, 3, 4 reused as rendered; hero 2 re-render with 3D text
2. Eleven idents (astris-ident-01..11) + astris-idents-master.mp4 + timestamps.txt (0.6 s black gaps, stream-copy concat)
3. Stills: stills/2000/logo-*.png + stills/150/logo-*.png + stills/stills-overview.png
4. Banners (2560x1440 < 6 MB, safe area 1546x423) + profiles (1600 + 800, circle-safe)
5. Previews (banner desktop/tablet/phone crops, profile circles), then bonus idents (astris-bonus-01..)

## Status: complete (20:45)
- [x] Heroes 1-4, idents 01-11, bonus 01-05 rendered and reviewed from the encodes (review.py)
- [x] Master (1:06.125, 0.583 s black gaps) + timestamps.txt; picture bit-identical to the sources at the joins,
      sound offset 0 samples, gaps digital silence
- [x] Stills (20 badges, 2000 + 150 px) + overview
- [x] Banners + profiles (7 sets), previews (14)
- [x] checks.py: all checks passed -> output/MANIFEST.txt
- [x] Committed (no mp4s) and delivered

## Notes
- OpenCV only anti-aliases on 8-bit images: line art for stills/banners/bonus idents is drawn on uint8 layers.
- Concat note: stream-copying AAC across files drifts by the encoder priming at each join, so the master's
  audio is rebuilt from the WAV masters (encoded once) while the picture is stream-copied.

## Ident designs (each its own palette, type, pace, sound)
01 mini switcher (5.5 s) - ink, lava, circuit, balloon, wood, marble, holo foil, comic -> rainbow -> white drain; brand type
02 scribble (6 s) - cream paper, graphite pencil, hand-printed single-stroke caps (Hershey), underline + doodle star
03 graffiti (5 s) - night brick wall, sodium light, spray tag w/ drips (rainbow fade fill), stencil text
04 fly-through (9 s) - three.js: giant glossy champagne letters ASTRIS in a midnight-teal void, DOF, pull back to lockup
05 rainbow prism (4 s) - smoky dark, white beam -> glass logo -> spectrum fan -> folds back -> white glow, light-sweep text
06 glitch (3 s) - acid chartreuse/magenta/cyan on black, pixel sort, datamosh, lock-in
07 ink & water (7 s) - stable-fluids sim, rainbow inks in backlit water, condense into logo, serif text
08 cutout (4 s) - stop-motion on twos, cutting-mat background, coloured paper pieces, hopping letters
09 16mm (6 s, retro) - countdown leader, burn-in, fat-face/slab type, grain/weave/dust/halation, light leak
10 70s sunburst (5 s, retro) - rays, orange/mustard/brown/cream/teal stripes swirl into logo, groovy type, misregistration
11 80s synthwave VHS (5 s, retro) - neon grid, cut sun, chrome emblem + glint, chrome type, VHS/CRT treatment

## Bonus idents
B01 neon (5.5 s) - dark room, cold glass tubes flicker to life (pink logo, ice-blue type), wall light, buzz
B02 constellation (7 s) - stars ignite at the logo's corners, lines connect, sprocket stars, rainbow aurora
B03 fireworks (7 s) - peony/chrysanthemum/willow over hills; rainbow sphere gathers into the logo; fuse type
B04 arcade (6 s) - INSERT COIN, 8-bit logo levels up 60px -> 1px blocks, palettes grow, CRT snaps to HD
B05 bubbles (6.5 s) - thin-film interference bubbles merge into a big bubble with the logo inside; pop
