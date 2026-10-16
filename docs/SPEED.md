# Conversion speed (host1, one worker, current converter + Rust fast path)

First usable = reader + tables + preview (`timings` of tools/sweep.py): the page opens with the element table, levels, grids and a preview mesh; the full meshes stream in until `total`. Cached models open instantly (about 0.3 s).

| year | file | MB | first usable s | total s | elements | triangles |
|---|---|---|---|---|---|---|
| rfa-2016 | rac_basic_sample_family-2016.rfa | 0.3 | 1.0 | 1.4 | 1596 | 1717 |
| rfa-2017 | rac_basic_sample_family-2017.rfa | 0.3 | 1.1 | 1.4 | 1631 | 1717 |
| rfa-2018 | rac_basic_sample_family-2018.rfa | 0.3 | 1.2 | 1.5 | 1693 | 1717 |
| rfa-2019 | rac_basic_sample_family-2019.rfa | 0.3 | 1.1 | 1.3 | 1713 | 1717 |
| rfa-2020 | racbasicsamplefamily-2020.rfa | 0.3 | 1.1 | 1.4 | 1750 | 1717 |
| rfa-2021 | racbasicsamplefamily-2021.rfa | 0.3 | 1.1 | 1.4 | 1814 | 1717 |
| rfa-2022 | racbasicsamplefamily-2022.rfa | 0.4 | 1.3 | 1.5 | 1879 | 1717 |
| rfa-2023 | racbasicsamplefamily-2023.rfa | 0.4 | 1.2 | 1.4 | 1964 | 1717 |
| rfa-2024 | racbasicsamplefamily-2024.rfa | 0.4 | 1.2 | 1.5 | 1975 | 1717 |
| rfa-2025 | racbasicsamplefamily-2025.rfa | 0.4 | 1.3 | 1.5 | 1984 | 1717 |
| rfa-2026 | racbasicsamplefamily-2026.rfa | 0.4 | 1.2 | 1.5 | 1992 | 1717 |
| 2021 | 62_Construction-DefaultMetric.rte | 5.0 | 1.2 | 2.1 | 5426 | 36 |
| 2022 | 65_Construction-DefaultMetric.rte | 5.0 | 1.3 | 2.2 | 5502 | 36 |
| 2023 | 68_Construction-DefaultMetric.rte | 5.0 | 1.2 | 2.2 | 5591 | 36 |
| 2026 | 77_Construction-DefaultMetric.rte | 5.2 | 1.5 | 2.4 | 5714 | 36 |
| 2024 | 71_Construction-DefaultMetric.rte | 5.3 | 1.3 | 2.2 | 5603 | 36 |
| 2025 | 74_Construction-DefaultMetric.rte | 5.3 | 1.5 | 2.4 | 5640 | 36 |
| 2018 | 06_rst_basic_sample_project.rvt | 5.8 | 6.4 | 11.8 | 13997 | 469743 |
| 2019 | 12_rst_basic_sample_project.rvt | 5.9 | 6.3 | 9.7 | 13810 | 469755 |
| 2020 | 18_rst_basic_sample_project.rvt | 5.9 | 5.9 | 9.3 | 13853 | 469743 |
| 2017 | 00_rst_basic_sample_project.rvt | 6.0 | 6.4 | 10.0 | 13934 | 469776 |
| 2021 | 24_rst_basic_sample_project.rvt | 6.2 | 6.0 | 9.6 | 13924 | 469755 |
| 2023 | 36_rst_basic_sample_project.rvt | 6.5 | 6.3 | 9.9 | 13820 | 471254 |
| 2022 | 30_rst_basic_sample_project.rvt | 6.5 | 6.5 | 10.0 | 14035 | 471367 |
| 2020 | 19_Commercial_Sample_Project.rvt | 7.4 | 2.4 | 5.7 | 7042 | 116068 |
| 2020 | 20_Residential_Sample_Project.rvt | 10.2 | 1.8 | 4.3 | 7277 | 103454 |
| 2017 | 01_rst_advanced_sample_project.rvt | 13.1 | 6.4 | 13.5 | 13486 | 292358 |
| 2018 | 07_rst_advanced_sample_project.rvt | 13.3 | 6.1 | 11.5 | 13551 | 292454 |
| 2019 | 13_rst_advanced_sample_project.rvt | 13.5 | 6.4 | 11.2 | 13543 | 292374 |
| 2020 | 21_rst_advanced_sample_project.rvt | 13.6 | 5.0 | 9.8 | 13586 | 292454 |
| 2017 | 02_Arch_Link_Model.rvt | 14.2 | 15.3 | 27.5 | 16906 | 866808 |
| 2018 | 08_Arch_Link_Model.rvt | 14.3 | 9.0 | 22.2 | 16972 | 866808 |
| 2021 | 25_rst_advanced_sample_project.rvt | 14.4 | 4.9 | 10.0 | 13659 | 292370 |
| 2023 | 37_rst_advanced_sample_project.rvt | 14.4 | 4.8 | 9.8 | 13727 | 298086 |
| 2022 | 31_rst_advanced_sample_project.rvt | 14.4 | 6.5 | 73.3 | 13733 | 292370 |
| 2019 | 14_Arch_Link_Model.rvt | 14.5 | 8.3 | 20.3 | 16971 | 866808 |
| 2021 | 26_Arch_Link_Model.rvt | 15.1 | 8.0 | 19.9 | 17084 | 866820 |
| 2022 | 32_Arch_Link_Model.rvt | 15.1 | 8.0 | 20.0 | 17157 | 866820 |
| 2017 | 03_rac_advanced_sample_project.rvt | 15.3 | 10.2 | 22.4 | 17132 | 850081 |
| 2018 | 09_rac_advanced_sample_project.rvt | 15.5 | 11.8 | 24.4 | 17198 | 850081 |
| 2023 | 38_Arch_Link_Model.rvt | 15.6 | 8.6 | 20.7 | 17350 | 871685 |
| 2019 | 15_rac_advanced_sample_project.rvt | 15.6 | 8.2 | 21.0 | 17197 | 850093 |
| 2023 | 66_Precast_Detailing-DefaultMetricCHS.rte | 15.7 | 1.6 | 3.1 | 10088 | 48 |
| 2023 | 67_Precast_Detailing-DefaultMetricCSY.rte | 15.9 | 1.7 | 3.1 | 10090 | 48 |
| 2021 | 27_Technical_school-current_m.rvt | 16.3 | 8.1 | 22.2 | 17313 | 850117 |
| 2021 | 60_Precast_Detailing-DefaultMetricCHS.rte | 16.3 | 1.8 | 3.3 | 9918 | 48 |
| 2022 | 33_Technical_school-current_m.rvt | 16.3 | 8.2 | 22.4 | 17386 | 850117 |
| 2022 | 63_Precast_Detailing-DefaultMetricCHS.rte | 16.4 | 1.9 | 3.1 | 9991 | 48 |
| 2023 | 39_Technical_school-current_m.rvt | 16.4 | 8.7 | 22.5 | 17477 | 854923 |
| 2021 | 61_Precast_Detailing-DefaultMetricCSY.rte | 16.5 | 1.6 | 3.1 | 9919 | 48 |
| 2022 | 64_Precast_Detailing-DefaultMetricCSY.rte | 16.6 | 1.9 | 3.1 | 9992 | 48 |
| 2026 | 75_Precast_Detailing-DefaultMetricCHS.rte | 16.7 | 1.6 | 3.1 | 10217 | 48 |
| 2024 | 69_Precast_Detailing-DefaultMetricCHS.rte | 16.7 | 1.7 | 3.3 | 10101 | 48 |
| 2025 | 72_Precast_Detailing-DefaultMetricCHS.rte | 16.8 | 1.6 | 3.1 | 10142 | 48 |
| 2026 | 76_Precast_Detailing-DefaultMetricCSY.rte | 16.9 | 1.6 | 3.1 | 10226 | 48 |
| 2024 | 70_Precast_Detailing-DefaultMetricCSY.rte | 16.9 | 1.7 | 3.2 | 10110 | 48 |
| 2025 | 73_Precast_Detailing-DefaultMetricCSY.rte | 17.0 | 1.7 | 3.2 | 10151 | 48 |
| 2024 | 42_Snowdon_Towers_Sample_HVAC.rvt | 22.0 | 5.7 | 14.9 | 12679 | 764638 |
| 2026 | 54_Snowdon_Towers_Sample_HVAC.rvt | 22.2 | 5.4 | 15.9 | 12791 | 764638 |
| 2025 | 48_Snowdon_Towers_Sample_HVAC.rvt | 22.2 | 5.3 | 15.6 | 12716 | 764638 |
| 2026 | 55_Snowdon_Towers_Sample_Structural.rvt | 27.7 | 4.5 | 11.8 | 16678 | 667205 |
| 2017 | 04_rme_basic_sample_project.rvt | 27.9 | 20.8 | 67.3 | 27393 | 2153859 |
| 2024 | 43_Snowdon_Towers_Sample_Structural.rvt | 27.9 | 4.5 | 11.9 | 16571 | 667157 |
| 2025 | 49_Snowdon_Towers_Sample_Structural.rvt | 27.9 | 4.8 | 12.1 | 16612 | 667157 |
| 2018 | 10_rme_basic_sample_project.rvt | 28.4 | 12.9 | 59.2 | 27459 | 2153657 |
| 2019 | 16_rme_basic_sample_project.rvt | 28.5 | 11.6 | 57.8 | 27471 | 2153911 |
| 2020 | 22_rme_basic_sample_project.rvt | 29.1 | 11.5 | 57.9 | 27511 | 2153693 |
| 2021 | 28_rme_basic_sample_project.rvt | 30.4 | 11.7 | 58.0 | 27583 | 2153935 |
| 2022 | 34_rme_basic_sample_project.rvt | 30.5 | 11.5 | 58.3 | 27656 | 2153935 |
| 2023 | 40_rme_basic_sample_project.rvt | 30.8 | 12.1 | 59.3 | 27750 | 2157401 |
| 2017 | 05_rme_advanced_sample_project.rvt | 33.1 | 11.4 | 44.7 | 29016 | 1993846 |
| 2018 | 11_rme_advanced_sample_project.rvt | 33.7 | 13.1 | 49.1 | 29081 | 1993860 |
| 2019 | 17_rme_advanced_sample_project.rvt | 34.0 | 11.6 | 46.4 | 29101 | 1993910 |
| 2020 | 23_rme_advanced_sample_project.rvt | 34.8 | 11.4 | 45.9 | 29132 | 1993882 |
| 2021 | 29_rme_advanced_sample_project.rvt | 36.5 | 18.5 | 79.3 | 29204 | 1993922 |
| 2022 | 35_rme_advanced_sample_project.rvt | 36.7 | 17.2 | 90.2 | 29276 | 1993922 |
| 2023 | 41_rme_advanced_sample_project.rvt | 37.1 | 19.4 | 72.9 | 29370 | 1997568 |
| 2024 | 44_Snowdon_Towers_Sample_Electrical.rvt | 40.3 | 5.7 | 22.7 | 19769 | 2236556 |
| 2025 | 50_Snowdon_Towers_Sample_Electrical.rvt | 40.5 | 5.8 | 22.6 | 19810 | 2236556 |
| 2026 | 56_Snowdon_Towers_Sample_Electrical.rvt | 41.6 | 5.8 | 22.9 | 19901 | 2236556 |
| 2024 | 45_Snowdon_Towers_Sample_Plumbing.rvt | 41.6 | 12.0 | 45.4 | 25738 | 3146974 |
| 2026 | 57_Snowdon_Towers_Sample_Plumbing.rvt | 41.7 | 11.8 | 45.2 | 25837 | 3146022 |
| 2025 | 51_Snowdon_Towers_Sample_Plumbing.rvt | 41.7 | 11.8 | 44.9 | 25750 | 3145918 |
| 2026 | 58_Snowdon_Towers_Sample_Facades.rvt | 52.6 | 2.3 | 8.0 | 9645 | 294465 |
| 2024 | 46_Snowdon_Towers_Sample_Facades.rvt | 52.7 | 2.4 | 8.1 | 9534 | 294465 |
| 2025 | 52_Snowdon_Towers_Sample_Facades.rvt | 52.7 | 2.3 | 8.0 | 9571 | 294465 |
| 2025 | 53_Snowdon_Towers_Sample_Site.rvt | 54.3 | 3.2 | 7.0 | 11750 | 141476 |
| 2024 | 47_Snowdon_Towers_Sample_Site.rvt | 54.4 | 3.4 | 7.1 | 11711 | 141638 |
| 2026 | 59_Snowdon_Towers_Sample_Site.rvt | 60.7 | 3.4 | 6.8 | 11834 | 144041 |

## Files of 25 MB and more

Timings come from a shared host1 slice and can be inflated by neighbouring jobs (2026 Site went 48.7 s -> 7.4 s with the Rust face-edge index; 2017 rme_advanced reader 47 s -> 19 s cold, 7 s with a warm extraction cache). Median first usable 11.5 s, median total 45.2 s (n=29). Slowest first usable: 04_rme_basic_sample_project.rv 21 s, 41_rme_advanced_sample_project 19 s, 29_rme_advanced_sample_project 18 s.
