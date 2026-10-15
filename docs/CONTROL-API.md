# View control API (c2-vctl <-> c2-annot / rvt-sheets)

Goal: view-dependent elements (tags, text notes, dimensions, spot elevations, grids, levels, section marks, keynotes, hatches) are drawn by
rvt-sheets, delivered to the viewer as JSON primitives with stable element ids and category data, and placed in model space by the viewer
(`web/viewctl.js`) where every layer / category / subcategory / element can be toggled, recoloured, re-weighted, resized and picked.

## What exists today (viewer side, in this repo)
* `rvtviewer/vscene_worker.py`: one process per .rvt (rvt-sheets venv). Calls `ViewDrawer.draw(view_id)` and returns `{view, prims, elements, options, stats}`.
  Re-render options: `scale` (annotation scale 1:N, exact: sizes and pen widths are regenerated), `detail` (1/2/3), `template` (false = ignore the view template),
  `filters` (false = ignore view filters). Nothing in rvt-sheets is modified.
* `rvtviewer/viewctl.py`: HTTP: `GET /api/m/{mid}/vc/views`, `GET /api/m/{mid}/vc/scene/{vid}?scale=&detail=&template=0&filters=0`, `GET /api/m/{mid}/vc/element/{eid}`,
  `GET|PUT /api/vc/presets`. Results cached in `~/.cache/rvt-viewer/vscene/`.
* Scene = `view` (frame: origin/right/up/dir in world feet, scale, range, crop_uv), `prims` (rvt-sheets primitives in view coordinates, model feet, annotation sizes already
  multiplied by the view scale), `elements` ({eid: {cls, cat, catName, parent, parentName}}).

## What the viewer relies on in each primitive (please keep stable)
`t` (line | segs | cut | fill | text), `elem` (Revit element id of the owner), `layer` (cut, projection, underlay, symbolic, symbolic_fill, cut_fill, surface_fill, room_fill, mask,
annotation, annotation_fill, text, datum), `style` {w (paper mm), rgb, dash (paper mm), halftone}, text: `text origin x size font bold italic halign valign anchor box`.

## Requests to c2-annot (rvt-sheets) - answer under each item in CONTROL-API-ANSWERS.md (or edit here)
1. **Stable ids.** Every primitive carries `elem` (already) plus `part` for sub-parts of one element (tag text vs leader vs head vs frame; dimension line vs witness vs text;
   grid line vs bubble vs label) so the viewer can hide e.g. tag leaders only. Value: short string (`leader`, `text`, `head`, `witness`, `line`, `bubble`, `frame`, `arrow`).
2. **Category on every primitive**: `cat` (category id, subcategory id when the element uses a subcategory) on all prims, not only `cut`; `elements[eid]` should include `catName`, `parent`
   (category id of the parent), `parentName`. Today the viewer derives them from `vis.info.info[eid]` (works for model elements; annotation elements with `cat` -1 show up as "no category").
3. **Element properties for picking**: `GET /sheets/api/{mid}/view/{id}.json` or an `elements` table with at least `name`, `typeName`, `familyName`, `levelName`, `hostId` (tagged element),
   `text` (resolved text of tags / notes / dimension value), `params` {name: value} (type + instance, as Revit shows them in the Properties palette). Until then the viewer shows
   the raw stored fields of the record (`/vc/element/{eid}`).
4. **Anchor in model space**: for tags / text notes / dimensions / spots, `anchor` = model-space (world feet) point they annotate (tagged element's reference point), so the viewer can
   orient and place annotations in 3D relative to the model without relying on the 2D view frame, and so annotation scaling pivots on the right point.
5. **Scale-dependence flags** per primitive: `paper: true` for sizes that are paper sizes (text height, arrowheads, bubble radius, pen widths: grow with 1:N) vs `paper: false` for
   model-size geometry (walls, dimension extension geometry). The viewer scales text about its anchor when the user picks another annotation scale; with this flag the same can be
   done for symbols without a server round trip.
6. **Served directly by the sheets server**, same shape as the worker's scene: `GET /sheets/api/{mid}/view/{id}.json?scale=&detail=&template=0&filters=0` (and cached with the
   same key as the SVG, so the demo never decodes on host3). When that exists the viewer drops its own worker (`viewctl.py` proxies to it).
7. **Per-prim `gs`** (graphic style id) and for filled regions a `pattern` id + `pattern_color`, so line weight / pattern overrides can be applied per graphic style.
8. Everything above must be optional: absent keys mean "unknown", never an error.

## What the viewer provides (done = in this branch)
* [x] overlay in model space, plan and section/elevation frames, text sized in model feet (scales with zoom)
* [x] per layer / category / subcategory / class (type) / element visibility; colour override; line weight multiplier; text size x, font, colour; crop on/off; on-top / lift / opacity
* [x] annotation scale (re-render), detail level, view template on/off, filters on/off
* [x] picking (hover tooltip, click: highlight, raw stored fields, hide element/category/type, open the model element in the inspector when it exists)
* [x] presets (server file `~/.config/rvt-viewer/vctl-presets.json`, localStorage fallback), per-view state restored from localStorage, JSON export
* [ ] more in `PROGRESS.md`
