"""Locate the sibling projects (reader, rust fast path, sheets renderer) without hardcoding ~/src.

Order for each project: explicit env var, an installed/importable package, a sibling checkout next to the
calling repo, then the historical home layout (~/rvt-research, ~/src/rvt-core/python, ~/src/rvt-sheets)."""
import os, sys, importlib.util

_HOME = os.path.expanduser('~')


def _first_dir(cands, marker):
    for c in cands:
        if c and os.path.isfile(os.path.join(c, marker)):
            return os.path.abspath(c)
    return None


def _spec_dir(module):
    try:
        s = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        return None
    if s and s.origin and os.path.isfile(s.origin):
        return os.path.dirname(os.path.abspath(s.origin))
    return None


def _siblings(here, names):
    if not here:
        return []
    root = os.path.dirname(os.path.abspath(here))
    out = []
    for n in names:
        out += [os.path.join(root, n), os.path.join(os.path.dirname(root), n)]
    return out


def reader_dir(here=None):
    """directory holding rvt_geometry.py etc. (env RVT_READER_DIR)"""
    return os.environ.get('RVT_READER_DIR') or _first_dir(
        [_spec_dir('rvt_geometry')] + _siblings(here, ['rvt-research']) + [os.path.join(_HOME, 'rvt-research')],
        'rvt_geometry.py')


def core_py_dir(here=None):
    """directory holding rvt_fast.py (env RVT_CORE_PY); None when the fast path is not available"""
    return os.environ.get('RVT_CORE_PY') or _first_dir(
        [_spec_dir('rvt_fast')] + _siblings(here, ['rvt-core/python', 'rvt-core/pysrc']) + [os.path.join(_HOME, 'src', 'rvt-core', 'python')],
        'rvt_fast.py')


def sheets_dir(here=None):
    """directory that contains the rvtsheets package (env RVTSHEETS)"""
    e = os.environ.get('RVTSHEETS')
    if e:
        return os.path.expanduser(e)
    d = _spec_dir('rvtsheets')
    if d:
        return os.path.dirname(d)
    return _first_dir(_siblings(here, ['rvt-sheets']) + [os.path.join(_HOME, 'src', 'rvt-sheets')],
                      os.path.join('rvtsheets', '__init__.py'))


def python_exe(env='RVT_SHEETS_PY'):
    """interpreter for helper processes: env override, else the running one (never a hardcoded .venv/bin/python)"""
    return os.environ.get(env) or sys.executable


def add_to_path(*dirs):
    """prepend existing, not yet listed directories to sys.path; returns those added"""
    added = []
    for d in dirs:
        if d and os.path.isdir(d) and d not in sys.path:
            sys.path.insert(0, d)
            added.append(d)
    return added
