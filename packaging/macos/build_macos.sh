#!/bin/sh
# Build rvt-ballet.app (+ dmg when hdiutil exists) on macOS. UNTESTED on hardware (no Mac available); CI builds it.
# The app is an AppleScript droplet (osacompile) so Finder double click / drag-and-drop / "Open With" deliver the file
# (a shell launcher would not receive Apple Events). Not notarized (needs an Apple developer account): first start via right click > Open.
# usage: packaging/macos/build_macos.sh [OUT_DIR]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$HERE/../.."; OUT="${1:-$ROOT/dist}"
APP="$OUT/rvt-ballet.app"; rm -rf "$APP"; mkdir -p "$OUT"
python3 "$HERE/../stage_rvt.py" "$OUT"
osacompile -o "$APP" "$HERE/launcher.applescript"
R="$APP/Contents/Resources"
cp -R "$OUT/app" "$R/app"
python3 -m venv "$R/venv"
"$R/venv/bin/pip" install -q -r "$OUT/requirements.txt"
# merge document types + UTI into the applet's Info.plist (keeps the keys osacompile wrote)
python3 - "$APP/Contents/Info.plist" "$HERE/Info.plist" <<'P'
import plistlib, sys
dst, src = sys.argv[1], sys.argv[2]
d = plistlib.load(open(dst, 'rb')); s = plistlib.load(open(src, 'rb'))
for k in ('CFBundleName', 'CFBundleDisplayName', 'CFBundleIdentifier', 'CFBundleShortVersionString', 'CFBundleVersion', 'LSMinimumSystemVersion',
          'NSHighResolutionCapable', 'UTImportedTypeDeclarations', 'CFBundleDocumentTypes'):
    if k in s: d[k] = s[k]
d.pop('CFBundleTypeExtensions', None)
plistlib.dump(d, open(dst, 'wb'))
P
# editing Info.plist invalidated osacompile's ad-hoc signature; arm64 macOS refuses to launch an app with a broken signature ("damaged"). Ad-hoc sign again (no Apple account needed; still not notarized).
if command -v codesign >/dev/null; then codesign --force --deep -s - "$APP"; fi
# LIMITATION: venv/bin/python is a link to the python3 that built it, so the app runs only on Macs with that same python3 (use a python.org universal2 install). A relocatable embedded python is TODO.
if command -v hdiutil >/dev/null; then hdiutil create -quiet -volname rvt-ballet -srcfolder "$APP" -ov -format UDZO "$OUT/rvt-ballet.dmg"; fi
echo "built $APP"
