"""SVG -> PNG / PDF through a headless Chromium-family browser (Edge ships with Windows, Chrome on macOS):
replacement for rsvg-convert where it is not installed. Vector PDF, so sheets stay crisp."""
import os, re, sys, shutil, subprocess, tempfile
from . import browser, dirs


def _file_url(p):
    from urllib.request import pathname2url
    return 'file:' + pathname2url(os.path.abspath(p))


def _svg_size(svg):
    """(width, height) in CSS px from width/height or viewBox; mm/in/pt units converted"""
    head = open(svg, 'r', encoding='utf-8', errors='replace').read(4000)
    k = {'': 1.0, 'px': 1.0, 'mm': 96 / 25.4, 'cm': 96 / 2.54, 'in': 96.0, 'pt': 96 / 72.0}

    def dim(name):
        m = re.search(r'\b%s="([\d.]+)([a-z%%]*)"' % name, head)
        return float(m.group(1)) * k.get(m.group(2), 1.0) if m and m.group(2) != '%' else None
    w, h = dim('width'), dim('height')
    if not (w and h):
        m = re.search(r'viewBox="[\d.\-]+[ ,]+[\d.\-]+[ ,]+([\d.]+)[ ,]+([\d.]+)"', head)
        if m:
            w, h = float(m.group(1)), float(m.group(2))
    return (w or 1200.0, h or 800.0)


def _run(args, timeout):
    b = browser.find()
    if not b:
        raise RuntimeError('no Chromium-family browser found (set RVT_BROWSER)')
    prof = os.environ.get('RVTPLAT_RENDER_PROFILE') or dirs.cache_dir('rvtplat-render', make=True)     # persistent: first-run profile setup is slow (~40 s on a cold VM)
    try:
        cmd = [b, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
               '--hide-scrollbars', '--user-data-dir=' + prof] + args
        if sys.platform.startswith('linux') and hasattr(os, 'geteuid') and os.geteuid() == 0:
            cmd.append('--no-sandbox')
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    finally:
        pass


def svg_to_png(svg, out, width=None, timeout=120):
    """render `svg` to PNG `out` (white background); width in px (height follows the aspect ratio)"""
    w, h = _svg_size(svg)
    if width:
        h, w = h * width / w, float(width)
    html = tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8')
    try:
        html.write('<!doctype html><meta charset=utf-8><style>html,body{margin:0;background:#fff}img{display:block;width:%dpx;height:%dpx}</style><img src="%s">'
                   % (round(w), round(h), _file_url(svg)))
        html.close()
        tmp = out + '.tmp.png'
        _run(['--screenshot=' + os.path.abspath(tmp), '--window-size=%d,%d' % (round(w), round(h)), _file_url(html.name)], timeout)
        if not os.path.exists(tmp):
            raise RuntimeError('browser produced no screenshot')
        os.replace(tmp, out)
        return out
    finally:
        os.remove(html.name)


def svg_to_pdf(svg, out, timeout=180):
    """vector PDF of one SVG; page size = the SVG's own size"""
    w, h = _svg_size(svg)
    html = tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8')
    try:
        html.write('<!doctype html><meta charset=utf-8><style>@page{size:%.0fpx %.0fpx;margin:0}html,body{margin:0}img{display:block;width:%.0fpx;height:%.0fpx}</style><img src="%s">'
                   % (w, h, w, h, _file_url(svg)))
        html.close()
        tmp = out + '.tmp.pdf'
        _run(['--no-pdf-header-footer', '--print-to-pdf=' + os.path.abspath(tmp), _file_url(html.name)], timeout)
        if not os.path.exists(tmp):
            raise RuntimeError('browser produced no pdf')
        os.replace(tmp, out)
        return out
    finally:
        os.remove(html.name)
