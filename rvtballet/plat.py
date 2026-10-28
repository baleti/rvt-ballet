"""Cross-platform helpers (vendored rvtplat in _vendor/): browser launch, memory caps, paths. No Linux-only assumptions here."""
import os, sys
try: import rvtplat
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor")); import rvtplat
from rvtplat import browser, proc, paths, dirs, fsio, mem


def sheets_py():
    """interpreter for the sheets/vg3d helper processes: RVT_SHEETS_PY, the sheets venv when present, else this interpreter"""
    e = os.environ.get("RVT_SHEETS_PY")
    if e: return e
    sd = paths.sheets_dir(os.path.dirname(os.path.abspath(__file__)))
    if sd:
        for rel in (("Scripts", "python.exe"), ("bin", "python")):
            p = os.path.join(sd, ".venv", *rel)
            if os.path.isfile(p): return p
    return sys.executable


# sibling projects (Rust fast path, sheets renderer) importable wherever they are installed; no-op when already on sys.path
paths.add_to_path(paths.core_py_dir(os.path.dirname(os.path.abspath(__file__))), paths.sheets_dir(os.path.dirname(os.path.abspath(__file__))))

if not sys.platform.startswith("linux"):       # native cache location for the Rust fast path (rvt_fast.py hardcodes ~/.cache otherwise)
    os.environ.setdefault("RVT_CORE_CACHE", dirs.cache_dir("rvt-core"))
