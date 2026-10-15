"""aggregate ~/.cache/rvt-viewer/accept/*.json into the per-class, per-year table defined by ACCEPTANCE.md (markdown on stdout; also written to docs/ACCEPTANCE-STATUS.md).
Columns per class and year: elements, true geometry %, parametric-unproven %, approximate %, box-only %, bbox IoU>=0.95 %, volume within 2 % (of elements that have a Revit volume in gt4).
DONE flag = true >= 95 % and box <= 2 % and IoU-ok >= 95 % and (volume-ok >= 95 % where measurable)."""
import os, sys, json, glob, collections
OUT = os.path.expanduser('~/.cache/rvt-viewer/accept')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = ['SWall', 'Floor', 'Ceiling', 'ProfileRoof', 'FootPrintRoof', 'FamilyInstance', 'StairsRun', 'StairsElement', 'BaseRailing', 'RbsDuctCurve', 'RbsPipeCurve', 'RbsConduitCurve', 'CableTray',
        'CurtainGridLine', 'RoomElem', 'SiteSurface', 'WallSweep', 'ContFooting', 'Mass']


def reader_table():
    """class -> (accurate %, true-off %, box %) from ~/rvt-research/NOTES.md (reader session 176)"""
    out = {}; f = os.path.expanduser('~/rvt-research/NOTES.md')
    try: txt = open(f).read()
    except OSError: return out
    a = txt.find('Per-class / per-year geometry table')
    if a < 0: return out
    import re
    for l in txt[a:a + 20000].split('\n'):
        m = re.match(r'^(\w+)\s+(\d+)\s+([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%', l)
        if m: out[m.group(1)] = (m.group(3), m.group(4), m.group(5))
        if l.startswith('per year'): break
    return out


def main():
    agg = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.Counter())); files = collections.Counter()
    for f in sorted(glob.glob(os.path.join(OUT, '*.json'))):
        d = json.load(open(f)); y = d['year']; files[y] += 0.5 if ('__mesh' in f or '__analytic' in f) else 1
        for cls, c in d['classes'].items():
            a = agg[cls][y]
            for k in ('n', 'true', 'param_match', 'approx', 'box', 'vol_n', 'vol_ok', 'iou_n', 'iou_ok', 'acc', 'toff', 'unj'): a[k] += c.get(k, 0)
    years = sorted(files)
    lines = ['# Geometry acceptance status (per class, per year; measured on all corpus .rvt files converted so far)', '',
             'files per year (big files evaluated in two low-memory halves count 0.5 each): ' + ', '.join('%s: %g' % (y, files[y]) for y in years), '',
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
    lines += ['', '## Same data in the reader table\'s definition (NOTES.md "Per-class / per-year geometry table"), side by side', '',
              'ACCURATE = mesh/solid whose volume is within 2 % of Revit\'s (or, without a Revit volume, bbox IoU >= 0.95); true-off = a mesh exists but fails that; own approx = our parametric/approximate rebuild (not claimed accurate); box = box only; unjudged = mesh without a reference to judge it. Reader columns are 176\'s numbers (partial run, other element sampling).', '',
              '| class | n | viewer accurate | true-off | own approx | box | unjudged | reader accurate | reader true-off | reader box |', '|---|---|---|---|---|---|---|---|---|---|']
    rd = reader_table()
    for cls in classes:
        n = sum(agg[cls][y]['n'] for y in years)
        if not n: continue
        S = lambda k: sum(agg[cls][y][k] for y in years)
        rr = rd.get(cls)
        lines.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s |' % (cls, n, pct(S('acc'), n), pct(S('toff'), n), pct(S('param_match') + S('approx'), n), pct(S('box'), n), pct(S('unj'), n), *(rr if rr else ('-', '-', '-'))))
    txt = '\n'.join(lines) + '\n'
    os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True); open(os.path.join(ROOT, 'docs', 'ACCEPTANCE-STATUS.md'), 'w').write(txt); print(txt)


if __name__ == '__main__': main()
