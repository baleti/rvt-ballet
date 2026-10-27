"""per-view display options (visual style, sky / ground colours, silhouettes) of a converted model, computed AFTER the model is usable: the reader pass (rvt_viewdisp) is a second extraction
on cold files, so convert does not do it. Writes <model dir>/viewdisp.json = {view id: display}; the server merges it into meta.json views[].display (next load of the page)."""
import os, sys, json, subprocess
VS = {1: 'wireframe', 2: 'hiddenline', 7: 'consistent', 3: 'shaded', 4: 'shaded', 5: 'shaded', 6: 'shaded'}
_started = set()
def compute(src, out):
    sys.path.insert(0, os.path.expanduser('~/rvt-research'))
    import rvt_viewdisp
    d = {}
    for eid, r in rvt_viewdisp.view_display(src).items():
        if r.get('surfaces') is None: continue
        d[str(eid)] = {'surfaces': r['surfaces'], 'vstyle': VS.get(r['surfaces']), 'silhouettes': r.get('silhouettes'), 'bg': r.get('background_type'), 'sky': r.get('sky_color'), 'ground': r.get('ground_color'),
                       'shadows': r.get('cast_shadows'), 'hidden_lines': r.get('hidden_lines')}
    tmp = out + '.tmp'; json.dump(d, open(tmp, 'w')); os.replace(tmp, out)
def kick(mdir, src):
    """start the computation once per model dir in a niced subprocess (never blocks the server)"""
    out = os.path.join(mdir, 'viewdisp.json')
    if mdir in _started or os.path.exists(out) or not src or not os.path.exists(src) or os.environ.get('RVT_NO_VIEWDISP'): return
    _started.add(mdir)
    subprocess.Popen(['nice', '-n', '15', sys.executable, '-c', 'import sys; sys.path.insert(0, %r); from rvtballet import viewdisp; viewdisp.compute(%r, %r)' % (os.path.dirname(os.path.dirname(os.path.abspath(__file__))), src, out)],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
_merged = {}
def merged_meta(fn, mdir):
    """meta.json as bytes with views[].display merged from viewdisp.json when present (cached per mtime pair)"""
    vf = os.path.join(mdir, 'viewdisp.json')
    if not os.path.exists(vf): return None
    key = (os.path.getmtime(fn), os.path.getmtime(vf))
    c = _merged.get(fn)
    if c and c[0] == key: return c[1]
    m = json.load(open(fn)); vd = json.load(open(vf))
    for v in m.get('views', []):
        if 'display' not in v and str(v.get('id')) in vd: v['display'] = vd[str(v['id'])]
    b = json.dumps(m).encode(); _merged[fn] = (key, b); return b
