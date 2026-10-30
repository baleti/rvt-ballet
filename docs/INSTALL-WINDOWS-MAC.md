# Install on Windows and macOS

## Windows (10/11, per user, no admin)
1. Run `rvt-ballet-setup-0.1.0.exe`. It installs to `%LOCALAPPDATA%\Programs\rvt-ballet`, adds a Start menu entry and an "Open with" entry for .rvt files (it does not take over the default handler).
2. Start it from the Start menu, or right click a .rvt file > Open with > rvt-ballet. A browser window (Edge, Chrome, Brave or Chromium, whichever is installed; Edge ships with Windows) opens in app mode.
3. Uninstall from Settings > Apps; the program folder, shortcut and registry entries are removed.

Caches live under `%LOCALAPPDATA%` (override with `RVTPLAT_CACHE`, or `RVTPLAT_<APP>_CACHE`). `RVT_BROWSER` selects another Chromium-family browser.

Build the installer yourself: install Python 3.12 and Inno Setup 6 (`winget install JRSoftware.InnoSetup`), then run `packaging\build_windows.ps1` (dwg-ballet) or `packaging\build_windows_rvt.ps1` (rvt-ballet). Native speed-ups are optional: put the abi3 wheels (`dwgfast`, `dwgscene_fast`, `rvt_core`) into `dist\wheels` before building; without them the pure-Python code is used.

Verified on a fresh Windows VM (Python 3.12.10): build, silent install, start page / library answers HTTP 200, uninstall leaves nothing behind, test suites pass. Not verified: opening real drawings or models on Windows (no clean test files were available).

## macOS (11 or newer) - UNTESTED, no Mac hardware was available
`sh packaging/macos/build_macos.sh` builds `rvt-ballet.app` (an AppleScript droplet so Finder double click, drag and drop and "Open with" deliver the file) and a dmg. It is not notarized (that needs an Apple developer account): on first start use right click > Open. CI builds it on `macos-latest`; check the workflow log before trusting it.

## Saving (SAVE AS / SAVE / edits): status and limits
- NOT part of the installers: it needs the private `savegate` library and the write-lab / edit-lab checkouts (`~/src/savegate`, `~/rvt-research/write-lab`, `edit-lab`). Without them the viewer runs unchanged and every save endpoint answers 501 `unavailable`. Overwrite (`SAVE`) is OFF unless `RVTBALLET_ALLOW_OVERWRITE=1` AND an oracle gate is open; editing parameters by name needs `RVTBALLET_EDIT_BACKEND=rvtedit`. Details: `docs/SAVE.md`.
- Only Revit 2024 and 2026 files can be saved (other years are refused). Tested on Linux only; Windows and macOS are UNTESTED for saving (path handling, file locks and the worker below are the open points).
- Memory: the verify dumps every element and can need many GB on real projects (a 64 MB project passed 14 GB; 4 of 5 small real 2024 projects were saved identically, taking 12 s to 17 min). The dump runs in a worker process with a memory cap (`RVTBALLET_SNAPSHOT_MEM_GB`); a model that does not fit is refused with `too_big` and nothing is written. The cap uses POSIX `RLIMIT_AS`: on Windows the worker runs WITHOUT a cap (set the budget yourself or expect the machine to swap), on macOS RLIMIT_AS is not reliably enforced.
- Time: a save of a real project takes minutes; the browser UI polls `/api/m/<id>/saveprogress`. HTTP clients and proxies with a 5-minute timeout will give up before it finishes.

## Limits
- The memory cap used on Linux (systemd) is a Job Object on Windows; macOS has only `nice` (no hard cap).
- Layout/mesh worker pools use `spawn` or run sequentially where `fork` does not exist, so large files convert slower on Windows than on Linux.
- Code signing: the installers are unsigned until the SignPath Foundation application is approved (SmartScreen will warn).
