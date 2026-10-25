"""tools/side_by_side.py REVIT.png OURS.png OUT.png [LABEL]: Revit | ours composite for vision review (local only)"""
import sys
from PIL import Image, ImageDraw
a, b = Image.open(sys.argv[1]).convert('RGB'), Image.open(sys.argv[2]).convert('RGB'); h = max(a.height, b.height)
def fit(im): w = int(im.width * h / im.height); return im.resize((w, h))
a, b = fit(a), fit(b); o = Image.new('RGB', (a.width + b.width + 6, h + 18), 'white'); o.paste(a, (0, 18)); o.paste(b, (a.width + 6, 18))
d = ImageDraw.Draw(o); d.text((4, 3), 'REVIT ' + (sys.argv[4] if len(sys.argv) > 4 else ''), fill='black'); d.text((a.width + 10, 3), 'OURS (software HLR)', fill='black'); o.save(sys.argv[3])
