<p align="center"><img src="assets/logo.png" alt="rvt-viewer logo" width="140"></p>

<h1 align="center">rvt-viewer</h1>
<p align="center">Open a native Revit file in your browser. No Revit, no Autodesk SDK, fully offline.</p>

<p align="center"><a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-0f766e"></a> <img alt="Status: experimental" src="https://img.shields.io/badge/status-experimental-1e293b"></p>

## Features

- Orbit, pan and zoom a 3D model; pick elements and inspect their stored parameters.
- Model tree by category and level, search, per-category visibility, section box and measure tools.
- Hidden-line, shaded, consistent-colour and realistic visual styles; materials and textures from the file.
- Plan, section and elevation views with annotations (tags, text, dimensions, grids, levels).
- Embeds [rvt-sheets](https://github.com/baleti/rvt-sheets) to browse sheets and open viewports.

Python backend ([rvt-reader](https://github.com/baleti/rvt-reader), optionally [rvt-core](https://github.com/baleti/rvt-core)) with a Three.js front end.

## Quick start

```bash
git clone https://github.com/baleti/rvt-reader
export RVT_READER_DIR=$PWD/rvt-reader
python -m venv --system-site-packages .venv
.venv/bin/pip install cadquery-ocp mapbox-earcut aiohttp numpy scipy olefile
.venv/bin/python -m rvtviewer.cli open model.rvt
```

The first conversion of a large model can take minutes; results are cached and re-opening takes seconds. Other commands: `convert FILE OUTDIR` (write `model.glb` and metadata only) and `serve [DIR...]` (serve already converted models).

## Documentation

[`docs/`](docs) holds fidelity tables, the control and plug-in APIs and performance measurements. [`PROVENANCE.md`](PROVENANCE.md) describes where built-in tables come from, and [`DEMO.md`](DEMO.md) is a walkthrough. The vendored Three.js is MIT-licensed (see its header).

## Coverage

- **Corpus sweep:** 89 of 89 Autodesk sample files (Revit 2017-2026, 5-34 MB each) convert and load; the tabulated files pass the functional checks (see [`docs/SWEEP.md`](docs/SWEEP.md)).
- **Geometry fidelity** (reader accuracy per class, [`docs/FIDELITY-FINAL.md`](docs/FIDELITY-FINAL.md)): family instances 99.5% (14,435 elements), walls 99.3%, rooms 99.4%, floors and ceilings 100%, duct/pipe/conduit curves 100%, toposolids 97.6%.
- **Speed:** time to a usable picture is about 2 s on a cached 10 MB model, and typically 10-70 s for a first conversion of a sample project.

## Pending

- Compare-with-Revit deviation mode and some regression screenshots are not complete.
- Toposolid TIN accuracy (97.6%), Text3D elements and masses are the weakest classes.
- Hidden-line mode is the most polished style; shaded and realistic modes are less tuned.
- The `bin/rvt-view` launcher from the original working tree is not included; use `python -m rvtviewer.cli`.

## The rvt toolkit

| Repo | Role |
|---|---|
| [rvt-reader](https://github.com/baleti/rvt-reader) | Pure-Python reader: file container, schema, elements, parameters, geometry |
| [rvt-core](https://github.com/baleti/rvt-core) | Optional Rust acceleration for the reader (PyO3) |
| [rvt-viewer](https://github.com/baleti/rvt-viewer) | Browser 3D viewer built on the reader |
| [rvt-sheets](https://github.com/baleti/rvt-sheets) | Sheet and view renderer (2D drawings) built on the reader |
| [rvt-qa](https://github.com/baleti/rvt-qa) | Visual-diff QA tooling for rvt-sheets output |
| [rvt-writer](https://github.com/baleti/rvt-writer) | Experimental generator of `.rvt` / `.rte` scenes |

## Status and scope

Research-grade software developed by reverse-engineering the file format through black-box analysis of sample files and comparison with the output of the official Revit API. It is accurate on the files it has been tested against but makes no guarantees for arbitrary files. Test models (Autodesk sample files) and Revit-derived ground-truth data are **not** included in this repository.

## License

MIT, see [LICENSE](LICENSE). Autodesk and Revit are trademarks of Autodesk, Inc. This project is independent and is not affiliated with, endorsed by or sponsored by Autodesk.
