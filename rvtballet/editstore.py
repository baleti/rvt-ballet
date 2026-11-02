"""Pending edit ops survive a viewer restart: after every change of the edit list a small JSON file (one per source file, in the per-user data dir) holds the ops
together with the fingerprint of the file they were recorded against. After a restart the page offers them back; they are replayed through the normal trial
replay (a ruined op is refused) and only when the file is still byte-identical to the one they were recorded against. Nothing here writes to the model file."""
import os, json, hashlib, tempfile, time
from . import plat

DIR = os.environ.get('RVTBALLET_EDITSTORE') or os.path.join(plat.dirs.data_dir('rvt-ballet'), 'pending-edits')


def _file(src): return os.path.join(DIR, hashlib.sha1(os.fsencode(os.path.realpath(src))).hexdigest() + '.json')


def sweep(max_age=30 * 86400, gone_age=7 * 86400):
    """drop stores older than 30 days, and stores whose source file no longer exists once they are 7 days old (a recent one may belong to a drive that is just not mounted)"""
    n = 0
    try:
        now = time.time()
        for x in os.listdir(DIR):
            p = os.path.join(DIR, x)
            if x.endswith('.tmp') or x.endswith('.json'):
                try:
                    age = now - os.stat(p).st_mtime
                    if x.endswith('.tmp'): dead = age > 3600
                    else:
                        src = json.load(open(p, encoding='utf-8')).get('src')
                        dead = age > max_age or (age > gone_age and not (isinstance(src, str) and os.path.exists(src)))
                    if dead: os.remove(p); n += 1
                except (OSError, ValueError): pass
    except OSError: pass
    return n


def sync(src, ops, sha256):
    """write (or remove, when no ops are pending) the store for this source file. Never raises: losing the safety net must not break an edit"""
    try:
        p = _file(src)
        if not ops:
            try: os.remove(p)
            except FileNotFoundError: pass
            return
        os.makedirs(DIR, exist_ok=True); sweep()
        fd, tmp = tempfile.mkstemp(dir=DIR, suffix='.tmp')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump({'src': os.path.realpath(src), 'sha256': sha256, 'saved': int(time.time()), 'ops': list(ops)}, f); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, p)
    except Exception: pass


def load(src, sha256):
    """(ops, why): the stored ops when they were recorded against exactly this file content; ([], reason) otherwise. A mismatching store is left in place (it is the user's work)"""
    try: d = json.load(open(_file(src), encoding='utf-8'))
    except FileNotFoundError: return [], None
    except Exception as e: return [], 'unreadable edit store (%s)' % e
    if d.get('sha256') != sha256: return [], 'the file changed since these edits were recorded (they were made against another version)'
    ops = d.get('ops')
    return (ops, None) if isinstance(ops, list) else ([], 'damaged edit store')
