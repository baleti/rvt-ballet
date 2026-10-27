"""tools/gen_icons.py [OUTDIR]: the dwg-ballet / rvt-ballet icon family drawn in code (same tile shape, palette and line weight, no text).
dwg-ballet: drafting corner (two lines, a dimension arc); rvt-ballet: isometric box. Writes <OUTDIR>/<size>x<size>/apps/{dwg,rvt}-ballet.png for the hicolor sizes."""
import math, os, sys
from PIL import Image, ImageDraw
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/.local/share/icons/hicolor')
TILE, FG, ACC = (32, 26, 28), (235, 224, 225), (255, 176, 202)   # ballet-ui dark surface, foreground, accent
SIZES = [16, 24, 32, 48, 64, 96, 128, 256, 512]


def draw(kind, n):
    S = 4 * 512; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); u = S / 100.0
    d.rounded_rectangle([4 * u, 4 * u, 96 * u, 96 * u], radius=22 * u, fill=TILE)
    w = int(5 * u)
    def line(p, q, c=FG): d.line([p[0] * u, p[1] * u, q[0] * u, q[1] * u], fill=c, width=w)
    def dot(p, c=FG):
        r = w / 2; d.ellipse([p[0] * u - r, p[1] * u - r, p[0] * u + r, p[1] * u + r], fill=c)
    if kind == 'dwg':
        a, b, c = (26, 74), (26, 26), (74, 74)
        line(a, b); line(a, c); dot(a); dot(b); dot(c)
        d.arc([26 * u - 30 * u, 74 * u - 30 * u, 26 * u + 30 * u, 74 * u + 30 * u], start=-90, end=0, fill=ACC, width=w)
        line((38, 62), (62, 38), ACC) if False else None
    else:
        cx, cy, r = 50, 52, 26
        top = [(cx, cy - r), (cx + r * .866, cy - r / 2), (cx, cy), (cx - r * .866, cy - r / 2)]
        down = [(cx - r * .866, cy - r / 2), (cx, cy), (cx, cy + r), (cx - r * .866, cy + r / 2)]
        right = [(cx, cy), (cx + r * .866, cy - r / 2), (cx + r * .866, cy + r / 2), (cx, cy + r)]
        for poly in (top, down, right):
            pts = poly + [poly[0]]
            for i in range(4): line(pts[i], pts[i + 1], ACC if poly is top else FG)
        for p in top + [down[3], right[2], right[3]]: dot(p, ACC if p in top else FG)
    return im.resize((n, n), Image.LANCZOS)


for n in SIZES:
    p = os.path.join(OUT, '%dx%d' % (n, n), 'apps'); os.makedirs(p, exist_ok=True)
    for k in ('dwg', 'rvt'): draw(k, n).save(os.path.join(p, '%s-ballet.png' % k))
print('icons written to', OUT)
