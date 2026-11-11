# Premiere Pro assets (Red)

Everything here drops straight onto a Premiere Pro timeline. Nothing needs a plug-in.

**One honest note first:** there are no `.mogrt` Motion Graphics Templates in this kit. Those can only be made inside
After Effects or Premiere, and this kit was built with code. Instead you get rendered clips with transparency
(ProRes 4444) that behave like any other clip, and a one-line command to re-render the lower thirds with your own names.

## What is in this folder

| Folder | What | How to use it |
|---|---|---|
| `corner-bug/` | The logo as a watermark: PNG at 512, 256 and 128 px (light and colour), and a 10 s clip that fades in, sits at 70 % and fades out | Put it on the top video track, bottom-right. The clip is already positioned inside the title-safe area. For a whole film use a PNG and set Opacity to 70 %. |
| `corner-bug/astris-red-youtube-watermark-150x150.png` | YouTube's own watermark slot | YouTube Studio, Customisation, Branding, Video watermark. |
| `lower-thirds/` | Three designs, 5 s each, with transparency, plus a still PNG of each | Drop on a track above your footage. They animate in, hold, and animate out. To hold longer, use the still PNG between two cuts of the clip. |
| `overlays/` | 4K, 10 s seamless loops: film grain (fine, medium, coarse), dust and scratches, light leaks | Put on a track above your footage and set the blend mode (table below). Loop by duplicating the clip end to end. |

Sound effects are in `../06_Sound/`, textures and colour looks in `../10_Textures-and-LUTs/`, and the intros,
title logo and end card in `../04_Intros-and-Video/`.

## Blend modes for the overlays

Select the overlay clip, open Effect Controls, Opacity, Blend Mode.

| Overlay | Blend mode | Opacity to start with |
|---|---|---|
| `astris-overlay-grain-fine / medium / coarse` (grey) | **Overlay** (or Soft Light for less) | 60 to 75 % matches the grain in the brand graphics. 100 % is strong. |
| `astris-overlay-dust-and-scratches` (white on black) | **Screen** | 40 to 70 % |
| `astris-red-overlay-light-leaks` (colour on black) | **Screen** (or Linear Dodge (Add) for more) | 50 to 100 % |

The grain and dust loops are colour-neutral, so they are the same files in all three style folders.

## Transparent clips (ProRes 4444)

The `.mov` files carry an alpha channel. Premiere reads it automatically. If a clip ever shows a black background,
right-click it in the Project panel, Modify, Interpret Footage, Alpha Channel, and make sure "Ignore Alpha Channel" is off
and "Premultiplied Alpha" is off (these files use straight alpha).

## Putting your own name on the lower thirds

The text comes from `brand-config.json` at the top of the kit:

```json
"lower_thirds": [
  {"name": "[YOUR NAME]", "title": "[YOUR ROLE]"},
  {"name": "[GUEST NAME]", "title": "[GUEST TITLE]"},
  {"name": "[CREW NAME]", "title": "[CREW ROLE]"}
]
```

Design 1 uses the first entry, design 2 the second, design 3 the third. Change the names, then run:

```
python3 code/build.py premiere --style red lower-thirds
```

Each clip takes under a minute to render. See `code/README.md` for the one-time setup.

## Sequence settings these were made for

3840 x 2160, 24 fps, Rec. 709. They scale cleanly to 1920 x 1080 (set Scale to 50 % or use "Set to Frame Size").
At other frame rates Premiere will conform them; the animations are short enough that it is not noticeable.
