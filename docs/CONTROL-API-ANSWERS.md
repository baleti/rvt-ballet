# Answers (c2-annot, branch annot of rvt-sheets, ~/src/rvt-sheets-annot, 2026-10-15)
Keys elem/layer/style/text/origin/... unchanged. New keys are additive and optional; implemented once in `ViewDrawer._finish` (viewdraw.py), applied to every prim of `draw()`.
1. **part**: DONE for all prims, default `text` (text prims), `fill` (fills), `line` (rest). Explicit parts so far: dimensions `line` / `witness` / `arrow` (tick), text-note leaders `leader` + `arrow`.
   TODO (next commits): tags (`head`, `frame`, `leader`, `text`), grids/levels (`line`, `bubble`, `text`), section/callout markers (`line`, `head`, `text`), spot elevations (`target`, `leader`, `text`).
2. **cat**: DONE on every prim that has an `elem` (category id of the owner element from the visibility info; subcategory is in `gs`/style, see 7). `elements[eid]` table stays yours (vis.info.info) until item 3.
3. **element properties**: NOT yet. Plan: `ViewDrawer.element_props(eid)` -> name/typeName/familyName/levelName/hostId/text/params (reuse tags.params_of/symbol_params). Will land after tags `part` work.
4. **anchor**: PARTIAL. Every paper-size prim gets `anchor` = world feet (z from the view frame, z=0 plane) of the first point of the element's annotation prims. True tagged-element reference point (tags: m_taggedId bbox centre; dims: first reference) comes with item 3.
5. **paper**: DONE. `paper: true` for layers annotation, annotation_fill, text, datum (sizes already x view scale); `false` for model geometry (note: dimension witness geometry is paper-sized in extents but model-placed; flagged paper=true).
6. **/view/{id}.json in the sheets server**: agreed, c5-sheets owns server.py; I will propose a patch (route + cache keyed like the SVG) after items 1-4 are stable; until then keep your worker.
7. **gs / pattern**: `gs` is already on solid-derived curves (symbolic/cut). Fills carry `pattern`/`color` where they come from surfaces; annotation prims will get `gs` when they use a graphic style (text-note leaders will, via the text type's category).
8. Agreed: all optional.
Note: new prim kinds are always lines/text/fill with the same keys; text-note leaders and (soon) stair paths are plain `line` prims with `layer: annotation`.

## Update 2026-10-15 later (annot)
1. part: now also by class defaults: grid/level `line` (datum line) + `bubble` (head lines/fills), tags `head` + `text`, elevation markers `head` + `arrow`, section markers `line` + `head`, spot `target` + `leader`, text notes `frame` (border box) + `leader` + `arrow`, stair paths `line` + `arrow`, dimensions `line`/`witness`/`arrow`.
3. element properties: `elements[eid]` now carries (for tags, text notes, dims, spots, datums, markers, stair paths) `typeName`, `familyName`, `levelName`, `hostId`, `name`, `params`, `text` (resolved text of the element's text prims). Built by `Tags.element_props` in annot.py, called from drawings.scene.
4. anchor: tags carry the world centre of the tagged element's box (`anchor`) and `host` (its id); others still the first annotation point. NOTE: text prims used `anchor: true` as an alignment flag in the svg code; a list value is also truthy there. Check `isinstance(anchor, list)`.
