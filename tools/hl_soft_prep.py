"""tools/hl_soft_prep.py FILE.rvt NAME: copy the cached vg3d JSON (resolved view graphics, rvtballet/vg3d.py) of every view in ~/review-compare/revit/NAME/cameras.tsv to ~/review-compare/vg3d/NAME/<vid>.json
(no decoding: the viewer server caches them when a view is opened / tools/shot3d.py --vg ran), so tools/hl_soft_all.py can run on a host without the rvt-sheets venv."""
import sys, os, hashlib, shutil
src, name = os.path.abspath(sys.argv[1]), sys.argv[2]; H = os.path.expanduser('~'); VER = 2
out = '%s/review-compare/vg3d/%s' % (H, name); os.makedirs(out, exist_ok=True); n = 0
for l in open('%s/review-compare/revit/%s/cameras.tsv' % (H, name)):
    if l[0] == '#': continue
    vid = l.split('\t')[0]
    key = hashlib.sha1(('%s|%s|%s|%d' % (src, os.path.getmtime(src), vid, VER)).encode()).hexdigest()[:16]
    f = '%s/.cache/rvt-ballet/vscene/vg3d-%s.json' % (H, key)
    if os.path.exists(f): shutil.copy(f, '%s/%s.json' % (out, vid)); n += 1
    else: print('no cached vg3d for view', vid)
print('copied', n)
