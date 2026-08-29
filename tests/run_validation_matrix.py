"""Produce a reproducible pure-Python multi-size solver report."""

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.catalog import get_chain_data, load_catalog
from core.discrete_solver import calculate_discrete_chain_drive_geometry
from core.sprocket_catalog import get_available_teeth, load_enco_sprocket_catalog


chains = load_catalog(ROOT / "data" / "chains" / "enco_asa_chains.csv")
sprockets = load_enco_sprocket_catalog(ROOT / "data" / "sprockets" / "enco")

print("asa,z1,z2,desired_mm,N,offset,residual_mm,max_pitch_error_mm,time_s,status")
requested_sizes = tuple(map(int, sys.argv[1:])) or (35, 40, 60, 80, 100, 120, 160)
for asa in requested_sizes:
    available = get_available_teeth(sprockets, asa, 1, True)
    samples = sorted(set((available[0], available[len(available) // 2], available[-1])))
    pairs = ((samples[0], samples[1]), (samples[0], samples[-1]))
    pitch = float(get_chain_data(chains, asa)["pitch_P_mm"])
    for z1, z2 in pairs:
        desired = max(20.0 * pitch, 2.0 * pitch * z2 / 3.141592653589793)
        started = time.perf_counter()
        try:
            result = calculate_discrete_chain_drive_geometry(pitch, z1, z2, desired)
            elapsed = time.perf_counter() - started
            print(
                f"{asa},{z1},{z2},{desired:.6f},{result['link_count']},"
                f"{result['requires_offset_link']},{result['closure_residual_mm']:.3e},"
                f"{result['maximum_pitch_error_mm']:.3e},{elapsed:.6f},PASS"
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            print(f"{asa},{z1},{z2},{desired:.6f},,,,,{elapsed:.6f},FAIL:{exc}")
