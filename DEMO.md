# Demo script (one page)

Everything runs offline, no Revit, no Autodesk SDK. Prepare once before the interview, then every open is instant.

## Before (5-10 minutes, any time earlier the same day)
    ~/src/rvt-viewer/bin/rvt-view --prepare ~/rvt-research/corpus/2020/20_Residential_Sample_Project.rvt ~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt ~/rvt-research/corpus/2026/58_Snowdon_Towers_Sample_Facades.rvt
It converts and caches each model, pre-renders all sheets and views, and prints `READY: <command>` per file. If a peer changes the reader afterwards, the prepared model still opens instantly (a small "newer reader available" chip appears bottom right; ignore it or hide it with x).

## 1. The house (2020 Residential, 10 MB): materials and real geometry
    ~/src/rvt-viewer/bin/rvt-view ~/rvt-research/corpus/2020/20_Residential_Sample_Project.rvt
* Opens in ~2 s. Say: "a native .rvt, read by our own parser: no Revit, no Autodesk SDK".
* Orbit (left drag), pan (right drag), zoom (wheel). Untick **Planting** in the Model tree to see the house.
* Point at the stone chimney, the shake roof, the lap siding, the red door, glass and white sash: per-face materials from the file (25/25 sampled elements match Revit's own face materials), texture bitmaps tiled at the material's real-world size.
* **Materials** tab: Revit's own swatch images stored in the file; click a row to isolate where it is used. Click a swatch for colour/texture provenance.
* Click a window: the inspector shows its parameters, type, IfcGUID, and the geometry badge (saved mesh, surfaces, closed solid).
* **Section** (box or plane) to cut the house open; **Measure** with snapping.

## 2. The building (2024 Snowdon Towers Structural, 28 MB): scale and structure
    ~/src/rvt-viewer/bin/rvt-view ~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt --sheets
* Opens directly on the **Sheets** page: 12 sheets, 104 views drawn from the file (plans, sections, elevations with annotations). Click a viewport to open that view; click an element in a drawing to select it in 3D.
* **Model (3D)**: levels and grids labelled; Levels tab isolates a floor; search "W12" or "Concrete" (parameter values are searchable).
* **Coverage** tab: honest numbers per class (true geometry / rebuilt / box only) and why.

## 3. Curved facade (2026 Snowdon Towers Facades, 53 MB): newest format version
    ~/src/rvt-viewer/bin/rvt-view ~/rvt-research/corpus/2026/58_Snowdon_Towers_Sample_Facades.rvt
* Revit 2026 file; curtain walls, mullions and curved panels from cones, revolutions, ruled and Hermite surfaces decoded from the file.

## If something goes wrong
* Window does not appear: the command prints `serving http://127.0.0.1:PORT/...`; open that URL in any browser.
* A model looks unfinished: the banner says STILL PARSING with a live counter; boxes turn into meshes as they decode.
* Close with Ctrl+C in the terminal (or close the window).
