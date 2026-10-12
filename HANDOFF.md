# HANDOFF (rvt-viewer, session 187, 2026-10-12 ~14:25) - state when told to stop for the interview

Last good commit: see `git log -1`. Working tree clean; demo works: `bin/rvt-view FILE [--sheets]` (verified on 2020 Residential, 2024 Structural, 2026 .rte by tools/uitest10.py), `bin/rvt-view --prepare FILE...` (verified on the 2026 template: converts, calls `rvt-sheets warm` if present, prints READY).

## Remaining work (nothing is half-done in the tree)
1. remote-host jobs not started (remote-host was busy): `~/.local/share/offload/h1run run viewerall --env occ --dir ~/src/rvt-viewer -- bash tools/h1_all.sh` converts the 4 memory-light reference models with the final code (coverage -> ~/.cache/rvt-viewer/h1-coverage.json) then runs the per-class acceptance sweep (tools/accept_h1.sh; pull `.cache/rvt-viewer/accept`, then `python3 tools/accept_table.py` -> docs/ACCEPTANCE-STATUS.md, which is still the STALE one). The fidelity table in README predates: topology-check band change, void instances, flex ducts only for some models; regenerate (HVAC/MEP/Facades 'approx' counts will drop after the 0.6-1.5 area band).
2. rvt-sheets: `warm` command and `/sheets/api/{mid}/cache.json` are requested in ~/src/rvt-sheets/HOOKS.md; the viewer already consumes both (--prepare, cached badge).
3. Rust: rvt_fast.Doc + fork deadlock (NEEDS-FROM-READER 12), Facades em_geometries slow (13), curved-mesh topology (10), materials per face (11). Viewer uses the Python Doc with its own fork pool by default (RVT_FASTDOC=1 opt-in), the Rust model for quick table / load / streamed meshes.
4. Materials: per-face materials, real texture bitmaps, swatch thumbnails, asset scale/rotation are not applied (procedural fallback patterns only; labelled).
5. 2026-10-12 reader table fix: Revit Volume follows FINE detail for loadable families; the viewer's accept_eval still compares at Medium (family-instance 'true-off' numbers are partly an artefact), update when 176's fidfull6 table lands.
6. Heavy runs: one at a time, remote-host via h1run for anything > a few minutes; UI tests only on remote-host (tools/cdp.py now caps chromium: 300% CPU, 3 GB, nice 19).
