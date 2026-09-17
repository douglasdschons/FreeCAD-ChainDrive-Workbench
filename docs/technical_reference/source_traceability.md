# Source traceability

The current production source is the authority for implemented behavior. Bibliographic sources explain engineering origin; they do not override code silently.

| Topic | Implementation authority | Engineering/source basis | Status |
|---|---|---|---|
| `r_p=P/[2 sin(π/z)]` | `calculate_pitch_radius`; `calculate_asme_tooth_geometry` | ASME B29.1; pitch polygon | Matched in both modules |
| Four-segment tangent locus | `build_exact_pitch_path` | Classical open-drive geometry; iwis length context | Documented exactly |
| Count estimate and ±3 search | `calculate_discrete_chain_drive_geometry` | Implementation policy | Confirmed |
| `||p_(i+1)-p_i||=P` | `find_next_roller_path_coordinate`, `walk_rigid_chain` | Discrete rigid-link kinematics | Confirmed |
| Signed closure `R_s=s_N-L_Γ` | `walk_rigid_chain`, `_closure_residual`, center solver | Implementation closure coordinate | Confirmed; older Euclidean wording corrected |
| Geometric `p_N≈p_0` | periodic `point_at`; closing link pose | Closed polygon condition | Consequence, not stored scalar root |
| Minimum `|C_N-C_d|` selection | `calculate_discrete_chain_drive_geometry` | Implementation policy | Confirmed |
| Parity / OffsetLink | same solver function | Chain assembly topology | Confirmed |
| Solver-to-CAD mapping and `-Y` | `generate_chain_drive_document` | FreeCAD placement convention | Confirmed |
| Offset terminal reversal | offset branch in chain generator | Pin-at-A → roller-at-B template | Confirmed |
| Chain `P,E,R,H,G,L,T` data | `core/catalog.py`, chain CSV, `templates.py` | ENCO-derived table | Exact catalog pages pending |
| Four-arc plates | `create_plate_profile_face` | Simplified implementation profile | Equation documented; not manufacturing-certified |
| Inner/Outer links | `create_inner_template`, `create_outer_template` | iwis handbook p. 9 anatomy | Confirmed |
| OffsetLink loft/proportions | `cad/offset_link_generator.py` | Preserved ASA80 reference and validation FCStd | ASA80 functional; multi-size provisional |
| Seating diameter | `calculate_asme_tooth_geometry` | ASME B29.1 / GEARS | Code transcribed; edition check pending |
| `A,B,E,F,...` and tooth points | same function and intersection helpers | GEARS `design_draw_sprocket_5.pdf`, pp. 2–12 | Exact code formulas documented; no points invented |
| Mirrored cutter/polar pattern | `create_tooth_space_cutter`, `create_sprocket` | GEARS construction / symmetry | Confirmed |
| Commercial OD/hub/length/bores | sprocket parser, ENCO CSVs, `create_sprocket` | `catalogo_enco.pdf` | Per-row page map pending |
| Flange-width lookup | `ASME_SINGLE_FLANGE_WIDTH_MM` | ASME basis claimed by module | Controlled table check pending |
| Axial chamfer | `create_revolved_body` | ASME Section A wording in code | Clause/page pending |
| Static phase | `_sprocket_phase_deg` | Implementation policy | Confirmed; not dynamic meshing |
| Canonical ASA80 regression | `tests/test_solver.py`, validation report, example | Project evidence | Current values documented; manual CAD measurement pending |
| Multi-size matrix | validation matrix script/report | Project evidence | Numerical/catalog only outside ASA80 |

## Reference sources

- This repository is the primary implementation authority.
- `ASAChainDriveApp` is the predecessor project used for validation models and earlier figure drafts; it is not bundled here.
- GEARS, `design_draw_sprocket_5.pdf`: 15-page drawing note.
- ENCO, `catalogo_enco.pdf`: commercial dimensions underlying the included CSVs.
- iwis, *Handbook for Chain Engineering*: anatomy and design context.
- Tsubaki, *Guia de Produtos*: terminology and context.
- ASME B29.1 and ISO 606 were treated as controlled references.

External reference PDFs and predecessor models are not included in this repository.

## Provisional review items

1. Exact ASME B29.1 and ISO 606 editions in the bibliography.
2. Exact ENCO page for every derived table.
3. Clause/table provenance for flange widths and chamfer rules.
4. OffsetLink dimensional confirmation outside ASA80.
5. Independent FreeCAD measurements for planned cases.
