#!/usr/bin/env python3
"""rvt_vm_open.py YEAR FILE... : open already-saved outputs in the offline Revit VM (audit on) one by one (guest.vmlock serialises with other agents, ~7 min each); TSV row per file, appended to ~/c3x-rvtmatrix-work/vm_rows.tsv.
Row: agent, short id, year, class tag, revit_open, cmp, dialogs, failures (no paths)."""
import os, sys, hashlib
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign')); os.environ['STAGEB'] = '1'
import stages
year = int(sys.argv[1])
if year < 2020: sys.exit('refused: no Revit oracle for %d (revit-ballet add-in supports 2020-2026; 2017-2019 dropped, would only burn a lane)' % year)
out = os.path.expanduser('~/c3x-rvtmatrix-work/vm_rows.tsv')
def _sid(f): return hashlib.sha256(open(f, 'rb').read()).hexdigest()[:6]
if os.environ.get('RVT_WARM') == '1' and len(sys.argv) > 3:      # portfix: one lane lock + warm Revit for the whole batch
    files = sys.argv[2:]
    for f, r in stages.api_stage_batch(year, [(f, 'rm' + _sid(f)) for f in files]):
        sid = _sid(f); tag = os.path.basename(f)[:-4].split('_')[-1]
        row = '\t'.join(['c3x-rvtmatrix', sid, str(year), tag, 'revit_open=%s' % r['ok'], 'cmp=%s' % (r.get('cmp'),), 'dialogs=%s' % r.get('dialogs'), 'failures=%s' % r.get('failures'), (r.get('err') or '')[:100], 'lane=%s' % r.get('lane'), 'build=%s' % r.get('build'), 'sha256=%s' % r.get('sha256'), 'sec=%s' % r.get('sec'), 'ts=%d' % __import__('time').time(), 'warm=1'])
        print(row, flush=True); open(out, 'a').write(row + '\n')
    sys.exit(0)
for f in sys.argv[2:]:
    tag = os.path.basename(f)[:-4].split('_')[-1]; sid = hashlib.sha256(open(f, 'rb').read()).hexdigest()[:6]
    r = stages.api_stage(year, f, True, 'rm' + sid)
    row = '\t'.join(['c3x-rvtmatrix', sid, str(year), tag, 'revit_open=%s' % r['ok'], 'cmp=%s' % (r.get('cmp'),), 'dialogs=%s' % r.get('dialogs'), 'failures=%s' % r.get('failures'), (r.get('err') or '')[:100], 'lane=%s' % r.get('lane'), 'build=%s' % r.get('build'), 'sha256=%s' % r.get('sha256'), 'sec=%s' % r.get('sec'), 'ts=%d' % __import__('time').time()])
    print(row, flush=True); open(out, 'a').write(row + '\n')
