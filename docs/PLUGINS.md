# Viewer plug-in interface (for rvt-sheets and other modules)

The 3D viewer (`rvtviewer/server.py`) mounts plug-ins as aiohttp **sub-applications** next to its own API. A plug-in never edits viewer files.

## 1. Registering
A plug-in is a Python module exposing

```python
NAME = 'sheets'; TITLE = 'Sheets'; MOUNT = '/sheets/'       # optional
def make_app(ctx) -> aiohttp.web.Application: ...          # required
```
Loaded from (first match wins): env `RVT_PLUGINS=rvtsheets.server,...`; `~/.config/rvt-viewer/plugins.json`
`{"plugins": [{"module": "rvtsheets.server", "path": "~/src/rvt-sheets", "mount": "/sheets/", "title": "Sheets"}]}`; or, with neither present, `rvtsheets.server` from `~/src/rvt-sheets` when that directory exists.
A plug-in that fails to import is skipped with a message on the server console; the viewer keeps running. `GET /api/plugins` lists the mounted ones `[{name, title, mount}]`.

## 2. What `make_app(ctx)` receives (`rvtviewer.server.PluginContext`)
`ctx` is callable: `ctx(mid) -> absolute path of the source .rvt` (the `model_dir_resolver` of HOOKS.md). Attributes:
| call | returns |
|---|---|
| `ctx.model_ids()` | ids of the models currently loaded in the viewer |
| `ctx.source_path(mid)` | source .rvt path (None if unknown) |
| `ctx.model_dir(mid)` | cache directory (meta.json, model.sqlite, model.glb, summary.json) |
| `ctx.meta(mid)` | parsed meta.json: levels, grids, rooms, **views**, **sheets** (`{id, number, name, views[], issued, drawnBy}`), phases, `elements` rows `[id, class, category, name, type, level, fid, isType, family, phase]` |
| `ctx.sqlite(mid)` | sqlite3 connection (row_factory Row): `el(i,id,cls,cat,name,type,family,level,uid,ifc,fid,bb,iou,type_i)`, `prm(i,k,v)`, `ginfo(i,info json)` |
| `ctx.element_index(mid, element_id)` | viewer element index `i` of a Revit element id |
| `ctx.reader` | `rvtviewer.reader`: `reader._import()` puts `~/rvt-research` on sys.path (then `rvt_geometry`, `rvt_elemmesh`, `rvt_materials`, ... are importable), `reader.cached_load(path)` (decoded records), `reader.reader_stamp()` (cache version of the reader) |
Plug-ins read the .rvt through the reader themselves (their own cache); the viewer's converted data is only metadata and 3D batches.

## 3. HTTP API the plug-in page can use (same origin)
`/api/models`, `/m/<mid>/meta.json`, `/api/m/<mid>/el/<i>` (parameters, type parameters, geometry info), `/api/m/<mid>/search?q=`, `/api/m/<mid>/progress`, `/api/reader` (reader + viewer stamps).

## 4. Viewer -> plug-in links
* Toolbar: one button per plug-in (`TITLE`) opening `<MOUNT>#<mid>` in a new tab.
* Views tab: a `drawing` link on every sheet (`<MOUNT>#<mid>/sheet/<sheetId>`) and on every non-3D view (`<MOUNT>#<mid>/view/<viewId>`) when the plug-in is mounted at `/sheets/`.

## 5. Plug-in page -> viewer
The 3D viewer tab listens for `window.postMessage` (same origin; use `window.opener.postMessage(msg, location.origin)` from a page opened by the viewer, or `BroadcastChannel`-free: the viewer handles `message` events on its own window):
* `{type: 'rvt-select', elementId: <Revit id>}` selects the element and frames it.
* `{type: 'rvt-isolate', elementIds: [<Revit id>, ...]}` isolates and frames them.

## 6. Versioning / caching
Cache keys of the viewer include `reader.reader_stamp()`; a plug-in should key its own caches on the same stamp (changes mark everything stale at once).
