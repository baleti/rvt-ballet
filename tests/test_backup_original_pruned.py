"""Queue item 18 (answer: NOT a problem): pruning with backup_keep=3 over 6 versions keeps the ORIGINAL (oldest, pinned) and the newest backups, never more than 3. Synthetic bytes only."""
import os, sys, tempfile, hashlib
sys.path.insert(0, os.path.expanduser('~/src/savegate'))
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_BACKUP_DIR'] = T + '/bk'
from savegate import backup
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
p = T + '/f.rvt'; shas = []
for i in range(6):
    open(p, 'wb').write(b'version-%d' % i * 1000); shas.append(sha(p)); b = backup.make_backup(p, 3, 0)
    assert sha(b) == shas[-1]
have = {sha(x[1]) for x in backup.list_backups(p)}
print('kept', None if have is None else len(have), 'original kept:', None if have is None else shas[0] in have, 'newest kept:', None if have is None else shas[-1] in have)
assert shas[-1] in have and shas[0] in have and len(have) <= 3, 'original or newest pruned'
print('OK')
