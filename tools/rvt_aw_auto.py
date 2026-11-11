#!/usr/bin/env python3
"""rvt_aw_auto.py SRC.rvt DST.rvt X0 Y0 X1 Y1 [HEIGHT] [YEAR]: add one straight wall to an ARBITRARY project by discovering level/type/phase/likeWall
from its first existing wall (SWall), then calling the write-lab clone-and-patch (rvtedit aw). Autodesk samples / synthetic only; writes DST only."""
import os, sys, subprocess
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'):
    sys.path.insert(0, os.path.expanduser(p))
import rvt_geometry as G
import rvtedit
src, dst = sys.argv[1], sys.argv[2]; x0, y0, x1, y1 = sys.argv[3:7]
if os.path.realpath(src) == os.path.realpath(dst): sys.exit('REFUSED: output path equals the input file')
if os.path.exists(dst) and (os.path.samefile(src, dst) or os.stat(dst).st_nlink > 1): sys.exit('REFUSED: output {} is the input file or a hard link of some file (writing it would change the original in place); pick a fresh output path'.format(os.path.basename(dst)))
h = sys.argv[7] if len(sys.argv) > 7 else '10'; year = sys.argv[8] if len(sys.argv) > 8 else '2024'
if year not in ('2024', '2026'): sys.exit('REFUSED: wall ADD has fit tables for Revit 2024 and 2026 only (got %s)' % year)
import math
try: _v = [float(x) for x in (x0, y0, x1, y1, h)]
except ValueError: sys.exit('REFUSED: wall coordinates and height must be numbers')
if not all(math.isfinite(v) for v in _v) or any(abs(v) > 1e6 for v in _v): sys.exit('REFUSED: non-finite or absurd (> 1e6 ft) wall coordinate/height')
if math.hypot(_v[2] - _v[0], _v[3] - _v[1]) < 0.01: sys.exit('REFUSED: wall shorter than 0.01 ft (Revit minimum is ~0.0026 ft; zero length is a degenerate wall)')
if _v[4] <= 0 or _v[4] > 3000: sys.exit('REFUSED: wall height must be in (0, 3000] ft')
import cfb, re as _re
try:      # the writer's wall template is year specific: a wrong year writes a structurally wrong record (c4x-rvtdiff: a 2025 file got the 2024 template and was saved)
    _bfi = bytes(cfb.CFB(open(src, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')
    _fy = int(_re.search(r'(20[12]\d)', _bfi).group(1))
except Exception: sys.exit('REFUSED: cannot read the Revit version of the file (BasicFileInfo); add-wall needs the file year to pick the wall template')
if _fy != int(year): sys.exit('REFUSED: the file is a Revit %d file but year=%s was requested; the wall template is year specific, nothing written' % (_fy, year))
if _fy not in (2024, 2026): sys.exit('REFUSED: add-wall has a verified wall template only for 2024 and 2026 (file is %d); nothing written' % _fy)
if _fy == 2026 and os.environ.get('RVT_ADD26_SAVED') and not os.environ.get('RVT_ADD26_EXPERIMENT'):      # opt-in: Revit-SAVED 2026 base (single merged partition) + in-place member layout verified once (Electrical, VM 2026, readback exact); originals (4 partitions) stay refused
    _np = sum(1 for k in cfb.CFB(open(src, 'rb').read()).streams() if k.startswith('Partitions/'))
    _st = _re.findall(r'(20\d{6})_\d{4}\(x\d+\)', _bfi); _need = {2026: 20250519}[_fy]
    if not _st or int(_st[0]) < _need: sys.exit('REFUSED: file was not saved by the Revit build the VM verified (BasicFileInfo build stamp %s, need >= %d); originals and synthetic files corrupt on open; nothing written' % (_st[:1], _need))
    if _np != 1: sys.exit('REFUSED: 2026 add-wall is only allowed on a Revit-saved file (1 partition stream); this file has %d (original, Revit 2026 rejects our add on those); nothing written' % _np)
    os.environ['RVTGEN_INPLACE'] = '1'; os.environ['RVT_ADD26_EXPERIMENT'] = '1'
if _fy == 2026 and not os.environ.get('RVT_ADD26_EXPERIMENT'): sys.exit('REFUSED: 2026 add-wall output was refused by Revit 2026 on the original Snowdon Structural sample (CorruptModel / ModificationForbidden, sev1 open); disabled until a Revit-verified fix. Set RVT_ADD26_EXPERIMENT=1 for lab use only; nothing written')
if _fy == 2024 and os.environ.get('RVTGEN_INPLACE'):      # in-place layout opened only on a 2024 file saved by Revit (build stamp 20231029); all 3 originals (stamp 20230206) were CorruptModel
    _st = _re.findall(r'(20\d{6})_\d{4}\(x\d+\)', _bfi)
    if not _st or int(_st[0]) < 20231029: sys.exit('REFUSED: in-place add needs a 2024 file saved by Revit build >= 20231029 (BasicFileInfo stamp %s); originals were CorruptModel in the VM; nothing written' % (_st[:1],))
if not os.environ.get('RVT_ADD_WORKSHARED_FORCE'):      # workshared models carry worksets + central link the writer does not maintain (same rule as rvt_add_clone and the in-place save)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from rvtballet.save import worksharing_state
    _ws = worksharing_state(open(src, 'rb').read())
    if not (_ws or '').startswith('Not enabled'): sys.exit('REFUSED: Worksharing state is %r (not "Not enabled"): add-wall would create an element without worksets; nothing written' % (_ws,))
ix = G.file_geometry_index(src)
walls = sorted(e for e, v in ix.items() if str(v) == 'SWall')
if not walls: sys.exit('no existing wall to take type/level/phase from')
import re
ed = rvtedit.Edit(src); e = ed.g.e
def eid(v):
    m = re.match(r"EID\((\d+)\)", str(v)); return int(m.group(1)) if m else None
w = walls[0]; tr = e.trace(w)
f = {l[1]: l[4] for l in tr[3] if len(l) > 4}
typ = eid(f['VWall.m_WallAttributesId']); ph = eid(f['Element.m_createdPhaseId']); lv = eid(f['Element.m_assocLevelId'])
org = [l[4] for l in e.trace(lv)[3] if len(l) > 4 and l[1] == 'Plane.m_origin'][0]
lz = float(str(org).strip('[]').split(',')[2])
op = 'aw:%s:%s:%s:%s:%s:%d:%r:%d:%d:%d' % (x0, y0, x1, y1, h, lv, lz, typ, ph, w)
try:      # thickness: the like-wall has the SAME type, so twice its key-reference offset is that type's width; the fitted template is a 200 mm wall (Revit 2026 harness: badvolume=1 without this)
    _kro = float(str(f['VWall.m_keyRefOffset']).strip())
    if math.isfinite(_kro) and 0.01 < _kro < 50 and abs(_kro - 0.32808398950131235) > 1e-6: op += ':%r' % (2 * _kro)
except Exception: pass
print('OP', op, flush=True)
env = dict(os.environ, YEAR=year)
_epi = bool(os.environ.get('RVT_ADD_EPISODE'))      # EXPERIMENT (c4x-rvtdiff): give the add Revit's new-episode bookkeeping (tools/rvt_new_episode.py); VM verdicts pending, never default
_out = dst + '.noepisode.tmp' if _epi else dst
_rc = subprocess.call([sys.executable, os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py'), src, _out, op], env=env)
if _rc == 0 and _epi:
    try:
        _rc = subprocess.call([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvt_new_episode.py'), src, _out, dst])
    finally:
        if os.path.exists(_out): os.remove(_out)
    if _rc != 0 and os.path.exists(dst): os.remove(dst)      # never leave a half-processed output
if _rc == 0 and os.path.exists(dst) and not os.environ.get('RVTGEN_INPLACE'):      # post-write layout check (c4x-rvtdiff): on a base whose first partition member is full, a tiny first member in the output is the layout Revit 2024/2026 refuses (CorruptModelException)
    try:
        for _p in ('~/rvt-research/write-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(_p))
        import rvtw, wlpart
        def _first(path):
            c = cfb.CFB(open(path, 'rb').read()); n = sorted(k for k in c.streams() if k.startswith('Partitions/'))[0]
            m = wlpart.Partition(rvtw.Stream(c.streams()[n].data)).mem[0]['raw']; return len(m)
        _a, _b = _first(src), _first(dst)
        if _a > 100000 and _b < 1000:
            os.remove(dst); sys.exit('REFUSED: output layout check failed (first partition member %d B -> %d B; Revit refuses this layout on Revit-saved files); output deleted, set RVTGEN_INPLACE=1 to use the in-place layout' % (_a, _b))
    except SystemExit: raise
    except Exception as _e: print('layout check skipped: %s' % _e)
if _rc == 0 and os.path.exists(dst):      # member cap check (c3x-rvtdiff): Revit never writes a partition member > 131088 raw bytes; our 2026 add produced 238572 B
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import rvt_member_cap as _mc
        _big = _mc.oversized(_mc.member_sizes(dst))
        if _big and not _mc.oversized(_mc.member_sizes(src)):
            os.remove(dst); sys.exit('REFUSED: output has partition member(s) over the Revit cap %d B: %s; output deleted' % (_mc.CAP, _big[:3]))
    except SystemExit: raise
    except Exception as _e: print('member cap check skipped: %s' % _e)
sys.exit(_rc)
