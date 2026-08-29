"""Instantiate rigid templates as App::Link objects using solver poses."""

from __future__ import annotations

import re
from math import atan2, cos, degrees, hypot, radians, sin
from datetime import datetime
from pathlib import Path


def _safe_name(value):
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(value)).strip("_")
    return value or "ASA_Chain_Drive"


def _unique_document_name(App, base_name):
    base_name = _safe_name(base_name)
    candidate = base_name
    suffix = 2
    existing_documents = App.listDocuments()
    while candidate in existing_documents:
        candidate = f"{base_name}_{suffix}"
        suffix += 1
    return candidate


def _add_property_once(obj, property_type, name, group):
    if name not in obj.PropertiesList:
        obj.addProperty(property_type, name, group)


def _sprocket_phase_deg(result, center_x_mm, pitch_radius_mm):
    """Align one ASME tooth space with the nearest chain roller center."""
    candidates = []
    for x_mm, z_mm in result["roller_centers"]:
        radial_error = abs(
            hypot(float(x_mm) - center_x_mm, float(z_mm)) - pitch_radius_mm
        )
        candidates.append((radial_error, float(x_mm), float(z_mm)))
    if not candidates:
        return 0.0
    _, x_mm, z_mm = min(candidates, key=lambda item: item[0])
    return degrees(atan2(z_mm, x_mm - center_x_mm))


def generate_chain_drive_document(
    chain_data,
    result,
    output_dir,
    document_name=None,
    save=True,
    small_sprocket_data=None,
    large_sprocket_data=None,
    small_bore_diameter_mm=None,
    large_bore_diameter_mm=None,
    sprocket_library_dir=None,
    sprocket_library_search_dirs=None,
):
    """Create a chain-drive document, optionally including both sprockets."""
    import FreeCAD as App

    from cad.templates import create_all_templates

    asa_size = str(chain_data["asa_size"])
    base_name = document_name or f"ASA_{asa_size}_Chain_Drive"
    internal_name = _unique_document_name(App, base_name)
    doc = App.newDocument(internal_name)
    doc.Label = f"ASA {asa_size} Chain Drive"

    root = doc.addObject("App::Part", "ASAChainDrive")
    root.Label = f"ASA {asa_size} Chain Drive"
    templates_group = doc.addObject("App::DocumentObjectGroup", "Templates")
    templates_group.Label = "Rigid Link Templates"
    chain = doc.addObject("App::Part", "GeneratedChain")
    chain.Label = f"Generated Chain - {int(result['link_count'])} links"
    root.addObject(templates_group)
    root.addObject(chain)

    templates = create_all_templates(doc, chain_data, templates_group)

    small_sprocket = None
    large_sprocket = None
    small_geometry = None
    large_geometry = None

    if (small_sprocket_data is None) != (large_sprocket_data is None):
        raise ValueError(
            "Provide both small_sprocket_data and large_sprocket_data, or neither."
        )

    if small_sprocket_data is not None:
        from cad.sprocket_library import add_sprocket_from_library
        from config import get_sprocket_library_dir

        if sprocket_library_dir is None:
            sprocket_library_dir = get_sprocket_library_dir()
        small_bore = (
            float(small_sprocket_data["pilot_bore_mm"])
            if small_bore_diameter_mm is None
            else float(small_bore_diameter_mm)
        )
        large_bore = (
            float(large_sprocket_data["pilot_bore_mm"])
            if large_bore_diameter_mm is None
            else float(large_bore_diameter_mm)
        )
        (
            small_sprocket,
            small_geometry,
            small_library_path,
            small_library_cache_hit,
        ) = add_sprocket_from_library(
            target_doc=doc,
            chain_data=chain_data,
            sprocket_data=small_sprocket_data,
            bore_diameter_mm=small_bore,
            library_dir=sprocket_library_dir,
            additional_search_dirs=sprocket_library_search_dirs,
            object_name="SmallSprocket",
            label=(
                f"Small Sprocket - ASA {asa_size}-1 - "
                f"{int(result['small_sprocket_teeth'])}T"
            ),
        )
        (
            large_sprocket,
            large_geometry,
            large_library_path,
            large_library_cache_hit,
        ) = add_sprocket_from_library(
            target_doc=doc,
            chain_data=chain_data,
            sprocket_data=large_sprocket_data,
            bore_diameter_mm=large_bore,
            library_dir=sprocket_library_dir,
            additional_search_dirs=sprocket_library_search_dirs,
            object_name="LargeSprocket",
            label=(
                f"Large Sprocket - ASA {asa_size}-1 - "
                f"{int(result['large_sprocket_teeth'])}T"
            ),
        )

        corrected_center = float(result["corrected_center_distance_mm"])
        small_phase = _sprocket_phase_deg(
            result,
            0.0,
            float(result["small_pitch_radius_mm"]),
        )
        large_phase = _sprocket_phase_deg(
            result,
            corrected_center,
            float(result["large_pitch_radius_mm"]),
        )
        small_sprocket.Placement = App.Placement(
            App.Vector(0.0, 0.0, 0.0),
            App.Rotation(App.Vector(0.0, -1.0, 0.0), small_phase),
        )
        large_sprocket.Placement = App.Placement(
            App.Vector(corrected_center, 0.0, 0.0),
            App.Rotation(App.Vector(0.0, -1.0, 0.0), large_phase),
        )
        root.addObject(small_sprocket)
        root.addObject(large_sprocket)

        _add_property_once(
            small_sprocket, "App::PropertyAngle", "AssemblyPhase", "Assembly"
        )
        small_sprocket.AssemblyPhase = small_phase
        _add_property_once(
            large_sprocket, "App::PropertyAngle", "AssemblyPhase", "Assembly"
        )
        large_sprocket.AssemblyPhase = large_phase

    for name, value, property_type in (
        ("ASASize", asa_size, "App::PropertyString"),
        ("SmallSprocketTeeth", int(result["small_sprocket_teeth"]), "App::PropertyInteger"),
        ("LargeSprocketTeeth", int(result["large_sprocket_teeth"]), "App::PropertyInteger"),
        ("LinkCount", int(result["link_count"]), "App::PropertyInteger"),
        ("DesiredCenterDistance", float(result["desired_center_distance_mm"]), "App::PropertyLength"),
        ("CorrectedCenterDistance", float(result["corrected_center_distance_mm"]), "App::PropertyLength"),
        ("ClosureResidual", float(result["closure_residual_mm"]), "App::PropertyFloat"),
        ("MaximumPitchError", float(result["maximum_pitch_error_mm"]), "App::PropertyFloat"),
    ):
        _add_property_once(root, property_type, name, "Chain Drive")
        setattr(root, name, value)

    links = []
    for pose in result["link_poses"]:
        index = int(pose["index"])
        link_type = str(pose["type"]).lower()
        object_name = f"{link_type.capitalize()}Link_{index:03d}"
        instance = doc.addObject("App::Link", object_name)
        instance.Label = f"{index:03d} - {link_type.capitalize()}Link"
        instance.LinkedObject = templates[link_type]

        # Solver +y maps to FreeCAD +Z.  Rotation around -Y maps local +X
        # to (cos(theta), 0, sin(theta)) in the global XZ plane.
        solver_angle_deg = float(pose["angle_deg"])
        placement_angle_deg = solver_angle_deg
        position_x = float(pose["x_mm"])
        position_z = float(pose["y_mm"])

        if link_type == "offset":
            # The solver's final odd span runs roller -> pin.  The canonical
            # template is deliberately pin-at-A -> roller-at-B, so map local
            # JointB to the solver start and local JointA to the solver end.
            angle_rad = radians(solver_angle_deg)
            span_length = float(pose.get("length_mm", chain_data["pitch_P_mm"]))
            position_x += span_length * cos(angle_rad)
            position_z += span_length * sin(angle_rad)
            placement_angle_deg += 180.0

        position = App.Vector(position_x, 0.0, position_z)
        rotation = App.Rotation(
            App.Vector(0.0, -1.0, 0.0), placement_angle_deg
        )
        instance.Placement = App.Placement(position, rotation)

        _add_property_once(instance, "App::PropertyInteger", "ChainIndex", "Chain")
        instance.ChainIndex = index
        _add_property_once(instance, "App::PropertyString", "ChainLinkType", "Chain")
        instance.ChainLinkType = link_type.capitalize()
        _add_property_once(instance, "App::PropertyAngle", "SolverAngle", "Solver Pose")
        instance.SolverAngle = solver_angle_deg
        _add_property_once(
            instance,
            "App::PropertyString",
            "InterfaceMapping",
            "Solver Pose",
        )
        instance.InterfaceMapping = (
            "JointB (roller) -> solver start; JointA (pin) -> solver end"
            if link_type == "offset"
            else "JointA -> solver start; JointB -> solver end"
        )
        chain.addObject(instance)
        links.append(instance)

    doc.recompute()
    if getattr(App, "GuiUp", False):
        templates_group.ViewObject.Visibility = False
        try:
            import FreeCADGui as Gui

            Gui.activeDocument().activeView().viewAxonometric()
            Gui.activeDocument().activeView().fitAll()
        except Exception:
            pass

    saved_path = None
    if save:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = (
            f"ASA_{asa_size}_z{int(result['small_sprocket_teeth'])}_"
            f"z{int(result['large_sprocket_teeth'])}_"
            f"N{int(result['link_count'])}_{timestamp}.FCStd"
        )
        saved_path = output_dir / file_name
        doc.recompute()
        doc.saveAs(str(saved_path))

    return {
        "document": doc,
        "root": root,
        "chain": chain,
        "templates": templates,
        "links": links,
        "small_sprocket": small_sprocket,
        "large_sprocket": large_sprocket,
        "small_sprocket_geometry": small_geometry,
        "large_sprocket_geometry": large_geometry,
        "small_sprocket_library_path": (
            small_library_path if small_sprocket is not None else None
        ),
        "large_sprocket_library_path": (
            large_library_path if large_sprocket is not None else None
        ),
        "small_sprocket_cache_hit": (
            small_library_cache_hit if small_sprocket is not None else None
        ),
        "large_sprocket_cache_hit": (
            large_library_cache_hit if large_sprocket is not None else None
        ),
        "saved_path": saved_path,
    }
