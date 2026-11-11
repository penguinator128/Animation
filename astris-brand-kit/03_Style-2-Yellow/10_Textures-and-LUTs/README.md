# Textures and colour looks (Yellow)

## Textures (`textures/`)

All tiles are 4096 x 4096 and seamless: they repeat in every direction with no visible join
(`astris-yellow-texture-seam-check.jpg` shows where the edges meet).

| File | What | How to use it |
|---|---|---|
| `textures/astris-texture-grain-fine-4096x4096.png` | Neutral film grain on mid-grey, fine | Lay over a picture or video, blend mode **Overlay**, 60 to 75 % opacity. |
| `textures/astris-texture-grain-medium-4096x4096.png` | The same, medium | Same. |
| `textures/astris-texture-grain-coarse-4096x4096.png` | The same, coarse | Same. Good for thumbnails. |
| `textures/astris-yellow-texture-field-4096x4096.png` | The style's colour with its grain | Use as a background, or behind titles. Normal blend mode. |
| `textures/astris-yellow-texture-paper-4096x4096.png` | The light neutral as paper, with fibres and grain | Use as a background, or behind titles. Normal blend mode. |
| `textures/astris-yellow-texture-dark-4096x4096.png` | The dark neutral with grain | Use as a background, or behind titles. Normal blend mode. |

The three neutral grain tiles are the same files in all three style folders.

For moving grain on video use the loops in `../05_Premiere-Assets/overlays/` instead: a still texture over video looks like a dirty window.

## Colour looks (`luts/`)

Three `.cube` files and how to load them in Premiere's Lumetri panel: see `luts/LUTS-README.md`.
