"""for every ~/review-compare/revit/<file>/ (index.tsv + cameras.tsv from c3-writer): viewer shots <id>__ours3d.png (shaded) and <id>__ours3d_hl.png (hidden line), white, --clean, --fit, same pixel size as Revit's PNG.
usage: tools/review_shots.py [FILEDIR_NAME ...]   (skips pairs that exist; model = ~/rvt-research/write-lab/scenes/<name>.rte or .rvt; run under tools/capped.sh)"""
import os, sys, subprocess, glob
H = os.path.expanduser('~'); R = H + '/review-compare/revit'; O = H + '/review-compare/viewer'; D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for name in (sys.argv[1:] or sorted(os.listdir(R))):
    d = '%s/%s' % (R, name)
    if not os.path.exists(d + '/index.tsv'): continue
    f = glob.glob('%s/rvt-research/rosetta/%s.rte' % (H, name)) or glob.glob('%s/rvt-research/write-lab/scenes/%s.r[tv][et]' % (H, name)) or glob.glob('%s/rvt-research/corpus/*/%s.rvt' % (H, name)) or glob.glob('%s/rvt-research/write-lab/**/%s.r[tv][et]' % (H, name), recursive=True)
    if not f: print('no model for', name); continue
    cams = {}
    if os.path.exists(d + '/cameras.tsv'):
        for l in open(d + '/cameras.tsv'):
            t = l.rstrip('\n').split('\t')
            if l[0] != '#' and len(t) >= 7: cams[t[0]] = (t[2].split() + t[3].split(), t[6] == 'False')
    os.makedirs('%s/%s' % (O, name), exist_ok=True)
    for l in open(d + '/index.tsv'):
        t = l.split('\t')
        if t[0] != 'VIEW': continue
        vid, kind, vname = t[1], t[2], t[4]; png = '%s/%s.png' % (d, vid)
        if not os.path.exists(png): continue
        if os.environ.get('HL3D') and kind != 'View3D': continue
        cam, ortho = cams.get(vid, (None, False))
        for suf, extra in (('', ['--style', 'shaded']), ('_hl', ['--style', 'hidden', '--vg', vid])):
            out = '%s/%s/%s__ours3d%s.png' % (O, name, vid, suf)
            if os.path.exists(out): continue
            a = [D + '/tools/capped.sh', os.environ.get('RVT_PY') or D + '/.venv/bin/python', D + '/tools/shot3d.py', f[0], vid if kind != 'View3D' else '3d', ','.join(cam) if cam else '-', out, '--clean', '--white'] + (['--fit'] if kind == 'View3D' else []) + ['--like', png] + extra + (['--ortho'] if ortho else [])
            if kind == 'View3D' and not cam: continue
            print(' '.join(a[3:])); subprocess.run(a, env=dict(os.environ, RVT_MEM_CAP='3G'), timeout=1500)
