# View control (Annotations panel)
Header button **Annotations** (or the `annotations` link on a plan/section row in the Views tab, or `?vc=VIEWID[&vcp=PRESET]` in the URL) shows the view-dependent content of a plan or section
(tags, text, dimensions, spot elevations, grids, levels, markers, hatches, linework) placed in model space on the 3D scene, as rvt-sheets draws it.
* **View**: pick a plan / section; the camera and clip follow the stored view.
* **Re-draws the view** (server round trip, cached): annotation scale 1:N (text, symbols and pen widths are regenerated exactly), detail level, view template on/off, filters on/off, plan cut plane (m), phase and phase filter.
* **Instant**: crop (model content only; annotations hang outside as in Revit), text on/off, text size x, font, symbol size x (about each element's anchor), line weight x, minimum px, on top / lift / opacity, hide the 3D model under the drawing, replace the viewer's own grids and levels by the view's datums.
* **Paper look**: white sheet, no 3D model, black linework.
* **Also show**: other plan/section views drawn faintly at their own height (stacked levels).
* **Visibility** tree, four modes: category (with subcategories) / layer / type (Revit class) / part (leaders, witness lines, arrows...) / element. Per category: checkbox, colour, line weight x, text size x, line pattern.
* **Picking**: hover tooltip; click highlights, shows category / class / id / stored fields, hides element / category / type, and opens the element in the inspector (full parameters) when it exists in the model.
* **Presets**: name + save / load / delete (stored in `~/.config/rvt-viewer/vctl-presets.json`, localStorage fallback); settings are also remembered per view; export JSON.
* Scenes come from the sheets server (`/sheets/api/{mid}/view/{id}.json`); big files should be warmed on host1 with `tools/vc_warm.sh FILE` then `h1run pull` of the printed cache dir, otherwise the first open decodes the model.
## Scripting
`window.vctl`: `toggle()`, `openView(id, preset?)`, `set({textSize, annoScale, layers, cats: {catId: {vis, color, wscale, tscale, dash}}, elems: {eid: {vis, color}}, parts, classes, crop, onTop, ...})`, `state()`, `pick(clientX, clientY)`.
HTTP: `/api/m/{mid}/vc/views|scene/{vid}|element/{eid}`, `/api/vc/presets`. Contract: CONTROL-API.md. Regression: `tools/vctltest.py URL VIEWID` (`VC_RERENDER=0` on big files). Placement test: `tools/vcalign.py URL VIEWID` (datum grids vs the reader's grids, plans and sections, mm offsets). Every view: `tools/vcsweep.py URL` (opens all drawable views, reports JS exceptions). Not overlaid: 3D views (their scenes hold only projected model linework, no annotations).
## Visual style (selector, per-view autosave, default)
Contract with c3-viewer: docs/VSTYLE-API.md (`window.vstyle.list/get/set`, event `vstylechange`). UI here: header select `#vsSel` and a "Visual style" row in the panel (both hidden until `window.vstyle` exists), style saved per view in localStorage `vstyle:{mid}:{viewId|model}`, user default `vstyle:default` (initial `hiddenline`, set with the panel's "default" button), presets carry `style`, `?vs=ID` overrides the default. Scripting: `vctl.vstyle.get() / set(id, opts, save) / setDefault()`. Test: `tools/vstyletest.py URL VIEWID` (mock vstyle).
