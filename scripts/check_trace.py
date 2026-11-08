import json, sys
from PIL import Image, ImageDraw, ImageChops
d = json.load(open('assets/logo-trace.json'))
im = Image.new('L', (d['w'], d['h']), 0); dr = ImageDraw.Draw(im)
for s in d['shapes']:
    if s['parent'] == -1: dr.polygon([tuple(p) for p in s['pts']], fill=255)
for s in d['shapes']:
    if s['parent'] != -1: dr.polygon([tuple(p) for p in s['pts']], fill=0)
src = Image.open('assets/astris-logo-source.jpg').convert('L').point(lambda v: 255 if v > 128 else 0)
diff = ImageChops.difference(im, src)
bad = sum(1 for v in diff.getdata() if v)
print('mismatched px:', bad, 'of', d['w']*d['h'], f'({100*bad/(d["w"]*d["h"]):.3f}%)')
