#!/bin/sh
# Per-user Linux integration (no root): .desktop entry, MIME type, "Open with", icon. Works from a checkout or an unpacked release.
# usage: packaging/linux/install.sh [--uninstall]      env: XDG_DATA_HOME (default ~/.local/share), APP_BIN (launcher to run, default <repo>/bin/rvt-ballet)
set -e
APP=rvt-ballet; EXT=rvt; MIME=application/x-revit-model; LABEL="rvt-ballet"
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$HERE/../.."
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"; BIN="${APP_BIN:-$ROOT/bin/$APP}"
DESK="$DATA/applications/$APP.desktop"; MIMEF="$DATA/mime/packages/$APP.xml"; ICON="$DATA/icons/hicolor/scalable/apps/$APP.svg"
refresh() { command -v update-mime-database >/dev/null && update-mime-database "$DATA/mime" >/dev/null 2>&1 || true
            command -v update-desktop-database >/dev/null && update-desktop-database "$DATA/applications" >/dev/null 2>&1 || true; }
if [ "$1" = "--uninstall" ]; then rm -f "$DESK" "$MIMEF" "$ICON"; refresh; echo "removed $APP integration"; exit 0; fi
mkdir -p "$DATA/applications" "$DATA/mime/packages" "$DATA/icons/hicolor/scalable/apps"
[ -x "$BIN" ] || { echo "launcher not found or not executable: $BIN" >&2; exit 1; }
cat > "$DESK" <<D
[Desktop Entry]
Type=Application
Name=$LABEL
Comment=Open $EXT files without the original CAD/BIM application
Exec="$BIN" %f
Icon=$APP
MimeType=$MIME;
Terminal=false
Categories=Graphics;Viewer;
D
cat > "$MIMEF" <<M
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="$MIME"><comment>$LABEL document</comment><glob pattern="*.$EXT"/><glob pattern="*.$(echo $EXT | tr a-z A-Z)"/></mime-type>
</mime-info>
M
[ -f "$ROOT/packaging/$APP.svg" ] && cp "$ROOT/packaging/$APP.svg" "$ICON" || true
refresh
echo "installed $APP integration under $DATA (Open With -> $LABEL for *.$EXT)"
