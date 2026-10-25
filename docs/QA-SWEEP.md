# View/sheet fidelity QA sweep (c8-viewer, started 2026-10-25)

Request (orchestrator, user): confirm that rvt-viewer and rvt-sheets render views and sheets like real Revit, without artifacts: (a) Autodesk corpus vs Revit exports, (b) a stratified sample of ~60 office models (corpus, local only) vs the Revit PDF sets next to them; rank artifact classes by frequency, fix the top ones, re-measure.

## (a) Corpus, current numbers (aggregate, no renders committed)
Source: ~/src/rvt-qa out43 (rst/Commercial/Residential, 104 views) and out44 (Snowdon Structural/Facades, 124 views), qaall26 on dev 450d26f; finding classes counted per view (a view counts once per class).
| class | 2020 corpus (104 views) | Snowdon (124 views) |
|---|---|---|
| longline-missing / extra / extent, bubble-missing / extra | 70-84 | 91-96 |
| region-missing | 87 | 90 |
| geom-extra-element | 66 | 75 |
| region-differs / region-extra | 40 / 49 | 72 / 70 |
| geom-layer-missing | 41 | 50 |
| text-extra / text-moved / text-baseline / text-missing | 21 / 16 / 12 / - | 79 / 54 / 59 / 42 |
| registration-unreliable | 22 | - |
Reading: grid-bubble / long-line classes fire on almost every view (the detectors are sensitive; they rank by extent in the defect lists, not by presence). The text classes are the real Snowdon gap (text-extra 79, text-baseline 59, text-moved 54). View types in the sample: plans 22+56, sections 35+18, 3D 21+6, sheets 16+28, drafting 7+16.
Worst corpus views (qa-triage out43): 3D views score ~0 because registration against the Revit PNG is unreliable (View3D region-missing x8); real defects: Graphical Column Schedule 1250040 (text-missing x93, known, NEEDS-FROM-SHEETS), Typ. Wall at Grade 196826, cross section 237764, east 29154.

## 3D vision review (viewer side)
* ~/review-compare/3d_* side-by-side images are STALE (shot on 2026-10-17 before the geometry had loaded: block-only box preview or an empty canvas with the "newer model available / Update model" toast baked in). They must not be used for judging; regenerate with tools/hl_soft_all.py (browser free, host1/host2, numba) or tools/shot3d.py (browser).
* Current software hidden-line renders (viewer/43_Snowdon_.../*__ours3d_hl2.png, 2026-10-17 23:26, tools/side_by_side.py Revit | ours) vs Revit, Snowdon 43:
  - Structure Only 600158: geometry and line weights match; ours lacks the pink dashed level / grid lines outside the building (datums are drawn in the live viewer, not in the software renderer), the yellow floor-edge fills and the teal/orange column colours of the Revit filter overrides (V/G filters evaluated by the viewer, not hl_soft), and the framing hatch is darker.
  - Foundations 783735: footprint, piles and pile caps match; ours has small circles on slab tops (pile markers?) that Revit does not draw, and the frame is smaller (registration in the tool, not a geometry error).
  - Artefact of the capture tool, not of the renderer: the "newer reader available / Update model" toast appears in the corner of captures.

## Fresh software hidden-line sweep, Snowdon 43 (2024), 2026-10-25 (tools/queue_hlsoft_snow.sh on host2, tools/hl_soft_all.py)
Registered line F1 vs the Revit HLR PNGs, 7 hidden-line 3D views: Structure Only 600158 0.945, Walls 783844 0.928, Columns 783871 0.907, Framing 783882 0.999, Slabs 783925 0.969, Cover Sheet 923315 0.953, Foundations 783735 0.272. Mean 0.853 with Foundations, 0.950 without.
Foundations 0.272 is a MEASUREMENT failure, not a render defect: side by side (tools/side_by_side.py) footprint, piles, pile caps and slabs match Revit line for line, but our image is rendered at ~0.4 of the Revit scale and hl_score's registration (scale 0.31, correlation 0.29) fails; fix = render at the Revit frame in hl_soft (--like) or widen the scale search. Visual defects seen: (1) a few stray tick marks / tiny circles at slab tops and near the centre (pile markers?) that Revit does not draw; (2) Structure Only: no level / grid lines (pink dashed) and no filter colours (yellow slab edges, teal / orange columns) in the software renderer; the live viewer draws datums, the soft renderer does not. Recall is 0.94-1.00 everywhere, so the loss is extra ink (precision 0.83-0.95 on Walls / Columns).

## (b) corpus real-world sample: what exists next to the models
Method: private map.tsv (rvt-extract-test/private, id -> original path) + tools/qa_corpus.py counts PDFs in the model's folder and its parent. Result (71 models scanned): most corpus models sit in "1. Drawings Out/<issue>/<model>" folders with 0 PDFs next to the model; a handful have a PDF set directly in the folder (corpus-001: 24, 015: 2, 016: 102, 026: 24, 039: 43, 040: 4, 062: 5; single PDFs next to 051, 063, 064). Only 001, 016, 026, 039 and 062 have a usable set, and a PDF set is not guaranteed to come from that exact model version (issue folders mix models). So a stratified 60-model PDF comparison is NOT possible from the folders; options: (1) the handful with PDFs (sheet-level compare with rvt-qa qa/pdfvec.py), (2) Revit-VM exports on host2 (needs the models opened in Revit offline: write-lab harness), (3) model-only checks: conversion, element/triangle counts, our own render sanity (blank / wrong-scale detection) for all 41 convertible models (done: corpus sweep, NEEDS-FROM-READER item 29).

## Next
1. Finish the PDF scan, pick the models with a sheet-set PDF, run sheet-level qa-view / pdfvec on host1/host2.
2. Regenerate the Snowdon 3D side-by-sides fresh (hl_soft_all on host2) and review all 38 views by eye; log classes with ids here.
3. Fix top viewer-side classes: hl_soft/viewer level+grid lines in 3D, V/G filter colours (yellow fills, column colours), pile markers.
