# VSTYLE-API: visual style contract (c3-vctl <-> c3-viewer), DRAFT 2026-10-17
Owner of the implementation (materials, edges, transparency, patterns): c3-viewer, in web/app.js or a new web/vstyle.js. Owner of the UI (selector, presets, per-view autosave, default): c3-vctl, in web/viewctl.js.

## Styles (Revit Visual Style menu)
`hiddenline` (DEFAULT for new sessions), `shaded`, `consistent` (Consistent Colors), `realistic` (today's textured/shadowed look), `wireframe`.
Current look = `realistic`.

## window.vstyle (c3-viewer provides; until it exists the UI shows the selector disabled)
* `vstyle.list()` -> [{id, label}] in menu order.
* `vstyle.get()` -> {id, opts}
* `vstyle.set(id, opts?)` -> applies to the whole scene (world, caps, overlay edges), returns after the next frame is dirtied. `opts` (all optional, defaults in brackets):
  `edgeAngle` [30 deg], `silhouettes` [true], `hiddenLines` ['faint' | 'off' | 'dashed'], `lineWeight` [1.0 multiplier], `transparency` [true: honour per-category/element transparency overrides], `patterns` [true], `halftone` [true], `faceColor` ['#ffffff'].
* Event: `window.dispatchEvent(new CustomEvent('vstylechange', {detail: {id, opts}}))` after every change (also when changed by c3-viewer code).
* `vstyle.defaultId` read-only: 'hiddenline'.

## c3-vctl side (this branch)
* Header select `#vsSel` ("Style: Hidden line") next to the nav select, mirrored in the View control panel.
* Stored state: localStorage `vstyle:default` (user default, initial 'hiddenline'), per view `vstyle:{mid}:{viewId|model}` = {id, opts}; opening a view applies its stored style, else the default; changing the style while a view is open saves it for that view (autosave). Presets (server file `~/.config/rvt-viewer/vctl-presets.json`) carry `style: {id, opts}` next to the annotation state; `?vs=hiddenline` in the URL overrides the default for the session.
* Without window.vstyle the UI still stores/restores the choice and fires nothing else.
