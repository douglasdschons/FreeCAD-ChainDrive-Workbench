# Dependency audit

## Standard library

`csv`, `dataclasses`, `datetime`, `math`, `pathlib`, `re`, `sys`, and `typing`.

## FreeCAD runtime

`FreeCAD`, `FreeCADGui`, and `Part`. GUI modules additionally use the PySide
binding bundled with FreeCAD. These imports are lazy or confined to CAD/GUI
modules, except `config.py`, which intentionally reads FreeCAD preferences.

## Local modules

`application`, `config`, and packages `core`, `cad`, and `gui`.

## External Python packages

No external package is required at runtime. `pytest` is a development/CI-only
dependency. Optional plotting in `core.discrete_solver.plot_result` imports
Matplotlib only when that function is invoked and is not part of workbench use.

