# FreeCAD Chain Drive Workbench

A FreeCAD workbench for catalog-backed ASA/ANSI roller-chain sprockets,
exact-pitch rigid-link chains, and complete two-sprocket drives.

> Status: incomplete v0.1.0 development snapshot, shared for study and reuse.
> Existing mathematical code, CAD/FreeCAD generators, and CSV catalogs are
> preserved as-is. Previous validation covers selected cases only; documentation
> and figures remain unfinished. No completed release or ongoing maintenance
> is promised.

## Features

- Three commands: **Generate Chain**, **Generate Sprocket**, and
  **Generate Chain Drive**.
- Discrete rigid-link solver with exact pitch and center-distance correction.
- InnerLink, OuterLink, and preserved functional OffsetLink templates.
- ASME B29.1 tooth-space construction with ENCO commercial body dimensions.
- Lightweight chain assemblies using `App::Link` instances.
- Portable catalogs and per-user generated model/library locations.

Catalog data exists for ASA 35, 40, 50, 60, 80, 100, 120, 140, and 160
single-strand sprockets. Tested support is intentionally limited to the sizes
listed in the validation report.

## Installation

For local testing, copy or link this directory as `ChainDrive` beneath the
FreeCAD user `Mod` directory, restart FreeCAD, and select **Chain Drive** from
the workbench selector. The eventual Addon Manager package is not published.

## Quick start

1. Select the **Chain Drive** workbench.
2. Choose one of the three toolbar commands.
3. Select an ASA series and catalog tooth counts.
4. For chain workflows, enter the desired center distance and choose whether
   an even link count is mandatory.
5. Calculate dimensions, inspect the engineering summary, then generate CAD.

Run the equivalent application API inside FreeCAD, with this repository on
the Python module path:

```python
from application import generate_chain, generate_sprocket, generate_chain_drive

generate_chain(80, 11, 20, 400.0)
generate_sprocket(80, 20)
generate_chain_drive(80, 11, 20, 400.0)
```

## Reuse the mathematics and catalogs

The solver in `core/discrete_solver.py` runs in ordinary Python 3.10+ without
FreeCAD. From the repository directory:

```python
from core.discrete_solver import calculate_discrete_chain_drive_geometry

result = calculate_discrete_chain_drive_geometry(25.4, 11, 20, 400.0)
print(result["link_count"], result["corrected_center_distance_mm"])
```

The existing CSV catalogs in `data/` are included for study and reuse.
CAD generation requires FreeCAD and its bundled Python environment.
See `LICENSE` for the existing LGPL-2.1-or-later terms and
`docs/technical_reference/source_traceability.md` for source notes and
unfinished provenance details. Referenced external PDFs and earlier CAD
models are not included.

## Architecture

- `gui/`: FreeCAD dialogs only.
- `application.py`: high-level workflows.
- `core/`: catalog readers and pure-Python discrete solver.
- `cad/`: link templates, sprocket construction, library, and assembly.
- `data/`: installed chain and sprocket catalogs.
- `tests/`: pure-Python regression and FreeCAD headless smoke tests.
- `docs/technical_reference/`: mathematical and CAD reference source.

Solver coordinates `(x, y)` map to FreeCAD `(X, Z)`. Positive solver
rotation is applied about FreeCAD `-Y`; template interfaces are
`JointA=(0,0,0)` and `JointB=(P,0,0)`.

## Validation

The canonical ASA80 case (`P=25.40 mm`, `z1=11`, `z2=20`, desired center
`400 mm`) produces 47 links, requires an OffsetLink, and corrects the center
distance to approximately `398.338658801 mm`. Pure solver, catalog, and
FreeCAD smoke-test details are recorded in `docs/VALIDATION_REPORT.md`.

## Technical reference

`docs/technical_reference/main.tex` describes the discrete model, coordinate
mapping, CAD generation, validation, and limitations. Figures are deliberately
deferred and marked as placeholders. This source is an unfinished draft.

## Limitations

- Single-strand catalog workflow only.
- No dynamic simulation, tension sizing, wear/lubrication calculation, or
  manufacturing certification.
- Generated sprockets require engineering review before fabrication.
- FreeCAD integration CI is currently documented but disabled until a pinned
  FreeCAD runner is selected.
- Final icons and figures are placeholders/deferred.

## License and author

Copyright Douglas D. Schons. Licensed under LGPL-2.1-or-later; see `LICENSE`.
