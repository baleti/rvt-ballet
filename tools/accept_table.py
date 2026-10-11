"""aggregate ~/.cache/rvt-viewer/accept/*.json into the per-class, per-year table defined by ACCEPTANCE.md (markdown on stdout; also written to docs/ACCEPTANCE-STATUS.md).
Columns per class and year: elements, true geometry %, parametric-unproven %, approximate %, box-only %, bbox IoU>=0.95 %, volume within 2 % (of elements that have a Revit volume in gt4).
DONE flag = true >= 95 % and box <= 2 % and IoU-ok >= 95 % and (volume-ok >= 95 % where measurable)."""
import os, sys, json, glob, collections
OUT = os.path.expanduser('~/.cache/rvt-viewer/accept')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = ['SWall', 'Floor', 'Ceiling', 'ProfileRoof', 'FootPrintRoof', 'FamilyInstance', 'StairsRun', 'StairsElement', 'BaseRailing', 'RbsDuctCurve', 'RbsPipeCurve', 'RbsConduitCurve', 'CableTray',
        'CurtainGridLine', 'RoomElem', 'SiteSurface', 'WallSweep', 'ContFooting', 'Mass']


def main():
    agg = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.Counter())); files = collections.Counter()
    for f in sorted(glob.glob(os.path.join(OUT, '*.json'))):
        d = json.load(open(f)); y = d['year']; files[y] += 1
        for cls, c in d['classes'].items():
            a = agg[cls][y]
            for k in ('n', 'true', 'param_match', 'approx', 'box', 'vol_n', 'vol_ok', 'iou_n', 'iou_ok'): a[k] += c[k]
    years = sorted(files)
    lines = ['# Geometry acceptance status (per class, per year; measured on all corpus .rvt files converted so far)', '',
             'files per year: ' + ', '.join('%s: %d' % (y, files[y]) for y in years), '',
             'Cell = elements n | true % | parametric-unproven % | approximate % | box-only % | IoU>=0.95 % | volume<=2% error % (n measurable). DONE = true>=95, box<=2, IoU>=95, volume>=95.', '']
    pct = lambda a, b: '%.0f' % (100.0 * a / b) if b else '-'
    classes = [c for c in CORE if c in agg] + sorted((c for c in agg if c not in CORE and sum(agg[c][y]['n'] for y in years) >= 20), key=lambda c: -sum(agg[c][y]['n'] for y in years))
    lines.append('| class | year | n | true | param | approx | box | IoU>=.95 | vol<=2% | DONE |'); lines.append('|---|---|---|---|---|---|---|---|---|---|')
    for cls in classes:
        for y in years:
            a = agg[cls][y]
            if not a['n']: continue
            n = a['n']; done = a['true'] / n >= 0.95 and a['box'] / n <= 0.02 and (not a['iou_n'] or a['iou_ok'] / a['iou_n'] >= 0.95) and (not a['vol_n'] or a['vol_ok'] / a['vol_n'] >= 0.95)
            lines.append('| %s | %s | %d | %s | %s | %s | %s | %s | %s (%d) | %s |' % (cls, y, n, pct(a['true'], n), pct(a['param_match'], n), pct(a['approx'], n), pct(a['box'], n), pct(a['iou_ok'], a['iou_n']), pct(a['vol_ok'], a['vol_n']), a['vol_n'], 'YES' if done else 'no'))
    txt = '\n'.join(lines) + '\n'
    os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True); open(os.path.join(ROOT, 'docs', 'ACCEPTANCE-STATUS.md'), 'w').write(txt); print(txt)


if __name__ == '__main__': main()
