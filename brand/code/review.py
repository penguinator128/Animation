"""
Contact sheet straight from a finished MP4 (decoded by ffmpeg, so it shows exactly what was encoded).
Usage: python3 review.py <video.mp4> [n_frames=8] [out.jpg]
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import common as C


def sheet(video, n=8, out=None, cols=4, tw=960):
    video = Path(video)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                               capture_output=True, text=True, check=True).stdout)
    times = [dur * (k + 0.5) / n for k in range(n - 1)] + [dur - 1.5 / 24]
    th = tw * 9 // 16
    rows = (n + cols - 1) // cols
    img = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
    f = ImageFont.truetype(str(C.FONT_DIR / "montserrat-500.ttf"), 26)
    for k, t in enumerate(times):
        raw = b""
        for back in (0.0, 0.05, 0.1, 0.2):          # a seek right at the end can land past the last frame
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t - back):.3f}", "-i", str(video), "-frames:v", "1",
                                  "-vf", f"scale={tw}:{th}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                 capture_output=True, check=True).stdout
            if len(raw) == tw * th * 3:
                break
        fr = Image.frombytes("RGB", (tw, th), raw)
        d = ImageDraw.Draw(fr)
        d.text((12, 8), f"{t:.2f}s", font=f, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        img.paste(fr, ((k % cols) * tw, (k // cols) * th))
    out = Path(out) if out else C.ROOT / "test-frames" / f"review_{video.stem}.jpg"
    out.parent.mkdir(exist_ok=True)
    img.save(out, quality=85)
    return out


if __name__ == "__main__":
    print(sheet(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8, sys.argv[3] if len(sys.argv) > 3 else None))
