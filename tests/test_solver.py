import math

import pytest

from core.discrete_solver import (
    calculate_discrete_chain_drive_geometry,
    calculate_pitch_radius,
)


def test_pitch_diameter_formula():
    pitch, teeth = 25.4, 20
    diameter = 2.0 * calculate_pitch_radius(pitch, teeth)
    assert diameter == pytest.approx(pitch / math.sin(math.pi / teeth), rel=1e-13)


def test_canonical_asa80_discrete_solution():
    result = calculate_discrete_chain_drive_geometry(25.4, 11, 20, 400.0)
    assert result["link_count"] == 47
    assert result["requires_offset_link"] is True
    assert result["corrected_center_distance_mm"] == pytest.approx(398.338658801, abs=1e-9)
    assert result["center_correction_mm"] == pytest.approx(-1.661341199, abs=1e-9)
    assert result["closure_residual_mm"] < 1e-8
    assert result["maximum_pitch_error_mm"] < 1e-8


@pytest.mark.parametrize("even", [False, True])
def test_link_count_parity_and_exact_pitch(even):
    result = calculate_discrete_chain_drive_geometry(
        25.4, 11, 20, 400.0, require_even_link_count=even
    )
    if even:
        assert result["link_count"] % 2 == 0
        assert result["requires_offset_link"] is False
    for pose in result["link_poses"]:
        assert pose["length_mm"] == pytest.approx(25.4, abs=1e-8)
    assert result["closure_residual_mm"] < 1e-8

