"""DEPRECATED compatibility shim, kept for one release (remove after 2026-12): the old streamed single-process scan that lived here was replaced by
fastquery.scan on 2026-11-14 (same result shape; the corrected sheet rule: 412 of 412 sheets equal Revit on a 984 MB project file where the old scan listed 393;
2-4 s instead of 17 s). The file helpers moved to rvtfile.py. Import those modules directly in new code."""
from .rvtfile import (_tune, _rss_mb, _trim, _paths, basic_info, project_information, saves, editors, _KEEP, _KEEP_VIEW, _reduce, _plausible, _sc,  # noqa: F401
                      file_info, elements_from_index)

PAGE_STORED = 65249; PAGE_PAYLOAD = 64896


def scan(path, log=None, want_elements=False, progress=None, **_):
    """== fastquery.scan(path, log, want_elements): levels, grids, views, sheets, revisions, phases, counts, class_counts, view_owned, stats, arrays"""
    from . import fastquery
    return fastquery.scan(path, log=log, want_elements=want_elements)
