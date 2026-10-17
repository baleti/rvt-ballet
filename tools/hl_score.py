"""hidden-line similarity: tools/hl_score.py REVIT.png OURS.png [DIFF.png]
Dark pixels = lines. Our image is registered to Revit's by the best scale + shift (FFT cross-correlation of blurred masks, so framing differences do not count), then
precision / recall / F1 of the line pixels with a 3 px tolerance are reported (at 1000 px height) together with the found scale."""
import sys, numpy as np
from PIL import Image, ImageFilter
H = 1000
def load(p):
    im = Image.open(p).convert('L'); im = im.resize((int(im.width * H / im.height), H), Image.BILINEAR)
    m = np.asarray(im) < 170; m[-50:, -300:] = False; return m
def blur(m, r): return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * r + 1)).filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255
def resize(m, s):
    im = Image.fromarray((m * 255).astype(np.uint8)); return np.asarray(im.resize((max(8, int(im.width * s)), max(8, int(im.height * s))), Image.BILINEAR)) > 60
def place(m, dx, dy, shape):
    out = np.zeros(shape, bool); h, w = m.shape; ys, xs = max(0, dy), max(0, dx); ye, xe = min(shape[0], dy + h), min(shape[1], dx + w)
    if ye > ys and xe > xs: out[ys:ye, xs:xe] = m[ys - dy:ye - dy, xs - dx:xe - dx]
    return out
def best(R, O):
    Rb = blur(R, 4); Rb -= Rb.mean(); res = (-1, 1, 0, 0); S = (2048, 2048)
    FR = np.fft.rfft2(Rb, S)
    for s in np.linspace(.6, 1.6, 51):
        Os = resize(O, s); Ob = blur(Os, 4); Ob -= Ob.mean(); c = np.fft.irfft2(FR * np.conj(np.fft.rfft2(Ob, S)), S)
        c = c / (np.linalg.norm(Rb) * np.linalg.norm(Ob) + 1e-9); i = np.unravel_index(np.argmax(c), c.shape)
        if c[i] > res[0]: res = (c[i], s, i[1] if i[1] < 1024 else i[1] - 2048, i[0] if i[0] < 1024 else i[0] - 2048)
    return res
def dil(m, r=3): return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * r + 1))) > 0
R, O = load(sys.argv[1]), load(sys.argv[2])
cor, s, dx, dy = best(R, O); Os = place(resize(O, s), dx, dy, R.shape)
p = (Os & dil(R)).sum() / max(Os.sum(), 1); r = (R & dil(Os)).sum() / max(R.sum(), 1); f = 2 * p * r / max(p + r, 1e-9)
print('registration: scale %.3f shift (%d, %d) corr %.2f | precision %.3f recall %.3f F1 %.3f' % (s, dx, dy, cor, p, r, f))
if len(sys.argv) > 3:
    img = np.full(R.shape + (3,), 255, np.uint8); img[R & ~dil(Os)] = (230, 40, 40); img[Os & ~dil(R)] = (40, 40, 230); img[R & dil(Os)] = (60, 60, 60); Image.fromarray(img).save(sys.argv[3])
