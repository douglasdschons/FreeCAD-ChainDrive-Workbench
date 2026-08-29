# Documentation-to-code audit

| Technical-reference item | Code location | Code symbol | Status |
|---|---|---|---|
| `Dp = P/sin(pi/z)` | `core/discrete_solver.py` | `calculate_pitch_radius` | Equivalent (`Dp=2rp`) |
| Exact pitch constraint | `core/discrete_solver.py` | `find_next_roller_path_coordinate`, `walk_rigid_chain` | Matched |
| Integer link selection/parity | `core/discrete_solver.py` | `calculate_discrete_chain_drive_geometry` | Matched |
| Center-distance root solve | `core/discrete_solver.py` | `solve_center_distance_for_link_count` | Matched |
| Closure and maximum pitch error | `core/discrete_solver.py` | result fields | Matched |
| `(x,y)` to `(X,Z)`, rotation about `-Y` | `cad/chain_generator.py` | placement loop | Matched |
| Offset terminal reversal | `cad/chain_generator.py` | `link_type == "offset"` branch | Matched |
| ASME tooth geometry | `cad/asme_sprocket_generator.py` | `calculate_asme_tooth_geometry` | Matched to implementation; source-table provenance needs release review |
| Commercial body dimensions | `core/sprocket_catalog.py`, `cad/asme_sprocket_generator.py` | catalog parsing, `create_sprocket` | Matched |

No code/document equation divergence was found. The historical residual values
quoted in project notes vary slightly from current execution at approximately
`2.1e-10 mm`; both are well within the documented `1e-8 mm` acceptance limit.

