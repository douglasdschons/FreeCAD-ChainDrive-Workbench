from pathlib import Path

import pytest

from core.catalog import get_chain_data, load_catalog, normalize_asa_size, to_float
from core.sprocket_catalog import (
    get_available_asa_sizes,
    get_available_teeth,
    get_sprocket,
    load_enco_sprocket_catalog,
)


ROOT = Path(__file__).resolve().parents[1]


def test_chain_catalog_required_dimensions_and_decimal_parsing():
    catalog = load_catalog(ROOT / "data" / "chains" / "enco_asa_chains.csv")
    for size in (35, 40, 60, 80, 100, 120, 160):
        row = get_chain_data(catalog, size)
        for field in (
            "pitch_P_mm", "roller_diameter_R_mm", "inner_width_E_mm",
            "plate_height_H_mm", "pin_diameter_G_mm", "plate_thickness_T_mm",
        ):
            assert float(row[field]) > 0
    assert to_float("25,40") == pytest.approx(25.4)
    assert normalize_asa_size("ASA 80-1") == "80"


def test_sprocket_catalog_supported_intersection():
    catalog = load_enco_sprocket_catalog(ROOT / "data" / "sprockets" / "enco")
    sizes = get_available_asa_sizes(catalog, strands=1, valid_only=True)
    for size in (35, 40, 60, 80, 100, 120, 160):
        assert size in sizes
        teeth = get_available_teeth(catalog, size, 1, True)
        assert teeth
        item = get_sprocket(catalog, size, teeth[0], 1, "ENCO", True)
        for field in (
                "teeth_z", "dp_catalog_mm", "outside_diameter_mm",
                "hub_diameter_mm", "total_length_mm", "pilot_bore_mm", "maximum_bore_mm",
        ):
            assert float(item[field]) > 0
