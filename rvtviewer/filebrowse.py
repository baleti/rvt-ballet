"""Server-side file browser for the library page (Open .rvt file...): only $HOME and mounted file systems are visible, only .rvt files are listed (directories to navigate)."""
import os

REAL_FS = {'ext2', 'ext3', 'ext4', 'btrfs', 'xfs', 'f2fs', 'vfat', 'exfat', 'ntfs', 'ntfs3', 'fuseblk', 'nfs', 'nfs4', 'cifs', 'smb3', 'zfs', 'overlay'}
EXT = ".rvt"


def roots():
    """allowed top directories: $HOME plus the mount points of real file systems (not '/', not system dirs)"""
    out = [os.path.realpath(os.path.expanduser('~'))]
    try:
        for ln in open('/proc/mounts'):
            f = ln.split()
            mp = f[1].replace('\\040', ' ')
            if not (f[2] in REAL_FS or f[2].startswith('fuse.')) or mp == '/' or mp.startswith(('/boot', '/var', '/usr', '/etc', '/proc', '/sys', '/dev', '/run/user', '/snap')): continue
            if any(x in ('.snapshots', 'swapvol') for x in mp.split('/')) or out[0].startswith(mp.rstrip('/') + '/'): continue   # snapshots, swap, a parent of $HOME
            if any(mp == r or mp.startswith(r.rstrip('/') + '/') for r in out): continue                                          # nested mounts are reachable by browsing
            out.append(mp)
    except OSError:
        pass
    return out


def allowed(p):
    p = os.path.realpath(p)
    return any(p == r or p.startswith(r.rstrip('/') + '/') for r in roots())


def browse(path):
    rs = roots()
    if not path: return {'path': '', 'parent': None, 'roots': rs, 'dirs': [], 'files': []}
    p = os.path.realpath(os.path.expanduser(path))
    if not allowed(p): return {'error': 'outside $HOME and the mounted directories', 'roots': rs}
    if not os.path.isdir(p): return {'error': 'not a directory', 'roots': rs}
    dirs, fl = [], []
    try:
        for e in sorted(os.scandir(p), key=lambda e: e.name.lower()):
            if e.name.startswith('.'): continue
            try:
                if e.is_dir(): dirs.append(e.name)
                elif e.is_file() and e.name.lower().endswith(EXT):
                    st = e.stat(); fl.append({'name': e.name, 'size': st.st_size, 'mtime': int(st.st_mtime)})
            except OSError: pass
    except OSError as ex:
        return {'error': ex.strerror or str(ex), 'roots': rs}
    parent = os.path.dirname(p) if p not in rs and allowed(os.path.dirname(p)) else None
    return {'path': p, 'parent': parent, 'roots': rs, 'dirs': dirs, 'files': fl}


def check(path):
    """(real path, None) for an openable file, else (None, message)"""
    if path.startswith('file://'):
        import urllib.parse; path = urllib.parse.unquote(path[7:])
    if not path: return None, 'no path given'
    p = os.path.realpath(os.path.expanduser(path))
    if not allowed(p): return None, 'outside $HOME and the mounted directories'
    if not p.lower().endswith(EXT): return None, 'not a .rvt file'
    if not os.path.isfile(p): return None, 'no such file'
    return p, None
