"""a declared edit that did not change its element is REFUSED (422 verify_failed, kind 'not_applied', nothing written): found on a real project where the second move of a multi-pass save was silently dropped and the save still
returned 200. Here the declaration and the bytes disagree on purpose (manifest names el:301595 but the output is the unchanged source); a real edit of the same element still passes."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
sg = save._import()
if not os.path.exists(RTE) or not sg: print('skip'); sys.exit(0)
src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); ss = save.SaveSessions(); d = ss.doc('m', src)
dest = os.path.join(_T, 'o.rvt')
try: save.save_as(ss, 'm', src, dest, new_bytes=bytes(d.buf) + b'', manifest={'modified': ['el:301595']}); raise SystemExit('FAIL: a declared edit with no effect was accepted')
except sg.VerifyFailed as e: assert ('not_applied', 'el:301595') in e.report['unexpected'], e.report; assert not os.path.exists(dest)
ss.edits('m').ops.clear(); save.add_edit(ss, 'm', src, {'op': 'move', 'eid': 301595, 'dx': 2.0})
r = save.save_as(ss, 'm', src, os.path.join(_T, 'ok.rvt')); assert r['ok'] and r['verify']['n_unexpected'] == 0
print('save not_applied OK: declared-but-unchanged element refused (nothing written); a real move of it still saves')
