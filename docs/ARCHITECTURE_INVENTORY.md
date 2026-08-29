# Source architecture inventory

Source inspected: `ASAChainDriveApp` (preserved unchanged).

## Production

- `core/discrete_solver.py`: validated exact-pitch rigid-link solver.
- `core/catalog.py`, `core/sprocket_catalog.py`: chain and ENCO catalog parsing.
- `cad/templates.py`: InnerLink and OuterLink templates.
- `cad/offset_link_generator.py`: validated OffsetLink; migrated unchanged.
- `cad/asme_sprocket_generator.py`: production ASME/ENCO sprocket geometry.
- `cad/sprocket_library.py`, `cad/chain_generator.py`: caching and App::Link assembly.
- `gui/unified_dialog.py`: unified user interface.
- chain and sprocket CSV catalogs; workbench SVG resources.

## Test/validation source

- `tests/run_offset_link_validation.py` and
  `tests/create_offset_link_validation_documents.py` were used as regression
  references. Their generated FCStd outputs were not migrated.

## Example or legacy

- `asa_chain_drive_app.py`, `ASAChainDrive.FCMacro`: development launchers.
- `gui/dialog.py`, `gui/asme_sprocket_dialog.py`, `gui/sprocket_dialog.py`:
  superseded by the unified dialog.
- `cad/sprocket_generator.py`: superseded sprocket construction.
- `cad/asme_sprocket_preview.py`: interactive development preview.

## Excluded artifacts

- `.codex-backups`, `__pycache__`, `output`, `.FCStd`, `.FCBak`, XLSX source
  copies, and figure-generation files.

## Target layering

`gui -> application -> core/cad`, with FreeCAD imports kept out of pure
mathematical and catalog modules. Installed resources are resolved relative to
the module directory; generated libraries and models use FreeCAD user data.

