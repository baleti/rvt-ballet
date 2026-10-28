"""Per-user cache/config/data locations. Env override first, then the OS default.

  RVTPLAT_CACHE / RVTPLAT_CONFIG / RVTPLAT_DATA  override the base for every app
  RVTPLAT_<APP>_CACHE (app upper-cased, '-' -> '_') overrides a single app
Linux keeps the historical layout (~/.cache/<app>) so existing caches stay valid."""
import os, sys


def _home():
    return os.path.expanduser('~')


def _base(kind):
    env = os.environ.get('RVTPLAT_' + kind.upper())
    if env:
        return env
    if sys.platform == 'win32':
        local = os.environ.get('LOCALAPPDATA') or os.path.join(_home(), 'AppData', 'Local')
        roaming = os.environ.get('APPDATA') or os.path.join(_home(), 'AppData', 'Roaming')
        return {'cache': os.path.join(local, 'Cache'), 'config': roaming, 'data': local}[kind]
    if sys.platform == 'darwin':
        lib = os.path.join(_home(), 'Library')
        return {'cache': os.path.join(lib, 'Caches'), 'config': os.path.join(lib, 'Application Support'),
                'data': os.path.join(lib, 'Application Support')}[kind]
    xdg = {'cache': ('XDG_CACHE_HOME', '.cache'), 'config': ('XDG_CONFIG_HOME', '.config'),
           'data': ('XDG_DATA_HOME', os.path.join('.local', 'share'))}[kind]
    return os.environ.get(xdg[0]) or os.path.join(_home(), xdg[1])


def _dir(kind, app, make):
    env = os.environ.get('RVTPLAT_%s_%s' % (app.upper().replace('-', '_'), kind.upper()))
    p = env or os.path.join(_base(kind), app)
    if make:
        os.makedirs(p, exist_ok=True)
    return p


def cache_dir(app, make=False):
    return _dir('cache', app, make)


def config_dir(app, make=False):
    return _dir('config', app, make)


def data_dir(app, make=False):
    return _dir('data', app, make)


def temp_dir(app, make=True):
    import tempfile
    p = os.path.join(tempfile.gettempdir(), app)
    if make:
        os.makedirs(p, exist_ok=True)
    return p
