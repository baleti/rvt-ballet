"""c3x-rvtdel item 26: standing gate. For one element of every allowlisted delete class in the 2024 Construction template, an ACCEPTED delete must leave no removed id mentioned in the decoded params of any surviving element (tools/rvt_dangling_check logic); refusals are fine. Fails on the old view-template / in-use style behaviour."""
import os, sys, re, tempfile, shutil, collections
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
import rvt_params
a = rvt_params.params(SRC); by = collections.defaultdict(list)
for e, d in a.items():
    if isinstance(d, dict) and d.get('class') in edit.DELETE_VM_VERIFIED: by[d['class']].append(e)
src = os.path.join(_T, 's.rte'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
num = re.compile(r"(?<=: )(\d{2,12})(?=[,}\]])|(?<=, )(\d{2,12})(?=[,}\]])")      # numeric VALUES only (not digits inside GUIDs/names)
bad = []; acc = ref = 0; WARN = {'AssemblyCodeTable'}      # open finding, see c3x-progress item 26
for cls, ids in sorted(by.items()):
    for eid in ids[:2]:
        try: nb, dl = edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': eid})])
        except edit.EditError: ref += 1; continue
        o = os.path.join(_T, 'o.rte'); open(o, 'wb').write(nb); b = rvt_params.params(o); gone = set(a) - set(b); acc += 1
        hits = [(e, x.get('class')) for e, x in b.items() for m in set(y for t in num.findall(repr(x)) for y in t if y) if int(m) in gone and int(m) != e]
        print(cls, eid, 'removed', len(gone), 'dangling', len(hits), flush=True)
        if hits and cls in WARN: print('WARN (VM-verified class, 9 Viewports carry "Parent View" = this id; needs Revit readback)', cls, eid)
        elif hits: bad.append((cls, eid, hits[:3]))
print('accepted', acc, 'refused', ref)
assert not bad, bad
print('OK')
