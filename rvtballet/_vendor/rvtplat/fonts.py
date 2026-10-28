"""Find a font file by family name on Linux (fontconfig), Windows and macOS, without third-party packages.

find(name, bold) -> (path, family) or None. fontconfig's answer is used when `fc-match` exists, but only the
family it really matched is reported, so callers can detect a silent fallback (as viewdraw._font does)."""
import os, sys, shutil, subprocess

# family -> (regular file, bold file) candidates; case-insensitive match on the basename
_FILES = {
    'arial': ('arial.ttf', 'arialbd.ttf'), 'arial narrow': ('arialn.ttf', 'arialnb.ttf'),
    'arial black': ('ariblk.ttf', 'ariblk.ttf'), 'times new roman': ('times.ttf', 'timesbd.ttf'),
    'courier new': ('cour.ttf', 'courbd.ttf'), 'verdana': ('verdana.ttf', 'verdanab.ttf'),
    'trebuchet ms': ('trebuc.ttf', 'trebucbd.ttf'), 'georgia': ('georgia.ttf', 'georgiab.ttf'),
    'tahoma': ('tahoma.ttf', 'tahomabd.ttf'), 'calibri': ('calibri.ttf', 'calibrib.ttf'),
    'segoe ui': ('segoeui.ttf', 'segoeuib.ttf'), 'helvetica': ('Helvetica.ttc', 'Helvetica.ttc'),
}
# when the family is missing, metric-compatible or common stand-ins in order
_FALLBACK = {'arial': ['liberation sans', 'dejavu sans', 'helvetica'], 'arial narrow': ['arial', 'liberation sans narrow'],
             'times new roman': ['liberation serif', 'dejavu serif'], 'courier new': ['liberation mono', 'dejavu sans mono']}
_LIBERATION = {'liberation sans': ('LiberationSans-Regular.ttf', 'LiberationSans-Bold.ttf'),
               'liberation serif': ('LiberationSerif-Regular.ttf', 'LiberationSerif-Bold.ttf'),
               'liberation mono': ('LiberationMono-Regular.ttf', 'LiberationMono-Bold.ttf'),
               'dejavu sans': ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'),
               'dejavu serif': ('DejaVuSerif.ttf', 'DejaVuSerif-Bold.ttf'),
               'dejavu sans mono': ('DejaVuSansMono.ttf', 'DejaVuSansMono-Bold.ttf')}


def font_dirs():
    d = []
    if sys.platform == 'win32':
        d += [os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts'),
              os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts')]
    elif sys.platform == 'darwin':
        d += ['/System/Library/Fonts', '/System/Library/Fonts/Supplemental', '/Library/Fonts',
              os.path.expanduser('~/Library/Fonts')]
    else:
        d += ['/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.local/share/fonts'),
              os.path.expanduser('~/.fonts')]
    extra = os.environ.get('RVT_FONT_DIRS')
    if extra:
        d = extra.split(os.pathsep) + d
    return [x for x in d if x and os.path.isdir(x)]


_INDEX = {}


def _index():
    if not _INDEX:
        for root in font_dirs():
            for dp, _, fs in os.walk(root):
                for f in fs:
                    if f.lower().endswith(('.ttf', '.otf', '.ttc')):
                        _INDEX.setdefault(f.lower(), os.path.join(dp, f))
    return _INDEX


def _fc(name, bold):
    if not shutil.which('fc-match'):
        return None
    try:
        out = subprocess.run(['fc-match', '-f', '%{file}|%{family}', '%s:%s' % (name, 'bold' if bold else 'regular')],
                             capture_output=True, text=True, timeout=5).stdout
        path, fam = out.split('|', 1)
        return (path, fam) if path and os.path.isfile(path) else None
    except Exception:
        return None


def _by_name(fam, bold):
    idx = _index()
    pair = _FILES.get(fam) or _LIBERATION.get(fam)
    if pair:
        p = idx.get(pair[1 if bold else 0].lower())
        if p:
            return p
    return None


def find(name, bold=False):
    """(path, matched family) for `name`, or None when nothing usable exists. `matched family` equals `name`
    for a real match and the stand-in's family otherwise."""
    r = _fc(name, bold)
    if r:
        return r
    key = name.lower()
    p = _by_name(key, bold)
    if p:
        return p, name
    for alt in _FALLBACK.get(key, ['dejavu sans', 'liberation sans']):
        p = _by_name(alt, bold) or (_by_name(_FALLBACK.get(alt, [''])[0], bold) if alt in _FALLBACK else None)
        if p:
            return p, alt
    return None
