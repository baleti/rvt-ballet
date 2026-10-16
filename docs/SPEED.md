# Conversion speed (host1, one worker, current converter + Rust fast path)

First usable = reader + tables + preview (`timings` of tools/sweep.py): the page opens with the element table, levels, grids and a preview mesh; the full meshes stream in until `total`. Cached models open instantly (about 0.3 s).

| year | file | MB | first usable s | total s | elements | triangles |
|---|---|---|---|---|---|---|
| rfa-2016 | rac_basic_sample_family-2016.rfa | 0.3 | 2.0 | 2.6 | 1596 | 1717 |
| rfa-2017 | rac_basic_sample_family-2017.rfa | 0.3 | 1.7 | 2.0 | 1631 | 1717 |
| rfa-2018 | rac_basic_sample_family-2018.rfa | 0.3 | 1.8 | 2.2 | 1693 | 1717 |
| rfa-2019 | rac_basic_sample_family-2019.rfa | 0.3 | 1.7 | 2.1 | 1713 | 1717 |
| rfa-2020 | racbasicsamplefamily-2020.rfa | 0.3 | 1.6 | 2.0 | 1750 | 1717 |
| rfa-2021 | racbasicsamplefamily-2021.rfa | 0.3 | 1.6 | 1.9 | 1814 | 1717 |
| rfa-2022 | racbasicsamplefamily-2022.rfa | 0.4 | 1.6 | 1.9 | 1879 | 1717 |
| rfa-2023 | racbasicsamplefamily-2023.rfa | 0.4 | 1.5 | 1.8 | 1964 | 1717 |
| rfa-2024 | racbasicsamplefamily-2024.rfa | 0.4 | 1.1 | 1.3 | 1975 | 1717 |
| rfa-2025 | racbasicsamplefamily-2025.rfa | 0.4 | 1.1 | 1.4 | 1984 | 1717 |
| rfa-2026 | racbasicsamplefamily-2026.rfa | 0.4 | 1.1 | 1.4 | 1992 | 1717 |
| 2021 | 62_Construction-DefaultMetric.rte | 5.0 | 1.2 | 2.1 | 5426 | 36 |
| 2022 | 65_Construction-DefaultMetric.rte | 5.0 | 1.2 | 2.1 | 5502 | 36 |
| 2023 | 68_Construction-DefaultMetric.rte | 5.0 | 1.3 | 2.2 | 5591 | 36 |
| 2026 | 77_Construction-DefaultMetric.rte | 5.2 | 1.2 | 2.3 | 5714 | 36 |
| 2024 | 71_Construction-DefaultMetric.rte | 5.3 | 1.2 | 2.1 | 5603 | 36 |
| 2025 | 74_Construction-DefaultMetric.rte | 5.3 | 1.2 | 2.1 | 5640 | 36 |
| 2018 | 06_rst_basic_sample_project.rvt | 5.8 | 5.2 | 9.2 | 13997 | 469743 |
| 2019 | 12_rst_basic_sample_project.rvt | 5.9 | 5.1 | 9.2 | 13810 | 469755 |
| 2020 | 18_rst_basic_sample_project.rvt | 5.9 | 5.1 | 9.1 | 13853 | 469743 |
| 2017 | 00_rst_basic_sample_project.rvt | 6.0 | 5.2 | 9.0 | 13934 | 469776 |
| 2021 | 24_rst_basic_sample_project.rvt | 6.2 | 5.2 | 9.1 | 13924 | 469755 |
| 2023 | 36_rst_basic_sample_project.rvt | 6.5 | 5.2 | 9.3 | 13820 | 471254 |
| 2022 | 30_rst_basic_sample_project.rvt | 6.5 | 6.0 | 11.0 | 14035 | 471367 |
| 2020 | 19_Commercial_Sample_Project.rvt | 7.4 | 2.8 | 6.9 | 7042 | 116068 |
| 2020 | 20_Residential_Sample_Project.rvt | 10.2 | 2.4 | 6.2 | 7277 | 103454 |
| 2017 | 01_rst_advanced_sample_project.rvt | 13.1 | 6.8 | 12.3 | 13486 | 292358 |
| 2018 | 07_rst_advanced_sample_project.rvt | 13.3 | 4.8 | 9.6 | 13551 | 292454 |
| 2019 | 13_rst_advanced_sample_project.rvt | 13.5 | 5.0 | 10.1 | 13543 | 292374 |
| 2020 | 21_rst_advanced_sample_project.rvt | 13.6 | 4.9 | 9.6 | 13586 | 292454 |
| 2017 | 02_Arch_Link_Model.rvt | 14.2 | 9.5 | 23.1 | 16906 | 866808 |
| 2018 | 08_Arch_Link_Model.rvt | 14.3 | 9.1 | 23.9 | 16972 | 866808 |
| 2021 | 25_rst_advanced_sample_project.rvt | 14.4 | 4.9 | 9.8 | 13659 | 292370 |
| 2023 | 37_rst_advanced_sample_project.rvt | 14.4 | 4.8 | 9.9 | 13727 | 298086 |
| 2022 | 31_rst_advanced_sample_project.rvt | 14.4 | 6.6 | 44.3 | 13733 | 292370 |
| 2019 | 14_Arch_Link_Model.rvt | 14.5 | 8.1 | 20.8 | 16971 | 866808 |
| 2021 | 26_Arch_Link_Model.rvt | 15.1 | 7.9 | 19.8 | 17084 | 866820 |
| 2022 | 32_Arch_Link_Model.rvt | 15.1 | 7.9 | 20.3 | 17157 | 866820 |
| 2017 | 03_rac_advanced_sample_project.rvt | 15.3 | 8.1 | 22.7 | 17132 | 850081 |
| 2018 | 09_rac_advanced_sample_project.rvt | 15.5 | 8.6 | 26.8 | 17198 | 850081 |
| 2023 | 38_Arch_Link_Model.rvt | 15.6 | 9.2 | 22.9 | 17350 | 871685 |
| 2019 | 15_rac_advanced_sample_project.rvt | 15.6 | 8.2 | 20.9 | 17197 | 850093 |
| 2023 | 66_Precast_Detailing-DefaultMetricCHS.rte | 15.7 | 1.6 | 3.2 | 10088 | 48 |
| 2023 | 67_Precast_Detailing-DefaultMetricCSY.rte | 15.9 | 1.6 | 3.2 | 10090 | 48 |
| 2021 | 27_Technical_school-current_m.rvt | 16.3 | 8.1 | 20.7 | 17313 | 850117 |
| 2021 | 60_Precast_Detailing-DefaultMetricCHS.rte | 16.3 | 1.7 | 3.1 | 9918 | 48 |
| 2022 | 33_Technical_school-current_m.rvt | 16.3 | 8.1 | 20.2 | 17386 | 850117 |
| 2022 | 63_Precast_Detailing-DefaultMetricCHS.rte | 16.4 | 1.9 | 3.1 | 9991 | 48 |
| 2023 | 39_Technical_school-current_m.rvt | 16.4 | 8.4 | 20.6 | 17477 | 854923 |
| 2021 | 61_Precast_Detailing-DefaultMetricCSY.rte | 16.5 | 1.6 | 3.1 | 9919 | 48 |
| 2022 | 64_Precast_Detailing-DefaultMetricCSY.rte | 16.6 | 2.0 | 3.3 | 9992 | 48 |
| 2026 | 75_Precast_Detailing-DefaultMetricCHS.rte | 16.7 | 1.7 | 3.4 | 10217 | 48 |
| 2024 | 69_Precast_Detailing-DefaultMetricCHS.rte | 16.7 | 1.7 | 3.5 | 10101 | 48 |
| 2025 | 72_Precast_Detailing-DefaultMetricCHS.rte | 16.8 | 1.8 | 3.5 | 10142 | 48 |
| 2026 | 76_Precast_Detailing-DefaultMetricCSY.rte | 16.9 | 1.8 | 3.6 | 10226 | 48 |
| 2024 | 70_Precast_Detailing-DefaultMetricCSY.rte | 16.9 | 1.7 | 3.4 | 10110 | 48 |
| 2025 | 73_Precast_Detailing-DefaultMetricCSY.rte | 17.0 | 1.8 | 3.4 | 10151 | 48 |
| 2024 | 42_Snowdon_Towers_Sample_HVAC.rvt | 22.0 | 5.7 | 16.8 | 12679 | 764638 |
| 2026 | 54_Snowdon_Towers_Sample_HVAC.rvt | 22.2 | 5.4 | 15.7 | 12791 | 764638 |
| 2025 | 48_Snowdon_Towers_Sample_HVAC.rvt | 22.2 | 8.9 | 21.8 | 12716 | 764638 |
| 2026 | 55_Snowdon_Towers_Sample_Structural.rvt | 27.7 | 4.6 | 16.7 | 16678 | 667205 |
| 2024 | 43_Snowdon_Towers_Sample_Structural.rvt | 27.9 | 5.0 | 14.5 | 16571 | 667157 |
| 2025 | 49_Snowdon_Towers_Sample_Structural.rvt | 27.9 | 5.0 | 13.5 | 16612 | 667157 |
| 2017 | 04_rme_basic_sample_project.rvt | 27.9 | 21.7 | 67.0 | 27393 | 2153859 |
| 2018 | 10_rme_basic_sample_project.rvt | 28.4 | 12.8 | 57.2 | 27459 | 2153657 |
| 2019 | 16_rme_basic_sample_project.rvt | 28.5 | 16.8 | 24.3 | 27471 | 2153911 |
| 2020 | 22_rme_basic_sample_project.rvt | 29.1 | 17.5 | 63.4 | 27511 | 2153693 |
| 2021 | 28_rme_basic_sample_project.rvt | 30.4 | 24.1 | 68.5 | 27583 | 2153935 |
| 2022 | 34_rme_basic_sample_project.rvt | 30.5 | 11.3 | 56.1 | 27656 | 2153935 |
| 2023 | 40_rme_basic_sample_project.rvt | 30.8 | 12.0 | 58.0 | 27750 | 2157401 |
| 2017 | 05_rme_advanced_sample_project.rvt | 33.1 | 51.2 | 85.8 | 29016 | 1993846 |
| 2018 | 11_rme_advanced_sample_project.rvt | 33.7 | 13.0 | 47.4 | 29081 | 1993860 |
| 2019 | 17_rme_advanced_sample_project.rvt | 34.0 | 17.5 | 53.9 | 29101 | 1993910 |
| 2020 | 23_rme_advanced_sample_project.rvt | 34.8 | 17.6 | 52.4 | 29132 | 1993882 |
| 2021 | 29_rme_advanced_sample_project.rvt | 36.5 | 26.5 | 60.5 | 29204 | 1993922 |
| 2022 | 35_rme_advanced_sample_project.rvt | 36.7 | 14.1 | 49.1 | 29276 | 1993922 |
| 2023 | 41_rme_advanced_sample_project.rvt | 37.1 | 14.6 | 49.6 | 29370 | 1997568 |
| 2024 | 44_Snowdon_Towers_Sample_Electrical.rvt | 40.3 | 6.6 | 23.8 | 19769 | 2236556 |
| 2025 | 50_Snowdon_Towers_Sample_Electrical.rvt | 40.5 | 6.7 | 23.6 | 19810 | 2236556 |
| 2026 | 56_Snowdon_Towers_Sample_Electrical.rvt | 41.6 | 7.2 | 24.0 | 19901 | 2236556 |
| 2024 | 45_Snowdon_Towers_Sample_Plumbing.rvt | 41.6 | 12.9 | 46.3 | 25738 | 3146974 |
| 2026 | 57_Snowdon_Towers_Sample_Plumbing.rvt | 41.7 | 13.5 | 46.8 | 25837 | 3146022 |
| 2025 | 51_Snowdon_Towers_Sample_Plumbing.rvt | 41.7 | 13.1 | 46.5 | 25750 | 3145918 |
| 2026 | 58_Snowdon_Towers_Sample_Facades.rvt | 52.6 | 2.3 | 8.3 | 9645 | 294465 |
| 2024 | 46_Snowdon_Towers_Sample_Facades.rvt | 52.7 | 3.1 | 9.2 | 9534 | 294465 |
| 2025 | 52_Snowdon_Towers_Sample_Facades.rvt | 52.7 | 3.0 | 8.8 | 9571 | 294465 |
| 2025 | 53_Snowdon_Towers_Sample_Site.rvt | 54.3 | 4.2 | 13.2 | 11750 | 141476 |
| 2024 | 47_Snowdon_Towers_Sample_Site.rvt | 54.4 | 4.2 | 12.9 | 11711 | 141638 |
| 2026 | 59_Snowdon_Towers_Sample_Site.rvt | 60.7 | 4.3 | 48.7 | 11834 | 144041 |

## Files of 25 MB and more

Timings come from a shared host1 slice and can be inflated by neighbouring jobs (2026 Site: 48.7 s in the sweep, 12.5 s alone). Median first usable 12.8 s, median total 46.8 s (n=29). Slowest first usable: 05_rme_advanced_sample_project 51 s, 29_rme_advanced_sample_project 27 s, 28_rme_basic_sample_project.rv 24 s.
