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
# relocatable CPython (python-build-standalone, permissive licence), so the .app runs on Macs without any Python; arch = the build machine
# (CI builds one .app per arch on macos-14 arm64 / macos-13 x86_64; a universal2 merge via lipo is possible later). Pin + checksum verified.
PBS_TAG="${PBS_TAG:-20261026}"; PBS_PY="${PBS_PY:-3.12.16}"
case "$(uname -m)" in arm64) PBS_ARCH=aarch64;; *) PBS_ARCH=x86_64;; esac
PBS_FILE="cpython-$PBS_PY+$PBS_TAG-$PBS_ARCH-apple-darwin-install_only.tar.gz"
PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/$PBS_TAG"
TMP="$(mktemp -d)"; curl -fsSL -o "$TMP/py.tgz" "$PBS_URL/$PBS_FILE"; curl -fsSL -o "$TMP/SHA256SUMS" "$PBS_URL/SHA256SUMS"
WANT="$(grep " $PBS_FILE\$" "$TMP/SHA256SUMS" | cut -d' ' -f1)"; GOT="$(shasum -a 256 "$TMP/py.tgz" | cut -d' ' -f1)"
[ -n "$WANT" ] && [ "$WANT" = "$GOT" ] || { echo "checksum mismatch for $PBS_FILE" >&2; exit 1; }
tar xzf "$TMP/py.tgz" -C "$TMP"; mv "$TMP/python" "$R/python"; rm -rf "$TMP"
"$R/python/bin/python3" -m pip install -q --no-warn-script-location -r "$OUT/requirements.txt"
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
if command -v hdiutil >/dev/null; then hdiutil create -quiet -volname rvt-ballet -srcfolder "$APP" -ov -format UDZO "$OUT/rvt-ballet.dmg"; fi
echo "built $APP"
