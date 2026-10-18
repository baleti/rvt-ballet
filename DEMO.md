# Demo script (one page)

Everything runs offline, no Revit, no Autodesk SDK. Prepare once before the interview, then every open is instant.

## Before (5-10 minutes, any time earlier the same day)
    ~/src/rvt-viewer/bin/rvt-view --prepare ~/rvt-research/corpus/2020/20_Residential_Sample_Project.rvt ~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt ~/rvt-research/corpus/2026/58_Snowdon_Towers_Sample_Facades.rvt
It converts and caches each model, pre-renders all sheets and views, and prints `READY: <command>` per file. If a peer changes the reader afterwards, the prepared model still opens instantly (a small "newer reader available" chip appears bottom right; ignore it or hide it with x).

## 1. The house (2020 Residential, 10 MB): materials and real geometry
    ~/src/rvt-viewer/bin/rvt-view ~/rvt-research/corpus/2020/20_Residential_Sample_Project.rvt --hide Planting,Entourage
* **Visual style**: models open in Revit's **Hidden line** style (white faces, black edges, faint hidden lines; header box `Style`). For the textured house switch the Style box to **Realistic** (or open `?style=realistic`); Shaded, Consistent colors and Wireframe are in the same box.
* In Hidden line, model surface patterns (shingle courses, lap siding, brick bond) are drawn as hatch lines like Revit's; plan / section / elevation views open in a parallel (orthographic-looking) projection, e.g. Views tab, `South` elevation of the Residential house. (Models converted before 2026-10-18 need `--prepare` again to carry the pattern data.)
* Opens in ~2 s. Say: "a native .rvt, read by our own parser: no Revit, no Autodesk SDK".
* Navigation is Revit's: **Shift + middle-drag = orbit**, **middle-drag = pan**, **wheel = zoom at the cursor**, double middle-click = zoom to fit, click the ViewCube to snap to a view; left click selects, right button does nothing. Touchpad without a middle button: **Alt + left-drag = orbit**, **Alt + Shift + left-drag = pan**, two-finger scroll / pinch zooms, key F fits (the toolbar `Nav` box can switch to the classic left-drag orbit). `--hide Planting,Entourage` starts with the trees hidden so the house is visible at once (without it, untick **Planting** in the Model tree).
* Point at the stone chimney, the shake roof, the lap siding, the red door, glass and white sash: per-face materials from the file (25/25 sampled elements match Revit's own face materials), texture bitmaps tiled at the material's real-world size.
* **Materials** tab: Revit's own swatch images stored in the file; click a row to isolate where it is used. Click a swatch for colour/texture provenance.
* Click a window: the inspector shows its parameters, type, IfcGUID, the geometry badge (saved mesh, surfaces, closed solid) and how well the reader matches Revit for that element class over the whole corpus (docs/FIDELITY-FINAL.md: e.g. walls 99.3%, family instances 99.5%).
* **Section** (box or plane) to cut the house open: cut walls, slabs and furniture are filled dark (poche) like a Revit section; **Measure** with snapping.
* **Views** tab: click `first floor` (plan) or `building section`: the view opens at Revit's stored cut plane with cut walls / slabs / roof filled dark, like the drawing in Revit. 'close view' returns.
* **Annotations** (header button, or the `annotations` link on a plan row in the Views tab): the view's tags, text, dimensions, grids, levels and markers appear in model space on the 3D scene, as the sheets renderer draws them. Switch annotation scale (1:48 ...), hide a category or a family type, change colour / line weight / text size, click a tag to see its properties; save a preset. Details: docs/VIEW-CONTROL.md.
* **Shadows** (or key L) toggles sun shadows; the sun follows the view so shadows always fall visibly beside objects.

## 2. The building (2024 Snowdon Towers Structural, 28 MB): scale and structure
    ~/src/rvt-viewer/bin/rvt-view ~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt --sheets
* Opens directly on the **Sheets** page: 12 sheets, 104 views drawn from the file (plans, sections, elevations with annotations). Click a viewport to open that view; click an element in a drawing to select it in 3D.
* **Model (3D)**: levels and grids labelled; Levels tab isolates a floor; search "W12" or "Concrete" (parameter values are searchable).
* **Coverage** tab: honest numbers per class (true geometry / rebuilt / box only) and why.

## 3. Curved facade (2026 Snowdon Towers Facades, 53 MB): newest format version
    ~/src/rvt-viewer/bin/rvt-view ~/rvt-research/corpus/2026/58_Snowdon_Towers_Sample_Facades.rvt
* Revit 2026 file; curtain walls, mullions and curved panels from cones, revolutions, ruled and Hermite surfaces decoded from the file.
* Zoom to the street front: running and soldier-course brick, granite, quartz, stained wood frames and copper come from Revit's Advanced (Prism) appearances, textured at their real-world size.

**Facades sheets**: the first pre-render of these big drawings can take long; after `--prepare` they are cached (re-warm with `tools/queue_warm.sh` when host1 is free). Check `curl localhost:PORT/sheets/api/<id>/cache.json` or the toolbar badge ("sheets cached"); if it says not cached, open Facades WITHOUT `--sheets` (the 3D model is instant) or run `~/src/rvt-sheets/rvt-sheets warm <file> --host1` first.

## If something goes wrong
* Window does not appear: the command prints `serving http://127.0.0.1:PORT/...`; open that URL in any browser.
* A model looks unfinished: the banner says STILL PARSING with a live counter; boxes turn into meshes as they decode.
* Close with Ctrl+C in the terminal (or close the window).

## Verified (2026-10-16)
* All three demo files pass tools/demo_smoke.sh on master (main page, materials, sheets page and doc); tools/uitest12.py (Revit navigation with real input events) and tools/vctltest.py (annotation control) pass. Whole corpus: 89 / 89 files pass (table below, docs/SWEEP.md); speed per file: docs/SPEED.md; geometry accuracy per class and year: docs/FIDELITY-FINAL.md.

## Verified (2026-10-14)
* `rvt-view FILE --sheets` end to end in headless Chromium (banner, 3D loads, Sheets page ready, Model button back, no JS exceptions): 2020 Residential (first picture 2.7 s, sheets page 2 s), 2024 Snowdon Structural (2.5 s, 12 sheets / 104 views), 2026 Snowdon Facades (3.1 s, 2 sheets / 47 views). The real app window (workspace 178, silent) opens too.
* Browser render check on one model per year 2017-2026 (tools/uisweep.py): 9 / 9 draw, pick and list materials. Feature tests: tools/uitest6.py (views, section, measure, isolate), uitest7.py (navigation), uitest11.py (materials).
* Bad input: missing / empty / non-Revit / folder paths exit with a one-line reason, truncated files show the reason in the page.

<!-- RESULTS -->

## Functionality test over the whole corpus (2026-10-16, tools/sweep.py + tools/functest.py on host1, re-run 2026-10-16 after the Rust speed fixes)

**89 / 89 files pass** (convert as `rvt-view` does, then through the real server: valid GLB, materials + swatch images, inspector, search, the sheets plug-in with one sheet SVG and one view SVG). "true geometry" = share of building elements drawn from the file's own geometry (saved graphics / rebar shapes / decoded B-rep); template (.rte) files have almost no model geometry.

| year | file | MB | convert s | elements | triangles | true geometry | glb | materials used (swatches) | inspector+search | sheets / views drawn | result |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | 00_rst_basic_sample_project.rvt | 6.0 | 10.5 | 13934 | 469776 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2017 | 01_rst_advanced_sample_project.rvt | 13.1 | 14.1 | 13486 | 292358 | 100% | ok | 8 (194) | ok | ok 9/31 | **PASS** |
| 2017 | 02_Arch_Link_Model.rvt | 14.2 | 28.3 | 16906 | 866808 | 99% | ok | 52 (186) | ok | ok 2/42 | **PASS** |
| 2017 | 03_rac_advanced_sample_project.rvt | 15.3 | 23.2 | 17132 | 850081 | 99% | ok | 50 (167) | ok | ok 2/40 | **PASS** |
| 2017 | 04_rme_basic_sample_project.rvt | 27.9 | 68.4 | 27393 | 2153859 | 97% | ok | 35 (175) | ok | ok 8/93 | **PASS** |
| 2017 | 05_rme_advanced_sample_project.rvt | 33.1 | 45.7 | 29016 | 1993846 | 98% | ok | 35 (175) | ok | ok 8/96 | **PASS** |
| 2018 | 06_rst_basic_sample_project.rvt | 5.8 | 12.2 | 13997 | 469743 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2018 | 07_rst_advanced_sample_project.rvt | 13.3 | 12.1 | 13551 | 292454 | 100% | ok | 9 (194) | ok | ok 9/31 | **PASS** |
| 2018 | 08_Arch_Link_Model.rvt | 14.3 | 22.9 | 16972 | 866808 | 99% | ok | 52 (186) | ok | ok 2/42 | **PASS** |
| 2018 | 09_rac_advanced_sample_project.rvt | 15.5 | 25.2 | 17198 | 850081 | 99% | ok | 50 (167) | ok | ok 2/40 | **PASS** |
| 2018 | 10_rme_basic_sample_project.rvt | 28.4 | 60.2 | 27459 | 2153657 | 97% | ok | 35 (175) | ok | ok 8/93 | **PASS** |
| 2018 | 11_rme_advanced_sample_project.rvt | 33.7 | 50.2 | 29081 | 1993860 | 98% | ok | 35 (175) | ok | ok 8/96 | **PASS** |
| 2019 | 12_rst_basic_sample_project.rvt | 5.9 | 10.1 | 13810 | 469755 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2019 | 13_rst_advanced_sample_project.rvt | 13.5 | 11.8 | 13543 | 292374 | 100% | ok | 9 (194) | ok | ok 9/31 | **PASS** |
| 2019 | 14_Arch_Link_Model.rvt | 14.5 | 21.0 | 16971 | 866808 | 99% | ok | 52 (186) | ok | ok 2/42 | **PASS** |
| 2019 | 15_rac_advanced_sample_project.rvt | 15.6 | 21.7 | 17197 | 850093 | 99% | ok | 50 (167) | ok | ok 2/40 | **PASS** |
| 2019 | 16_rme_basic_sample_project.rvt | 28.5 | 58.9 | 27471 | 2153911 | 97% | ok | 34 (175) | ok | ok 8/93 | **PASS** |
| 2019 | 17_rme_advanced_sample_project.rvt | 34.0 | 47.6 | 29101 | 1993910 | 98% | ok | 34 (175) | ok | ok 8/96 | **PASS** |
| 2020 | 18_rst_basic_sample_project.rvt | 5.9 | 9.8 | 13853 | 469743 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2020 | 19_Commercial_Sample_Project.rvt | 7.4 | 6.1 | 7042 | 116068 | 97% | ok | 43 (103) | ok | ok 4/24 | **PASS** |
| 2020 | 20_Residential_Sample_Project.rvt | 10.2 | 4.8 | 7277 | 103454 | 100% | ok | 58 (124) | ok | ok 4/25 | **PASS** |
| 2020 | 21_rst_advanced_sample_project.rvt | 13.6 | 10.4 | 13586 | 292454 | 100% | ok | 9 (194) | ok | ok 9/31 | **PASS** |
| 2020 | 22_rme_basic_sample_project.rvt | 29.1 | 59.0 | 27511 | 2153693 | 97% | ok | 35 (175) | ok | ok 8/93 | **PASS** |
| 2020 | 23_rme_advanced_sample_project.rvt | 34.8 | 47.0 | 29132 | 1993882 | 98% | ok | 35 (175) | ok | ok 8/95 | **PASS** |
| 2021 | 24_rst_basic_sample_project.rvt | 6.2 | 10.0 | 13924 | 469755 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2021 | 25_rst_advanced_sample_project.rvt | 14.4 | 10.6 | 13659 | 292370 | 100% | ok | 9 (194) | ok | ok 9/31 | **PASS** |
| 2021 | 26_Arch_Link_Model.rvt | 15.1 | 20.7 | 17084 | 866820 | 99% | ok | 52 (186) | ok | ok 2/42 | **PASS** |
| 2021 | 27_Technical_school-current_m.rvt | 16.3 | 23.0 | 17313 | 850117 | 99% | ok | 50 (167) | ok | ok 2/40 | **PASS** |
| 2021 | 28_rme_basic_sample_project.rvt | 30.4 | 59.0 | 27583 | 2153935 | 97% | ok | 34 (175) | ok | ok 8/93 | **PASS** |
| 2021 | 29_rme_advanced_sample_project.rvt | 36.5 | 81.2 | 29204 | 1993922 | 98% | ok | 34 (175) | ok | ok 8/95 | **PASS** |
| 2021 | 60_Precast_Detailing-DefaultMetricCHS.rte | 16.3 | 3.8 | 9918 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2021 | 61_Precast_Detailing-DefaultMetricCSY.rte | 16.5 | 3.7 | 9919 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2021 | 62_Construction-DefaultMetric.rte | 5.0 | 2.5 | 5426 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| 2022 | 30_rst_basic_sample_project.rvt | 6.5 | 10.4 | 14035 | 471367 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2022 | 31_rst_advanced_sample_project.rvt | 14.4 | 73.8 | 13733 | 292370 | 100% | ok | 9 (194) | ok | ok 9/31 | **PASS** |
| 2022 | 32_Arch_Link_Model.rvt | 15.1 | 20.8 | 17157 | 866820 | 99% | ok | 52 (186) | ok | ok 2/42 | **PASS** |
| 2022 | 33_Technical_school-current_m.rvt | 16.3 | 23.2 | 17386 | 850117 | 99% | ok | 50 (167) | ok | ok 2/40 | **PASS** |
| 2022 | 34_rme_basic_sample_project.rvt | 30.5 | 59.3 | 27656 | 2153935 | 97% | ok | 34 (175) | ok | ok 8/93 | **PASS** |
| 2022 | 35_rme_advanced_sample_project.rvt | 36.7 | 91.6 | 29276 | 1993922 | 98% | ok | 34 (175) | ok | ok 8/95 | **PASS** |
| 2022 | 63_Precast_Detailing-DefaultMetricCHS.rte | 16.4 | 3.6 | 9991 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2022 | 64_Precast_Detailing-DefaultMetricCSY.rte | 16.6 | 3.5 | 9992 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2022 | 65_Construction-DefaultMetric.rte | 5.0 | 2.6 | 5502 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| 2023 | 36_rst_basic_sample_project.rvt | 6.5 | 10.3 | 13820 | 471254 | 100% | ok | 18 (79) | ok | ok 8/37 | **PASS** |
| 2023 | 37_rst_advanced_sample_project.rvt | 14.4 | 10.5 | 13727 | 298086 | 100% | ok | 10 (194) | ok | ok 9/31 | **PASS** |
| 2023 | 38_Arch_Link_Model.rvt | 15.6 | 21.7 | 17350 | 871685 | 99% | ok | 52 (188) | ok | ok 2/42 | **PASS** |
| 2023 | 39_Technical_school-current_m.rvt | 16.4 | 23.4 | 17477 | 854923 | 99% | ok | 50 (168) | ok | ok 2/40 | **PASS** |
| 2023 | 40_rme_basic_sample_project.rvt | 30.8 | 60.3 | 27750 | 2157401 | 97% | ok | 34 (175) | ok | ok 8/93 | **PASS** |
| 2023 | 41_rme_advanced_sample_project.rvt | 37.1 | 74.1 | 29370 | 1997568 | 98% | ok | 34 (175) | ok | ok 8/95 | **PASS** |
| 2023 | 66_Precast_Detailing-DefaultMetricCHS.rte | 15.7 | 3.7 | 10088 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2023 | 67_Precast_Detailing-DefaultMetricCSY.rte | 15.9 | 3.6 | 10090 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2023 | 68_Construction-DefaultMetric.rte | 5.0 | 2.6 | 5591 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| 2024 | 42_Snowdon_Towers_Sample_HVAC.rvt | 22.0 | 15.5 | 12679 | 764638 | 100% | ok | 0 (39) | ok | ok 18/29 | **PASS** |
| 2024 | 43_Snowdon_Towers_Sample_Structural.rvt | 27.9 | 12.6 | 16571 | 667157 | 100% | ok | 6 (79) | ok | ok 12/60 | **PASS** |
| 2024 | 44_Snowdon_Towers_Sample_Electrical.rvt | 40.3 | 23.6 | 19769 | 2236556 | 100% | ok | 18 (48) | ok | ok 26/55 | **PASS** |
| 2024 | 45_Snowdon_Towers_Sample_Plumbing.rvt | 41.6 | 46.3 | 25738 | 3146974 | 100% | ok | 4 (72) | ok | ok 27/68 | **PASS** |
| 2024 | 46_Snowdon_Towers_Sample_Facades.rvt | 52.7 | 8.8 | 9534 | 294465 | 100% | ok | 20 (74) | ok | ok 2/28 | **PASS** |
| 2024 | 47_Snowdon_Towers_Sample_Site.rvt | 54.4 | 7.8 | 11711 | 141638 | 100% | ok | 12 (76) | ok | ok 3/17 | **PASS** |
| 2024 | 69_Precast_Detailing-DefaultMetricCHS.rte | 16.7 | 3.9 | 10101 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2024 | 70_Precast_Detailing-DefaultMetricCSY.rte | 16.9 | 3.8 | 10110 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2024 | 71_Construction-DefaultMetric.rte | 5.3 | 2.6 | 5603 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| 2025 | 48_Snowdon_Towers_Sample_HVAC.rvt | 22.2 | 16.1 | 12716 | 764638 | 100% | ok | 0 (39) | ok | ok 18/29 | **PASS** |
| 2025 | 49_Snowdon_Towers_Sample_Structural.rvt | 27.9 | 12.7 | 16612 | 667157 | 100% | ok | 6 (79) | ok | ok 12/60 | **PASS** |
| 2025 | 50_Snowdon_Towers_Sample_Electrical.rvt | 40.5 | 23.4 | 19810 | 2236556 | 100% | ok | 18 (48) | ok | ok 26/55 | **PASS** |
| 2025 | 51_Snowdon_Towers_Sample_Plumbing.rvt | 41.7 | 45.9 | 25750 | 3145918 | 100% | ok | 4 (72) | ok | ok 27/68 | **PASS** |
| 2025 | 52_Snowdon_Towers_Sample_Facades.rvt | 52.7 | 8.7 | 9571 | 294465 | 100% | ok | 20 (74) | ok | ok 2/28 | **PASS** |
| 2025 | 53_Snowdon_Towers_Sample_Site.rvt | 54.3 | 7.7 | 11750 | 141476 | 100% | ok | 12 (76) | ok | ok 3/17 | **PASS** |
| 2025 | 72_Precast_Detailing-DefaultMetricCHS.rte | 16.8 | 3.7 | 10142 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2025 | 73_Precast_Detailing-DefaultMetricCSY.rte | 17.0 | 3.7 | 10151 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2025 | 74_Construction-DefaultMetric.rte | 5.3 | 2.8 | 5640 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| 2026 | 54_Snowdon_Towers_Sample_HVAC.rvt | 22.2 | 16.5 | 12791 | 764638 | 100% | ok | 0 (39) | ok | ok 18/29 | **PASS** |
| 2026 | 55_Snowdon_Towers_Sample_Structural.rvt | 27.7 | 12.5 | 16678 | 667205 | 100% | ok | 6 (79) | ok | ok 12/60 | **PASS** |
| 2026 | 56_Snowdon_Towers_Sample_Electrical.rvt | 41.6 | 23.7 | 19901 | 2236556 | 100% | ok | 18 (48) | ok | ok 26/55 | **PASS** |
| 2026 | 57_Snowdon_Towers_Sample_Plumbing.rvt | 41.7 | 46.2 | 25837 | 3146022 | 100% | ok | 4 (72) | ok | ok 27/68 | **PASS** |
| 2026 | 58_Snowdon_Towers_Sample_Facades.rvt | 52.6 | 8.8 | 9645 | 294465 | 100% | ok | 20 (74) | ok | ok 2/28 | **PASS** |
| 2026 | 59_Snowdon_Towers_Sample_Site.rvt | 60.7 | 7.4 | 11834 | 144041 | 100% | ok | 12 (76) | ok | ok 3/17 | **PASS** |
| 2026 | 75_Precast_Detailing-DefaultMetricCHS.rte | 16.7 | 3.7 | 10217 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2026 | 76_Precast_Detailing-DefaultMetricCSY.rte | 16.9 | 3.7 | 10226 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2026 | 77_Construction-DefaultMetric.rte | 5.2 | 2.8 | 5714 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| rfa-2016 | rac_basic_sample_family-2016.rfa | 0.3 | 1.7 | 1596 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2017 | rac_basic_sample_family-2017.rfa | 0.3 | 1.7 | 1631 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2018 | rac_basic_sample_family-2018.rfa | 0.3 | 1.8 | 1693 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2019 | rac_basic_sample_family-2019.rfa | 0.3 | 1.7 | 1713 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2020 | racbasicsamplefamily-2020.rfa | 0.3 | 1.7 | 1750 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2021 | racbasicsamplefamily-2021.rfa | 0.3 | 1.8 | 1814 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2022 | racbasicsamplefamily-2022.rfa | 0.4 | 1.9 | 1879 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2023 | racbasicsamplefamily-2023.rfa | 0.4 | 1.8 | 1964 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2024 | racbasicsamplefamily-2024.rfa | 0.4 | 1.8 | 1975 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2025 | racbasicsamplefamily-2025.rfa | 0.4 | 1.8 | 1984 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2026 | racbasicsamplefamily-2026.rfa | 0.4 | 1.8 | 1992 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |

<!-- /RESULTS -->
