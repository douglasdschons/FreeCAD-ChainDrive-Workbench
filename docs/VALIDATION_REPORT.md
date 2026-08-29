# Validation report

Environment: Windows, FreeCAD 1.1.2, CPython 3.12 for pure tests, FreeCAD's
Python 3.11 for CAD tests. Measurements are approximate workstation timings.

## Automated regression

- Pure Python: **6 passed**.
- Canonical ASA80 11/20/400: `N=47`, OffsetLink `True`, corrected center
  `398.33865880057 mm`, correction `-1.661341199430 mm`, closure residual
  `2.11e-10 mm`, maximum pitch error `2.10e-10 mm`.
- FreeCAD headless: InnerLink, OuterLink, OffsetLink, sprocket, 47-link chain,
  and full drive generated without exception; all inspected shapes valid and
  non-null.
- GUI validation: the user tested **Generate Sprocket**, **Generate Chain**, and
  **Generate Chain Drive** in FreeCAD 1.1.2 after the startup, standalone
  visibility, and chain-only reporting fixes. All three workflows passed.

## Multi-size solver matrix

Every row passed with exact-pitch/closure errors below `5e-10 mm`.

| ASA | z1 | z2 | desired mm | N | offset | residual mm | max pitch error mm |
|---:|---:|---:|---:|---:|:---:|---:|---:|
| 35 | 9 | 24 | 190.60 | 57 | yes | 1.11e-10 | 1.10e-10 |
| 35 | 9 | 95 | 576.36 | 176 | no | 3.67e-10 | 3.68e-10 |
| 40 | 9 | 24 | 254.00 | 57 | yes | 1.77e-10 | 1.76e-10 |
| 40 | 9 | 95 | 768.08 | 176 | no | 3.83e-10 | 3.83e-10 |
| 60 | 9 | 24 | 381.00 | 57 | yes | 2.25e-10 | 2.24e-10 |
| 60 | 9 | 95 | 1152.12 | 176 | no | -2.34e-10 | 2.33e-10 |
| 80 | 9 | 24 | 508.00 | 57 | yes | 3.20e-10 | 3.19e-10 |
| 80 | 9 | 95 | 1536.16 | 176 | no | -2.61e-10 | 2.62e-10 |
| 100 | 11 | 23 | 635.00 | 57 | yes | -2.86e-10 | 2.87e-10 |
| 100 | 11 | 76 | 1536.16 | 142 | no | -3.98e-10 | 3.99e-10 |
| 120 | 11 | 25 | 762.00 | 58 | no | -4.76e-10 | 4.77e-10 |
| 120 | 11 | 114 | 2765.09 | 211 | yes | 4.00e-10 | 4.00e-10 |
| 160 | 11 | 23 | 1016.00 | 57 | yes | -4.38e-10 | 4.38e-10 |
| 160 | 11 | 114 | 3686.79 | 211 | yes | -1.09e-10 | 1.08e-10 |

The matrix validates the solver and catalog intersection. Full CAD was tested
for ASA80 only; the remaining sizes must therefore not yet be advertised as
fully CAD-validated.

## Performance

| Operation | Result | Time |
|---|---:|---:|
| ASA80 sprocket, 11T | valid | 0.77 s |
| ASA80 chain | 47 links | 3.80 s |
| ASA80 full drive | 47 links + 2 sprockets | 3.98 s |
| ASA80 chain scaling | 49 links | 3.84 s |
| ASA80 chain scaling | 102 links | 5.01 s |
| ASA80 chain scaling | 153 links | 6.74 s |

All chain cases used three shared rigid templates and `App::Link` instances.
