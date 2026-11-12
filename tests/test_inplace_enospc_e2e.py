"""in-place edit with injected ENOSPC (backup write / final rename) on the Autodesk 2024 HVAC sample, private copy, temp gate: target stays the original, no temp left. Slow (~2 min each). python tests/test_inplace_enospc_e2e.py backup|commit"""
import os, sys
if not os.path.exists(os.path.expanduser("~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt")): print("sample absent: skipped"); sys.exit(0)
import os, sys, errno, shutil, hashlib, glob
which = sys.argv[1]
D = os.path.expanduser('~/c3x-tmp/enospc_' + which); shutil.rmtree(D, ignore_errors=True); os.makedirs(D)
os.environ.update(SAVEGATE_JOURNAL=D + '/j', SAVEGATE_CACHE=D + '/c', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=D + '/gate.json')
open(D + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}')
S = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt'); P = D + '/ip.rvt'; shutil.copy(S, P)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]; o = sha(S)
sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet')); sys.path.insert(0, os.path.expanduser('~/src/savegate'))
from unittest import mock
from savegate import atomic as A, backup as B
err = OSError(errno.ENOSPC, 'No space left on device')
patch = {'backup': mock.patch.object(B, 'full_fsync', side_effect=err), 'commit': mock.patch.object(A, 'commit_temp', side_effect=err)}[which]
from rvtballet.cli import main
with patch:
    try: main(['edit', P, '--in-place', '--set-string', '1365188', 'Mark', 'c8x-enospc-' + which])
    except SystemExit as e: rc = e.code
    else: rc = 0
left = [f for f in glob.glob(D + '/**', recursive=True) if f.endswith(('.tmp', '.part', '.new')) or '.sg-tmp' in f]
bk = [f for f in glob.glob(D + '/.savegate/*')]
print('RESULT', which, 'rc', rc, 'target', 'ORIGINAL' if sha(P) == o else 'CHANGED', 'size', os.path.getsize(P), 'tmp_left', len(left), left[:2], 'backups', [(os.path.basename(b)[-12:], sha(b) == o) for b in bk])
