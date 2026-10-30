"""rvt-ballet: convert .rvt (Revit 2020-2026) to glTF + JSON metadata and view it in a browser, without Revit."""

import os as _os
for _k in list(_os.environ):          # old RVT_VIEWER_* variables are still accepted
    if _k.startswith("RVT_VIEWER_") and "RVT_BALLET_" + _k[11:] not in _os.environ: _os.environ["RVT_BALLET_" + _k[11:]] = _os.environ[_k]

# staged install (packaging/stage_rvt.py): savegate + write-lab modules sit next to the package
_app = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _os.path.isdir(_os.path.join(_app, "writelab")):
    for _k, _v in (("RVTBALLET_WRITELAB", _os.path.join(_app, "writelab")), ("SAVEGATE_RVT_LIB", _os.path.join(_app, "writelab")), ("SAVEGATE_RVT_READER", _app)):
        _os.environ.setdefault(_k, _v)
