# Colour looks (Yellow)

Three 33-point `.cube` files that pull your footage toward this style's palette.

| File | What it does | Where to use it |
|---|---|---|
| `astris-yellow-look-1-natural-33.cube` | A gentle film grade. Blacks sit on the style's dark neutral, whites lean to its light neutral, and the signature colour gets a little more life. | Everyday footage. Start at 70 to 100 % intensity. |
| `astris-yellow-look-2-strong-33.cube` | The same idea, pushed further. | Moody scenes, b-roll, anything that should feel graded. Start at 50 to 80 %. |
| `astris-yellow-look-3-print-33.cube` | A graphic look: brightness is mapped onto the style's own colours, like a duotone print. | Title sequences, freeze frames, thumbnails. Not for skin tones in a normal scene. |

`astris-yellow-looks-preview.jpg` shows a test chart: original, natural, strong, print (left to right). The chart is
generated, not a photograph, so judge the looks on your own footage.

## Using them in Premiere Pro (Lumetri Color)

1. Select the clip (or an adjustment layer above several clips).
2. Open **Lumetri Color**, then the **Creative** section.
3. In the **Look** menu choose **Browse...** and pick a `.cube` file from this folder.
4. Use the **Intensity** slider to taste. It is normal to end up below 100 %.

Do your basic correction first (exposure, white balance) in **Basic Correction**, then add the look in **Creative**.
These looks expect normal Rec. 709 footage. If you shoot in a log profile, convert it to Rec. 709 first
(Basic Correction, Input LUT, with your camera maker's conversion LUT), then add the look.

To have them appear in the Look menu every time, copy the `.cube` files into Adobe's shared folder
(create the folders if they are not there yet), then restart Premiere:

- macOS: `/Library/Application Support/Adobe/Common/LUTs/Creative`
- Windows: `C:\Program Files\Adobe\Common\LUTs\Creative`

The same files work in DaVinci Resolve, Final Cut Pro (Custom LUT effect), After Effects (Apply Color LUT) and Photoshop
(Color Lookup adjustment layer).
