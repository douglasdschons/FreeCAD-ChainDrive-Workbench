"""Public application API for the ASA Chain Drive workbench.

FreeCAD-dependent modules are imported lazily so catalog and solver code remain
usable with ordinary CPython and in continuous integration.
"""

from __future__ import annotations

from pathlib import Path

from core.catalog import get_chain_data, load_catalog
from core.discrete_solver import calculate_discrete_chain_drive_geometry
from core.sprocket_catalog import get_sprocket, load_enco_sprocket_catalog


APP_ROOT = Path(__file__).resolve().parent
CHAIN_CATALOG = APP_ROOT / "data" / "chains" / "enco_asa_chains.csv"
SPROCKET_CATALOG = APP_ROOT / "data" / "sprockets" / "enco"


def _catalog_records(asa_size: int, teeth: int):
    chains = load_catalog(CHAIN_CATALOG)
    sprockets = load_enco_sprocket_catalog(SPROCKET_CATALOG)
    chain = get_chain_data(chains, asa_size)
    sprocket = get_sprocket(
        sprockets, asa=asa_size, teeth_z=teeth, strands=1,
        manufacturer="ENCO", valid_only=True,
    )
    return chain, sprocket


def generate_chain(
    asa_size: int,
    small_teeth: int,
    large_teeth: int,
    center_distance_mm: float,
    *,
    require_even_link_count: bool = False,
    output_dir=None,
    save: bool = True,
):
    """Generate a rigid-link chain document without sprocket solids."""
    chain, _ = _catalog_records(asa_size, small_teeth)
    result = calculate_discrete_chain_drive_geometry(
        float(chain["pitch_P_mm"]), small_teeth, large_teeth,
        center_distance_mm, require_even_link_count,
    )
    from cad.chain_generator import generate_chain_drive_document
    from config import get_output_dir

    return generate_chain_drive_document(
        chain, result, output_dir or get_output_dir(), save=save,
    )


def generate_sprocket(
    asa_size: int,
    teeth: int,
    *,
    bore_diameter_mm: float | None = None,
    library_dir=None,
):
    """Generate or reuse one catalog-backed sprocket document."""
    chain, sprocket = _catalog_records(asa_size, teeth)
    from cad.sprocket_library import open_or_create_sprocket_document
    from config import get_sprocket_library_dir

    bore = float(sprocket["pilot_bore_mm"] if bore_diameter_mm is None else bore_diameter_mm)
    return open_or_create_sprocket_document(
        chain, sprocket, bore, library_dir or get_sprocket_library_dir(),
    )


def generate_chain_drive(
    asa_size: int,
    small_teeth: int,
    large_teeth: int,
    center_distance_mm: float,
    *,
    require_even_link_count: bool = False,
    output_dir=None,
    save: bool = True,
):
    """Generate both sprockets and the exact-pitch rigid-link chain assembly."""
    chain, small = _catalog_records(asa_size, small_teeth)
    _, large = _catalog_records(asa_size, large_teeth)
    result = calculate_discrete_chain_drive_geometry(
        float(chain["pitch_P_mm"]), small_teeth, large_teeth,
        center_distance_mm, require_even_link_count,
    )
    from cad.chain_generator import generate_chain_drive_document
    from config import get_output_dir, get_sprocket_library_dir

    return generate_chain_drive_document(
        chain, result, output_dir or get_output_dir(), save=save,
        small_sprocket_data=small, large_sprocket_data=large,
        sprocket_library_dir=get_sprocket_library_dir(),
    )

