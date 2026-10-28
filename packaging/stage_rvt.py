"""Stage rvt-ballet for the installers: app + reader modules + sheets package + Rust fast path python part, no corpus/tests/caches.
usage: python packaging/stage_rvt.py OUT_DIR [--reader DIR] [--sheets DIR] [--core DIR]   (defaults: RVT_READER_DIR / sibling checkouts via rvtplat.paths)
OUT_DIR/app has everything on one sys.path root: rvtballet/, rvtsheets/, rvt_*.py, rvt_fast.py, rvt_core*.(pyd|so), data json."""
import os, sys, shutil, glob, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
IGN = shutil.ignore_patterns('__pycache__', '*.pyc', 'tests', '.venv')
SKIP_JSON = ('agg_', 'survey', 'train_', 'gt_', 'cmp', 'ana_')


def _closure(reader):
    """reader modules reachable from the rvt*.py entry points through import statements (fmt_parser, ifcguid, ... are not named rvt_*)"""
    import re
    loc = {f[:-3] for f in os.listdir(reader) if f.endswith('.py')}
    todo = [f[:-3] for f in os.listdir(reader) if f.startswith('rvt') and f.endswith('.py')] + ['learn_enum']; seen = set()
    while todo:
        m = todo.pop()
        if m in seen or m not in loc: continue
        seen.add(m)
        txt = open(os.path.join(reader, m + '.py'), encoding='utf-8', errors='replace').read()
        for line in re.findall(r'^\s*import\s+([^#\n]+)', txt, re.M): todo += [w.split()[0].split('.')[0] for w in line.split(',') if w.split()]
        todo += re.findall(r'^\s*from\s+([A-Za-z_0-9]+)\s+import', txt, re.M)
    return sorted(seen)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--reader'); ap.add_argument('--sheets'); ap.add_argument('--core')
    a = ap.parse_args()
    from rvtballet import plat
    here = os.path.join(ROOT, 'rvtballet')
    reader = a.reader or os.environ.get('RVT_READER_DIR') or plat.paths.reader_dir(here)
    sheets = a.sheets or plat.paths.sheets_dir(here)
    core = a.core or plat.paths.core_py_dir(here)
    assert reader and sheets, 'reader and sheets directories not found'
    app = os.path.join(a.out, 'app')
    if os.path.exists(app): shutil.rmtree(app)
    os.makedirs(app)
    for d in ('rvtballet', 'web'):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(app, d), ignore=IGN)
    shutil.copytree(os.path.join(sheets, 'rvtsheets'), os.path.join(app, 'rvtsheets'), ignore=IGN)
    if os.path.isdir(os.path.join(sheets, 'web')): shutil.copytree(os.path.join(sheets, 'web'), os.path.join(app, 'web-sheets'), ignore=IGN)
    for m in _closure(reader): shutil.copy2(os.path.join(reader, m + '.py'), app)
    for f in glob.glob(os.path.join(reader, '*.json')) + glob.glob(os.path.join(reader, '*.txt')):
        b = os.path.basename(f)
        if not b.startswith(SKIP_JSON) and os.path.getsize(f) < 20 * 2 ** 20 and not b.startswith(('PARAM_', 'HANDOFF', 'FID_')): shutil.copy2(f, app)
    if core:
        for f in glob.glob(os.path.join(core, '*.py')) + glob.glob(os.path.join(core, '*.pyd')) + glob.glob(os.path.join(core, '*.so')): shutil.copy2(f, app)
    shutil.copy2(os.path.join(ROOT, 'packaging', 'requirements-rvt.txt'), os.path.join(a.out, 'requirements.txt'))
    n = sum(len(fs) for _, _, fs in os.walk(app)); sz = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(app) for f in fs)
    print('staged %d files, %.1f MB into %s' % (n, sz / 2 ** 20, app))


if __name__ == '__main__':
    main()
