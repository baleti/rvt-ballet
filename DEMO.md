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
* **Shadows** (or key L) toggles sun shadows; the sun follows the view so shadows always fall visibly beside objects.

## 2. The building (2024 Snowdon Towers Structural, 28 MB): scale and structure
    ~/src/rvt-viewer/bin/rvt-view ~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt --sheets
* Opens directly on the **Sheets** page: 12 sheets, 104 views drawn from the file (plans, sections, elevations with annotations). Click a viewport to open that view; click an element in a drawing to select it in 3D.
* **Model (3D)**: levels and grids labelled; Levels tab isolates a floor; search "W12" or "Concrete" (parameter values are searchable).
* **Coverage** tab: honest numbers per class (true geometry / rebuilt / box only) and why.

## 3. Curved facade (2026 Snowdon Towers Facades, 53 MB): newest format version
    ~/src/rvt-viewer/bin/rvt-view ~/rvt-research/corpus/2026/58_Snowdon_Towers_Sample_Facades.rvt
* Revit 2026 file; curtain walls, mullions and curved panels from cones, revolutions, ruled and Hermite surfaces decoded from the file.

**Facades sheets**: their drawings are big (about 25 minutes to pre-render). Check `curl localhost:PORT/sheets/api/<id>/cache.json` or the toolbar badge ("sheets cached"); if it says not cached, open Facades WITHOUT `--sheets` (the 3D model is instant) or run `~/src/rvt-sheets/rvt-sheets warm <file> --remote-host` first.

## If something goes wrong
* Window does not appear: the command prints `serving http://127.0.0.1:PORT/...`; open that URL in any browser.
* A model looks unfinished: the banner says STILL PARSING with a live counter; boxes turn into meshes as they decode.
* Close with Ctrl+C in the terminal (or close the window).

## Verified (2026-10-14)
* `rvt-view FILE --sheets` end to end in headless Chromium (banner, 3D loads, Sheets page ready, Model button back, no JS exceptions): 2020 Residential (first picture 2.7 s, sheets page 2 s), 2024 Snowdon Structural (2.5 s, 12 sheets / 104 views), 2026 Snowdon Facades (3.1 s, 2 sheets / 47 views). The real app window (workspace 178, silent) opens too.
* Browser render check on one model per year 2017-2026 (tools/uisweep.py): 9 / 9 draw, pick and list materials. Feature tests: tools/uitest6.py (views, section, measure, isolate), uitest7.py (navigation), uitest11.py (materials).
* Bad input: missing / empty / non-Revit / folder paths exit with a one-line reason, truncated files show the reason in the page.

<!-- RESULTS -->

## Functionality test over the whole corpus (2026-10-15, tools/sweep.py + tools/functest.py on remote-host)

**121 / 121 files pass** (convert as `rvt-view` does, then through the real server: valid GLB, materials + swatch images, inspector, search, the sheets plug-in with one sheet SVG and one view SVG). "true geometry" = share of building elements drawn from the file's own geometry (saved graphics / rebar shapes / decoded B-rep); template (.rte) files have almost no model geometry.

| year | file | MB | convert s | elements | triangles | true geometry | glb | materials used (swatches) | inspector+search | sheets / views drawn | result |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | 00_rst_basic_sample_project.rvt | 6.0 | 5.7 | 13934 | 170152 | 86% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2017 | 01_rst_advanced_sample_project.rvt | 13.1 | 8.7 | 13486 | 247630 | 98% | ok | 8 (194) | ok | ok 9/31 | **PASS** |
| 2017 | 02_Arch_Link_Model.rvt | 14.2 | 15.9 | 16906 | 866820 | 99% | ok | 52 (186) | ok | ok 2/42 | **PASS** |
| 2017 | 03_rac_advanced_sample_project.rvt | 15.3 | 16.9 | 17132 | 850153 | 99% | ok | 50 (167) | ok | ok 2/40 | **PASS** |
| 2017 | 04_rme_basic_sample_project.rvt | 27.9 | 47.9 | 27393 | 2153919 | 97% | ok | 35 (175) | ok | ok 8/93 | **PASS** |
| 2017 | 05_rme_advanced_sample_project.rvt | 33.1 | 75.5 | 29016 | 1993906 | 98% | ok | 35 (175) | ok | ok 8/96 | **PASS** |
| 2018 | 06_rst_basic_sample_project.rvt | 5.8 | 6.3 | 13997 | 469767 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2018 | 07_rst_advanced_sample_project.rvt | 13.3 | 8.5 | 13551 | 292490 | 100% | ok | 9 (194) | ok | ok 9/31 | **PASS** |
| 2018 | 08_Arch_Link_Model.rvt | 14.3 | 15.6 | 16972 | 866820 | 99% | ok | 52 (186) | ok | ok 2/42 | **PASS** |
| 2018 | 09_rac_advanced_sample_project.rvt | 15.5 | 18.7 | 17198 | 850153 | 99% | ok | 50 (167) | ok | ok 2/40 | **PASS** |
| 2018 | 10_rme_basic_sample_project.rvt | 28.4 | 42.1 | 27459 | 2153717 | 97% | ok | 35 (175) | ok | ok 8/93 | **PASS** |
| 2018 | 11_rme_advanced_sample_project.rvt | 33.7 | 36.5 | 29081 | 1993920 | 98% | ok | 35 (175) | ok | ok 8/96 | **PASS** |
| 2019 | 12_rst_basic_sample_project.rvt | 5.9 | 6.3 | 13810 | 469779 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2019 | 13_rst_advanced_sample_project.rvt | 13.5 | 12.0 | 13543 | 292410 | 100% | ok | 9 (194) | ok | ok 9/31 | **PASS** |
| 2019 | 14_Arch_Link_Model.rvt | 14.5 | 14.6 | 16971 | 866820 | 99% | ok | 52 (186) | ok | ok 2/42 | **PASS** |
| 2019 | 15_rac_advanced_sample_project.rvt | 15.6 | 18.9 | 17197 | 850165 | 99% | ok | 50 (167) | ok | ok 2/40 | **PASS** |
| 2019 | 16_rme_basic_sample_project.rvt | 28.5 | 47.7 | 27471 | 2153971 | 97% | ok | 34 (175) | ok | ok 8/93 | **PASS** |
| 2019 | 17_rme_advanced_sample_project.rvt | 34.0 | 42.0 | 29101 | 1993970 | 98% | ok | 34 (175) | ok | ok 8/96 | **PASS** |
| 2020 | 18_rst_basic_sample_project.rvt | 5.9 | 6.1 | 13853 | 469767 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2020 | 19_Commercial_Sample_Project.rvt | 7.4 | 5.3 | 7042 | 116080 | 97% | ok | 43 (103) | ok | ok 4/24 | **PASS** |
| 2020 | 20_Residential_Sample_Project.rvt | 10.2 | 4.7 | 7277 | 103466 | 100% | ok | 58 (124) | ok | ok 4/25 | **PASS** |
| 2020 | 21_rst_advanced_sample_project.rvt | 13.6 | 10.5 | 13586 | 292490 | 100% | ok | 9 (194) | ok | ok 9/31 | **PASS** |
| 2020 | 22_rme_basic_sample_project.rvt | 29.1 | 47.3 | 27511 | 2153777 | 97% | ok | 35 (175) | ok | ok 8/93 | **PASS** |
| 2020 | 23_rme_advanced_sample_project.rvt | 34.8 | 41.4 | 29132 | 1993966 | 98% | ok | 35 (175) | ok | ok 8/95 | **PASS** |
| 2021 | 24_rst_basic_sample_project.rvt | 6.2 | 6.1 | 13924 | 469791 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2021 | 25_rst_advanced_sample_project.rvt | 14.4 | 9.3 | 13659 | 292406 | 100% | ok | 9 (194) | ok | ok 9/31 | **PASS** |
| 2021 | 26_Arch_Link_Model.rvt | 15.1 | 14.8 | 17084 | 866832 | 99% | ok | 52 (186) | ok | ok 2/42 | **PASS** |
| 2021 | 27_Technical_school-current_m.rvt | 16.3 | 19.0 | 17313 | 850189 | 99% | ok | 50 (167) | ok | ok 2/40 | **PASS** |
| 2021 | 28_rme_basic_sample_project.rvt | 30.4 | 52.1 | 27583 | 2153983 | 97% | ok | 34 (175) | ok | ok 8/93 | **PASS** |
| 2021 | 29_rme_advanced_sample_project.rvt | 36.5 | 52.6 | 29204 | 1993970 | 98% | ok | 34 (175) | ok | ok 8/95 | **PASS** |
| 2021 | 60_Precast_Detailing-DefaultMetricCHS.rte | 16.3 | 7.0 | 9918 | 60 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2021 | 61_Precast_Detailing-DefaultMetricCSY.rte | 16.5 | 6.5 | 9919 | 60 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2021 | 62_Construction-DefaultMetric.rte | 5.0 | 1.9 | 5426 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| 2022 | 30_rst_basic_sample_project.rvt | 6.5 | 6.2 | 14035 | 471403 | 100% | ok | 17 (76) | ok | ok 8/37 | **PASS** |
| 2022 | 31_rst_advanced_sample_project.rvt | 14.4 | 43.4 | 13733 | 292406 | 100% | ok | 9 (194) | ok | ok 9/31 | **PASS** |
| 2022 | 32_Arch_Link_Model.rvt | 15.1 | 15.2 | 17157 | 866820 | 99% | ok | 52 (186) | ok | ok 2/42 | **PASS** |
| 2022 | 33_Technical_school-current_m.rvt | 16.3 | 19.1 | 17386 | 850213 | 99% | ok | 50 (167) | ok | ok 2/40 | **PASS** |
| 2022 | 34_rme_basic_sample_project.rvt | 30.5 | 42.2 | 27656 | 2153983 | 97% | ok | 34 (175) | ok | ok 8/93 | **PASS** |
| 2022 | 35_rme_advanced_sample_project.rvt | 36.7 | 37.5 | 29276 | 1993970 | 98% | ok | 34 (175) | ok | ok 8/95 | **PASS** |
| 2022 | 63_Precast_Detailing-DefaultMetricCHS.rte | 16.4 | 6.9 | 9991 | 60 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2022 | 64_Precast_Detailing-DefaultMetricCSY.rte | 16.6 | 7.0 | 9992 | 60 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2022 | 65_Construction-DefaultMetric.rte | 5.0 | 1.9 | 5502 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| 2023 | 36_rst_basic_sample_project.rvt | 6.5 | 6.8 | 13820 | 471266 | 100% | ok | 18 (79) | ok | ok 8/37 | **PASS** |
| 2023 | 37_rst_advanced_sample_project.rvt | 14.4 | 8.3 | 13727 | 298122 | 100% | ok | 10 (194) | ok | ok 9/31 | **PASS** |
| 2023 | 38_Arch_Link_Model.rvt | 15.6 | 17.0 | 17350 | 871697 | 99% | ok | 52 (188) | ok | ok 2/42 | **PASS** |
| 2023 | 39_Technical_school-current_m.rvt | 16.4 | 17.0 | 17477 | 855007 | 99% | ok | 50 (168) | ok | ok 2/40 | **PASS** |
| 2023 | 40_rme_basic_sample_project.rvt | 30.8 | 42.2 | 27750 | 2157461 | 97% | ok | 34 (175) | ok | ok 8/93 | **PASS** |
| 2023 | 41_rme_advanced_sample_project.rvt | 37.1 | 38.7 | 29370 | 1997628 | 98% | ok | 34 (175) | ok | ok 8/95 | **PASS** |
| 2023 | 66_Precast_Detailing-DefaultMetricCHS.rte | 15.7 | 3.2 | 10088 | 60 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2023 | 67_Precast_Detailing-DefaultMetricCSY.rte | 15.9 | 3.1 | 10090 | 60 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2023 | 68_Construction-DefaultMetric.rte | 5.0 | 3.5 | 5591 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| 2024 | 42_Snowdon_Towers_Sample_HVAC.rvt | 22.0 | 10.0 | 12679 | 764638 | 100% | ok | 0 (39) | ok | ok 18/29 | **PASS** |
| 2024 | 43_Snowdon_Towers_Sample_Structural.rvt | 27.9 | 11.3 | 16571 | 667157 | 100% | ok | 6 (79) | ok | ok 12/60 | **PASS** |
| 2024 | 44_Snowdon_Towers_Sample_Electrical.rvt | 40.3 | 17.9 | 19769 | 2236556 | 100% | ok | 18 (48) | ok | ok 26/55 | **PASS** |
| 2024 | 45_Snowdon_Towers_Sample_Plumbing.rvt | 41.6 | 33.2 | 25738 | 3146974 | 100% | ok | 4 (72) | ok | ok 27/68 | **PASS** |
| 2024 | 46_Snowdon_Towers_Sample_Facades.rvt | 52.7 | 9.3 | 9534 | 294465 | 100% | ok | 20 (74) | ok | ok 2/28 | **PASS** |
| 2024 | 47_Snowdon_Towers_Sample_Site.rvt | 54.4 | 12.6 | 11711 | 141638 | 100% | ok | 12 (76) | ok | ok 3/17 | **PASS** |
| 2024 | 69_Precast_Detailing-DefaultMetricCHS.rte | 16.7 | 3.2 | 10101 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2024 | 70_Precast_Detailing-DefaultMetricCSY.rte | 16.9 | 3.2 | 10110 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2024 | 71_Construction-DefaultMetric.rte | 5.3 | 1.9 | 5603 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| 2025 | 48_Snowdon_Towers_Sample_HVAC.rvt | 22.2 | 10.1 | 12716 | 764638 | 100% | ok | 0 (39) | ok | ok 18/29 | **PASS** |
| 2025 | 49_Snowdon_Towers_Sample_Structural.rvt | 27.9 | 13.5 | 16612 | 667157 | 100% | ok | 6 (79) | ok | ok 12/60 | **PASS** |
| 2025 | 50_Snowdon_Towers_Sample_Electrical.rvt | 40.5 | 18.4 | 19810 | 2236556 | 100% | ok | 18 (48) | ok | ok 26/55 | **PASS** |
| 2025 | 51_Snowdon_Towers_Sample_Plumbing.rvt | 41.7 | 31.2 | 25750 | 3145918 | 100% | ok | 4 (72) | ok | ok 27/68 | **PASS** |
| 2025 | 52_Snowdon_Towers_Sample_Facades.rvt | 52.7 | 9.2 | 9571 | 294465 | 100% | ok | 20 (74) | ok | ok 2/28 | **PASS** |
| 2025 | 53_Snowdon_Towers_Sample_Site.rvt | 54.3 | 12.7 | 11750 | 141476 | 100% | ok | 12 (76) | ok | ok 3/17 | **PASS** |
| 2025 | 72_Precast_Detailing-DefaultMetricCHS.rte | 16.8 | 3.1 | 10142 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2025 | 73_Precast_Detailing-DefaultMetricCSY.rte | 17.0 | 3.2 | 10151 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2025 | 74_Construction-DefaultMetric.rte | 5.3 | 1.9 | 5640 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| 2026 | 54_Snowdon_Towers_Sample_HVAC.rvt | 22.2 | 10.1 | 12791 | 764638 | 100% | ok | 0 (39) | ok | ok 18/29 | **PASS** |
| 2026 | 55_Snowdon_Towers_Sample_Structural.rvt | 27.7 | 10.7 | 16678 | 667205 | 100% | ok | 6 (79) | ok | ok 12/60 | **PASS** |
| 2026 | 56_Snowdon_Towers_Sample_Electrical.rvt | 41.6 | 18.5 | 19901 | 2236556 | 100% | ok | 18 (48) | ok | ok 26/55 | **PASS** |
| 2026 | 57_Snowdon_Towers_Sample_Plumbing.rvt | 41.7 | 31.7 | 25837 | 3146022 | 100% | ok | 4 (72) | ok | ok 27/68 | **PASS** |
| 2026 | 58_Snowdon_Towers_Sample_Facades.rvt | 52.6 | 9.4 | 9645 | 294465 | 100% | ok | 20 (74) | ok | ok 2/28 | **PASS** |
| 2026 | 59_Snowdon_Towers_Sample_Site.rvt | 60.7 | 41.0 | 11834 | 144041 | 100% | ok | 12 (76) | ok | ok 3/17 | **PASS** |
| 2026 | 75_Precast_Detailing-DefaultMetricCHS.rte | 16.7 | 2.9 | 10217 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2026 | 76_Precast_Detailing-DefaultMetricCSY.rte | 16.9 | 2.9 | 10226 | 48 | 0% | ok | 0 (160) | ok | ok 0/10 | **PASS** |
| 2026 | 77_Construction-DefaultMetric.rte | 5.2 | 2.1 | 5714 | 36 | 0% | ok | 0 (73) | ok | ok 0/12 | **PASS** |
| rfa-2016 | rac_basic_sample_family-2016.rfa | 0.3 | 0.8 | 1596 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2017 | rac_basic_sample_family-2017.rfa | 0.3 | 0.7 | 1631 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2018 | rac_basic_sample_family-2018.rfa | 0.3 | 0.7 | 1693 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2019 | rac_basic_sample_family-2019.rfa | 0.3 | 0.7 | 1713 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2020 | racbasicsamplefamily-2020.rfa | 0.3 | 0.8 | 1750 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2021 | racbasicsamplefamily-2021.rfa | 0.3 | 0.9 | 1814 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2022 | racbasicsamplefamily-2022.rfa | 0.4 | 0.8 | 1879 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2023 | racbasicsamplefamily-2023.rfa | 0.4 | 0.8 | 1964 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2024 | racbasicsamplefamily-2024.rfa | 0.4 | 0.8 | 1975 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2025 | racbasicsamplefamily-2025.rfa | 0.4 | 0.8 | 1984 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| rfa-2026 | racbasicsamplefamily-2026.rfa | 0.4 | 0.8 | 1992 | 1717 | 100% | ok | 2 (0) | ok | ok 1/7 | **PASS** |
| scenes | 2024_house3.rte | 6.4 | 2.6 | 6094 | 40052 | 100% | ok | 13 (73) | ok | ok 3/16 | **PASS** |
| scenes | 2024_writer_anno1.rte | 5.4 | 1.9 | 5668 | 1410 | 100% | ok | 9 (73) | ok | ok 1/13 | **PASS** |
| scenes | 2024_writer_campus3.rte | 5.5 | 2.3 | 6015 | 12370 | 62% | ok | 9 (73) | ok | ok 0/18 | **PASS** |
| scenes | 2024_writer_campus4.rte | 5.5 | 2.2 | 6039 | 12370 | 62% | ok | 9 (73) | ok | ok 4/18 | **PASS** |
| scenes | 2024_writer_campus5.rte | 5.5 | 2.3 | 6045 | 12430 | 61% | ok | 9 (73) | ok | ok 4/18 | **PASS** |
| scenes | 2024_writer_fitout1_roomsByRevit.rte | 5.5 | 1.9 | 5742 | 2577 | 95% | ok | 9 (73) | ok | ok 3/15 | **PASS** |
| scenes | 2024_writer_frame2.rte | 5.4 | 2.0 | 5726 | 4929 | 61% | ok | 9 (73) | ok | ok 0/12 | **PASS** |
| scenes | 2024_writer_grids1_2024.rte | 5.4 | 1.9 | 5647 | 1357 | 100% | ok | 9 (73) | ok | ok 0/12 | **PASS** |
| scenes | 2024_writer_grids1r.rte | 5.4 | 1.9 | 5647 | 1357 | 100% | ok | 9 (73) | ok | ok 0/12 | **PASS** |
| scenes | 2024_writer_grids1s.rte | 5.4 | 1.9 | 5647 | 1357 | 100% | ok | 9 (73) | ok | ok 0/12 | **PASS** |
| scenes | 2024_writer_house1.rte | 5.4 | 2.5 | 5675 | 7186 | 100% | ok | 9 (73) | ok | ok 0/12 | **PASS** |
| scenes | 2024_writer_house2.rte | 5.4 | 2.6 | 5686 | 7282 | 100% | ok | 9 (73) | ok | ok 0/12 | **PASS** |
| scenes | 2024_writer_house_lv.rte | 5.4 | 2.0 | 5685 | 6498 | 80% | ok | 9 (73) | ok | ok 0/13 | **PASS** |
| scenes | 2024_writer_office5.rte | 5.4 | 2.0 | 5819 | 5342 | 65% | ok | 9 (73) | ok | ok 0/17 | **PASS** |
| scenes | 2024_writer_office6.rte | 5.4 | 2.0 | 5859 | 5342 | 65% | ok | 9 (73) | ok | ok 5/17 | **PASS** |
| scenes | 2024_writer_office7.rte | 5.5 | 2.2 | 5884 | 5642 | 52% | ok | 9 (73) | ok | ok 5/17 | **PASS** |
| scenes | 2024_writer_roofs2.rte | 5.4 | 2.6 | 5720 | 1429 | 100% | ok | 10 (73) | ok | ok 0/12 | **PASS** |
| scenes | 2024_writer_topo1.rte | 5.4 | 1.9 | 5643 | 1409 | 78% | ok | 9 (73) | ok | ok 0/12 | **PASS** |
| scenes | 2024_writer_tower20.rte | 5.6 | 2.7 | 6348 | 12577 | 41% | ok | 9 (73) | ok | ok 0/17 | **PASS** |
| scenes | 2026_writer_campus3.rte | 5.5 | 3.0 | 6128 | 12371 | 22% | ok | 9 (73) | ok | ok 0/18 | **PASS** |
| scenes | 2026_writer_campus4.rte | 5.5 | 2.9 | 6152 | 12371 | 22% | ok | 9 (73) | ok | ok 4/18 | **PASS** |
| scenes | 2026_writer_campus5.rte | 5.5 | 2.9 | 6158 | 12431 | 22% | ok | 9 (73) | ok | ok 4/18 | **PASS** |
| scenes | 2026_writer_fitout1_roomsByRevit.rte | 5.5 | 2.6 | 5855 | 2578 | 64% | ok | 9 (73) | ok | ok 3/15 | **PASS** |
| scenes | 2026_writer_frame2.rte | 5.4 | 2.5 | 5839 | 4930 | 38% | ok | 9 (73) | ok | ok 0/12 | **PASS** |
| scenes | 2026_writer_house_lv.rte | 5.4 | 2.5 | 5798 | 6499 | 71% | ok | 9 (73) | ok | ok 0/13 | **PASS** |
| scenes | 2026_writer_office5.rte | 5.4 | 2.8 | 5932 | 5343 | 26% | ok | 9 (73) | ok | ok 0/17 | **PASS** |
| scenes | 2026_writer_office6.rte | 5.4 | 2.6 | 5972 | 5343 | 26% | ok | 9 (73) | ok | ok 5/17 | **PASS** |
| scenes | 2026_writer_office7.rte | 5.4 | 3.0 | 5997 | 6143 | 21% | ok | 9 (73) | ok | ok 5/17 | **PASS** |
| scenes | 2026_writer_office8.rte | 5.4 | 2.7 | 5987 | 5348 | 26% | ok | 9 (73) | ok | ok 5/17 | **PASS** |
| scenes | 2026_writer_roofs2.rte | 5.3 | 2.7 | 5833 | 1430 | 100% | ok | 10 (73) | ok | ok 0/12 | **PASS** |
| scenes | 2026_writer_spec_example2.rte | 5.5 | 2.6 | 5920 | 12823 | 91% | ok | 10 (73) | ok | ok 1/14 | **PASS** |
| scenes | 2026_writer_tower20.rte | 5.6 | 3.3 | 6461 | 12578 | 10% | ok | 9 (73) | ok | ok 0/17 | **PASS** |

<!-- /RESULTS -->
