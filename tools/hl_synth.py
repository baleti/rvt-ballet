"""deterministic synthetic line drawings for tools/hl_score tests: make_pair(seed, outdir) writes revit.png (1500x743, black lines on white) and ours.png (the same drawing scaled 1.10, shifted (40, 25), 15% of the lines dropped, a few extra lines) and returns both paths"""
import os, random
from PIL import Image, ImageDraw
W, H = 1500, 743
def make_pair(seed, outdir):
    rnd = random.Random(seed); os.makedirs(outdir, exist_ok=True)
    items = []
    for _ in range(110):
        x, y = rnd.randint(60, W - 260), rnd.randint(60, H - 160)
        if rnd.random() < .5: items.append(('l', x, y, x + rnd.randint(40, 240), y + rnd.choice([0, 0, rnd.randint(-40, 40)]), rnd.choice([2, 3, 4])))
        else: items.append(('l', x, y, x + rnd.choice([0, 0, rnd.randint(-40, 40)]), y + rnd.randint(40, 140), rnd.choice([2, 3, 4])))
    for _ in range(18):
        x, y = rnd.randint(60, W - 300), rnd.randint(60, H - 200); items.append(('r', x, y, x + rnd.randint(30, 200), y + rnd.randint(20, 120), 2))
    def draw(its, s, dx, dy, name):
        im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
        for k, x0, y0, x1, y1, w in its:
            p = [x0 * s + dx, y0 * s + dy, x1 * s + dx, y1 * s + dy]
            (d.line if k == 'l' else d.rectangle)(p, fill=(0, 0, 0), width=max(1, round(w * s))) if k == 'l' else d.rectangle(p, outline=(0, 0, 0), width=max(1, round(w * s)))
        path = os.path.join(outdir, name); im.save(path); return path
    kept = [it for it in items if rnd.random() > .15]
    extra = [('l', x, y, x + rnd.randint(30, 120), y, 3) for x, y in [(rnd.randint(60, W - 200), rnd.randint(60, H - 100)) for _ in range(6)]]
    return draw(items, 1.0, 0, 0, 'revit.png'), draw(kept + extra, 1.10, 40, 25, 'ours.png')
if __name__ == '__main__':
    import sys; print(*make_pair(int(sys.argv[1]), sys.argv[2]))
