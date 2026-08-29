"""Create lightweight rigid chain-link templates directly in FreeCAD memory."""

from __future__ import annotations

import FreeCAD as App
import Part

from cad.offset_link_generator import create_offset_link


PROFILE_RATIO = 0.875


def _clean_shape(shape):
    try:
        return shape.removeSplitter()
    except Exception:
        return shape


def read_dimensions(chain_data):
    return {
        "P": float(chain_data["pitch_P_mm"]),
        "E": float(chain_data["inner_width_E_mm"]),
        "R": float(chain_data["roller_diameter_R_mm"]),
        "H": float(chain_data["plate_height_H_mm"]),
        "G": float(chain_data["pin_diameter_G_mm"]),
        "L": float(chain_data["overall_width_L_mm"]),
        "T": float(chain_data["plate_thickness_T_mm"]),
    }


def create_plate_profile_face(y_position, pitch, height):
    """Make the four-arc ANSI-style plate profile in the global XZ plane."""
    end_radius = height / 2.0
    half_pitch = pitch / 2.0
    half_neck = height * PROFILE_RATIO / 2.0
    denominator = 2.0 * (half_neck - end_radius)
    if abs(denominator) < 1.0e-12:
        raise ValueError("Plate neck ratio produces a degenerate profile.")

    relief_radius = (
        end_radius**2 - half_pitch**2 - half_neck**2
    ) / denominator
    if relief_radius <= 0.0:
        raise ValueError(
            "Plate dimensions cannot produce a tangent four-arc profile."
        )
    relief_center_z = half_neck + relief_radius
    center_distance = end_radius + relief_radius
    tangent_scale = end_radius / center_distance

    left_upper = App.Vector(
        half_pitch * tangent_scale,
        y_position,
        relief_center_z * tangent_scale,
    )
    left_lower = App.Vector(
        half_pitch * tangent_scale,
        y_position,
        -relief_center_z * tangent_scale,
    )
    right_upper = App.Vector(
        pitch - half_pitch * tangent_scale,
        y_position,
        relief_center_z * tangent_scale,
    )
    right_lower = App.Vector(
        pitch - half_pitch * tangent_scale,
        y_position,
        -relief_center_z * tangent_scale,
    )

    upper_mid = App.Vector(pitch / 2.0, y_position, half_neck)
    lower_mid = App.Vector(pitch / 2.0, y_position, -half_neck)
    left_outer = App.Vector(-end_radius, y_position, 0.0)
    right_outer = App.Vector(pitch + end_radius, y_position, 0.0)

    edges = [
        Part.Arc(left_upper, upper_mid, right_upper).toShape(),
        Part.Arc(right_upper, right_outer, right_lower).toShape(),
        Part.Arc(right_lower, lower_mid, left_lower).toShape(),
        Part.Arc(left_lower, left_outer, left_upper).toShape(),
    ]
    return Part.Face(Part.Wire(edges))


def create_plate(inner_face_y, direction, pitch, height, pin_diameter, thickness):
    if direction not in (-1, 1):
        raise ValueError("Plate extrusion direction must be -1 or +1.")
    face = create_plate_profile_face(inner_face_y, pitch, height)
    solid = face.extrude(App.Vector(0.0, direction * thickness, 0.0))

    y_end = inner_face_y + direction * thickness
    hole_y = min(inner_face_y, y_end) - 1.0
    hole_length = thickness + 2.0
    for x_position in (0.0, pitch):
        hole = Part.makeCylinder(
            pin_diameter / 2.0,
            hole_length,
            App.Vector(x_position, hole_y, 0.0),
            App.Vector(0.0, 1.0, 0.0),
        )
        solid = solid.cut(hole)
    return _clean_shape(solid)


def create_roller(x_position, inner_width, roller_diameter, pin_diameter):
    axis = App.Vector(0.0, 1.0, 0.0)
    base = App.Vector(x_position, -inner_width / 2.0, 0.0)
    outer = Part.makeCylinder(roller_diameter / 2.0, inner_width, base, axis)
    bore = Part.makeCylinder(pin_diameter / 2.0, inner_width, base, axis)
    return _clean_shape(outer.cut(bore))


def create_pin(x_position, pin_diameter, overall_width):
    return Part.makeCylinder(
        pin_diameter / 2.0,
        overall_width,
        App.Vector(x_position, -overall_width / 2.0, 0.0),
        App.Vector(0.0, 1.0, 0.0),
    )


def _add_property_once(component, property_type, name, group):
    if name not in component.PropertiesList:
        component.addProperty(property_type, name, group)


def add_metadata(component, chain_data, link_type):
    dimensions = read_dimensions(chain_data)
    _add_property_once(component, "App::PropertyString", "LinkType", "Chain")
    component.LinkType = link_type
    _add_property_once(component, "App::PropertyString", "ASASize", "Chain")
    component.ASASize = str(chain_data["asa_size"])

    for name, value in {
        "Pitch": dimensions["P"],
        "InnerWidth": dimensions["E"],
        "RollerDiameter": dimensions["R"],
        "PlateHeight": dimensions["H"],
        "PinDiameter": dimensions["G"],
        "OverallWidth": dimensions["L"],
        "PlateThickness": dimensions["T"],
    }.items():
        _add_property_once(component, "App::PropertyLength", name, "ASA Dimensions")
        setattr(component, name, value)

    _add_property_once(component, "App::PropertyVector", "JointA", "Interface")
    component.JointA = App.Vector(0.0, 0.0, 0.0)
    _add_property_once(component, "App::PropertyVector", "JointB", "Interface")
    component.JointB = App.Vector(dimensions["P"], 0.0, 0.0)
    _add_property_once(
        component, "App::PropertyString", "LocalAxisConvention", "Interface"
    )
    component.LocalAxisConvention = (
        "X: JointA -> JointB; Y: pin/roller axis; Z: plate height"
    )


def _set_visual(component, color):
    if getattr(App, "GuiUp", False):
        component.ViewObject.ShapeColor = color
        component.ViewObject.LineColor = (0.18, 0.18, 0.18)


def create_inner_template(doc, chain_data):
    d = read_dimensions(chain_data)
    shapes = [
        create_plate(-d["E"] / 2.0, -1, d["P"], d["H"], d["G"], d["T"]),
        create_plate(+d["E"] / 2.0, +1, d["P"], d["H"], d["G"], d["T"]),
        create_roller(0.0, d["E"], d["R"], d["G"]),
        create_roller(d["P"], d["E"], d["R"], d["G"]),
    ]
    component = doc.addObject("Part::Feature", "InnerLink_Template")
    component.Label = f"ASA {chain_data['asa_size']} - InnerLink Template"
    component.Shape = Part.makeCompound(shapes)
    add_metadata(component, chain_data, "Inner")
    _set_visual(component, (0.72, 0.72, 0.75))
    return component


def create_outer_template(doc, chain_data):
    d = read_dimensions(chain_data)
    plate_offset = d["E"] / 2.0 + d["T"]
    shapes = [
        create_plate(-plate_offset, -1, d["P"], d["H"], d["G"], d["T"]),
        create_plate(+plate_offset, +1, d["P"], d["H"], d["G"], d["T"]),
        create_pin(0.0, d["G"], d["L"]),
        create_pin(d["P"], d["G"], d["L"]),
    ]
    component = doc.addObject("Part::Feature", "OuterLink_Template")
    component.Label = f"ASA {chain_data['asa_size']} - OuterLink Template"
    component.Shape = Part.makeCompound(shapes)
    add_metadata(component, chain_data, "Outer")
    _set_visual(component, (0.50, 0.53, 0.58))
    return component


def create_offset_template(doc, chain_data):
    """Create the canonical pin-at-A, roller-at-B offset template."""
    component = create_offset_link(doc, chain_data)
    add_metadata(component, chain_data, "Offset")
    _set_visual(component, (0.76, 0.56, 0.24))
    return component


def create_all_templates(doc, chain_data, parent_group=None):
    templates = {
        "inner": create_inner_template(doc, chain_data),
        "outer": create_outer_template(doc, chain_data),
        "offset": create_offset_template(doc, chain_data),
    }
    if parent_group is not None:
        for component in templates.values():
            parent_group.addObject(component)
    doc.recompute()
    return templates
