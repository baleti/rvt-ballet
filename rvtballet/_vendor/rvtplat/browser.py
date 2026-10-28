"""Find a Chromium-family browser and open an app window (--app mode) on Windows, macOS and Linux."""
import os, sys, shutil, subprocess, webbrowser

_WIN_REL = [r'Microsoft\Edge\Application\msedge.exe', r'Google\Chrome\Application\chrome.exe',
            r'BraveSoftware\Brave-Browser\Application\brave.exe', r'Chromium\Application\chrome.exe']
_MAC = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
        '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
        '/Applications/Chromium.app/Contents/MacOS/Chromium']
_LINUX = ['chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable', 'microsoft-edge',
          'microsoft-edge-stable', 'brave-browser', 'brave']


def _win_registry(exe):
    try:
        import winreg
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\%s' % exe) as k:
                    p = winreg.QueryValue(k, None)
                    if p and os.path.isfile(p):
                        return p
            except OSError:
                pass
    except ImportError:
        pass
    return None


def find():
    """path of a Chromium-family browser, or None. Env RVT_BROWSER (path or command name) wins."""
    e = os.environ.get('RVT_BROWSER')
    if e:
        return e if os.path.isfile(e) else shutil.which(e)
    if sys.platform == 'win32':
        for n in ('msedge.exe', 'chrome.exe', 'brave.exe'):       # Edge ships with Windows 10/11
            p = _win_registry(n)
            if p:
                return p
        for env in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA'):
            base = os.environ.get(env)
            for rel in _WIN_REL:
                if base and os.path.isfile(os.path.join(base, rel)):
                    return os.path.join(base, rel)
        return None
    if sys.platform == 'darwin':
        for p in _MAC + [os.path.expanduser('~' + x) for x in _MAC]:
            if os.path.isfile(p):
                return p
        return None
    for n in _LINUX:
        p = shutil.which(n)
        if p:
            return p
    return None


def app_command(url, profile_dir=None, size=(1500, 950), extra=()):
    """argv for an app-mode window, or None when no browser is installed"""
    b = find()
    if not b:
        return None
    cmd = [b, '--app=' + url, '--no-first-run', '--no-default-browser-check', '--window-size=%d,%d' % size]
    if profile_dir:
        cmd.append('--user-data-dir=' + profile_dir)
    return cmd + list(extra)


def open_app(url, profile_dir=None, size=(1500, 950), extra=(), env=None):
    """open url as an app window; falls back to the default browser. Returns the Popen or None."""
    cmd = app_command(url, profile_dir, size, extra)
    if not cmd:
        webbrowser.open(url)
        return None
    kw = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL, 'env': env}
    if sys.platform == 'win32':
        kw['creationflags'] = 0x00000008 | 0x00000200      # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw['start_new_session'] = True
    return subprocess.Popen(cmd, **kw)
