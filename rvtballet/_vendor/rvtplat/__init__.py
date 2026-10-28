"""rvtplat: tiny cross-platform layer shared by the rvt/dwg tools (Windows, macOS, Linux).
No third-party imports at module level; psutil is used when present, never required."""
from . import dirs, fsio, mem, browser, proc, paths, fonts, render

__all__ = ['dirs', 'fsio', 'mem', 'browser', 'proc', 'paths', 'fonts', 'render']
