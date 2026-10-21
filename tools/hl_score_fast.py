"""Fast hidden-line registration and tolerance scoring (1000 pixel height)."""
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import fft, ndimage as nd

H = 1000


def load(path):
    with Image.open(path) as source:
        im = source.convert('L')
    im = im.resize((int(im.width * H / im.height), H), Image.Resampling.BILINEAR)
    mask = np.asarray(im) < 170
    mask[-50:, -300:] = False
    return mask


def resize(mask, scale):
    im = Image.fromarray(mask.astype(np.uint8) * 255)
    return np.asarray(im.resize((max(8, int(im.width * scale)),
                                 max(8, int(im.height * scale))),
                                Image.Resampling.BILINEAR)) > 60


def dil(mask, r=3):
    # Separable maximum filtering is identical to PIL's square MaxFilter.
    return nd.maximum_filter(mask, size=2 * r + 1, mode='nearest')


def blur(mask, r):
    im = Image.fromarray(dil(mask, r).astype(np.uint8) * 255)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255


def place(mask, dx, dy, shape):
    out = np.zeros(shape, bool)
    h, w = mask.shape
    ys, xs = max(0, dy), max(0, dx)
    ye, xe = min(shape[0], dy + h), min(shape[1], dx + w)
    if ye > ys and xe > xs:
        out[ys:ye, xs:xe] = mask[ys-dy:ye-dy, xs-dx:xe-dx]
    return out


def drop_datums(mask):
    labels, _ = nd.label(dil(mask, 9))
    keep = mask.copy()
    density = nd.uniform_filter(mask.astype(np.float32), 41)
    for i, sl in enumerate(nd.find_objects(labels), 1):
        h, w = (s.stop - s.start for s in sl)
        component = labels[sl] == i
        count = (mask[sl] & component).sum()
        if (max(h, w) > .35 * max(mask.shape) and count < .03 * h * w
                and density[sl][component].max() < .10):
            keep[sl][component] = False
    return keep


def _correlations(reference, ours, scales, size, radius, factor=1.):
    rb = blur(reference, radius)
    rb -= rb.mean()
    fr = fft.rfft2(rb, s=(size, size))
    norm_r = np.sqrt(np.sum(rb * rb, dtype=np.float64))
    results = []
    for scale in scales:
        ob = blur(resize(ours, scale * factor), radius)
        ob -= ob.mean()
        norm_o = np.sqrt(np.sum(ob * ob, dtype=np.float64))
        c = fft.irfft2(fr * np.conj(fft.rfft2(ob, s=(size, size))),
                      s=(size, size))
        index = np.unravel_index(np.argmax(c), c.shape)
        corr = float(c[index] / (norm_r * norm_o + 1e-9))
        dy, dx = (int(v if v < size // 2 else v - size) for v in index)
        results.append((corr, float(scale), dx, dy))
    return results


def best(reference, ours):
    scales = np.geomspace(.15, 8, 91)
    coarse = _correlations(resize(reference, .25), ours, scales, 512, 1, .25)
    winner = max(range(len(coarse)), key=lambda i: coarse[i][0])
    # Preserve the original scale grid and circular FFT convention at full size.
    local = scales[max(0, winner - 2):min(len(scales), winner + 3)]
    # The geometric grid skips unity; include it for unscaled drawings.
    if local[0] <= 1. <= local[-1]:
        local = np.sort(np.append(local, 1.))
    return max(_correlations(reference, ours, local, 2048, 4), key=lambda r: r[0])


def _sample(mask, ys, xs):
    valid = (ys >= 0) & (ys < mask.shape[0]) & (xs >= 0) & (xs < mask.shape[1])
    return int(np.count_nonzero(mask[ys[valid], xs[valid]])), int(valid.sum())


def score(revit_path, ours_path, diff_path=None):
    reference, ours = drop_datums(load(revit_path)), load(ours_path)
    corr, scale, dx, dy = best(reference, ours)
    dr = dil(reference)
    ry, rx = np.nonzero(reference)
    nr = max(len(ry), 1)
    bestf = (-1., scale, dx, dy)
    for candidate in scale * np.linspace(.96, 1.04, 9):
        resized = resize(ours, candidate)
        od = dil(resized)
        oy, ox = np.nonzero(resized)
        for ddx in range(-6, 7, 2):
            for ddy in range(-6, 7, 2):
                x, y = dx + ddx, dy + ddy
                matched, count = _sample(dr, oy + y, ox + x)
                p = matched / max(count, 1)
                matched_r, _ = _sample(od, ry - y, rx - x)
                r = matched_r / nr
                f = 2 * p * r / max(p + r, 1e-9)
                if f > bestf[0]:
                    bestf = (f, float(candidate), x, y)
    _, scale, dx, dy = bestf
    placed = place(resize(ours, scale), dx, dy, reference.shape)
    # Final dilation occurs AFTER clipping, as in the reference.
    dp = dil(placed)
    p = float((placed & dr).sum() / max(placed.sum(), 1))
    r = float((reference & dp).sum() / nr)
    f = 2 * p * r / max(p + r, 1e-9)
    if diff_path is not None:
        img = np.full(reference.shape + (3,), 255, np.uint8)
        img[reference & ~dp] = (230, 40, 40)
        img[placed & ~dr] = (40, 40, 230)
        img[reference & dp] = (60, 60, 60)
        Image.fromarray(img).save(diff_path)
    return dict(scale=scale, dx=dx, dy=dy, corr=corr, precision=p, recall=r, f1=f)


def main():
    result = score(*sys.argv[1:])
    print('registration: scale %.3f shift (%d, %d) corr %.2f | precision %.3f recall %.3f F1 %.3f'
          % tuple(result[k] for k in ('scale', 'dx', 'dy', 'corr', 'precision', 'recall', 'f1')))


if __name__ == '__main__':
    main()
