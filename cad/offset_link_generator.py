"""
offset_link_generator.py
========================

Robust parametric ANSI/ASA one-pitch offset-link (half-link)
generator for FreeCAD.

Coordinate convention
---------------------
X = chain longitudinal direction
Y = pin / roller axis
Z = plate height

JointA = (0, 0, 0)      -> connecting-pin end
JointB = (P, 0, 0)      -> roller / bushing end

Topology
--------
OffsetLink
├── OffsetPlateLeft
├── OffsetPlateRight
├── Roller
├── Bushing
└── ConnectingPin

Plate reference geometry
------------------------
The ASA 80 reference used during development is:

    P                    = 25.40 mm
    plate thickness      = 3.20 mm
    end-lobe radius      = 10.40 mm
    concave relief radius= 12.00 mm
    pin diameter         = 7.92 mm
    bend start           = 8.92 mm
    bend end             = 14.90 mm

The X-Z plate outline is made from two circular end lobes joined
by two tangent concave arcs.

IMPORTANT IMPLEMENTATION NOTE
-----------------------------
The bent plate is NOT made by lofting two non-planar perimeter
wires. That construction can produce invalid OpenCascade solids.

Instead, the central web is built from a sequence of planar
rectangular Y-Z cross-sections and a ruled solid loft. The exact
circular end lobes are then fused to that web. This is much more
robust in FreeCAD/OpenCascade.

The resulting object remains a rigid multi-solid compound for
efficient use as an App::Link template in the chain assembly.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any, Dict, Mapping, Optional

import FreeCAD as App
import Part


# ============================================================
# REFERENCE RATIOS
# ============================================================

ASA80_PITCH_MM = 25.40

DEFAULT_END_RADIUS_RATIO = (
    10.40 / ASA80_PITCH_MM
)

DEFAULT_RELIEF_RADIUS_RATIO = (
    12.00 / ASA80_PITCH_MM
)

DEFAULT_BEND_START_RATIO = (
    8.92 / ASA80_PITCH_MM
)

DEFAULT_BEND_END_RATIO = (
    14.90 / ASA80_PITCH_MM
)

DEFAULT_SIDE_CLEARANCE_MM = 0.03

# Number of sections used to approximate the exact X-Z relief
# while lofting the bent plate web. 28 is already visually smooth
# and remains light enough for repeated chain generation.
DEFAULT_WEB_SECTIONS = 28

EPS = 1.0e-8


# ============================================================
# SPECIFICATION
# ============================================================

@dataclass(frozen=True)
class OffsetLinkSpec:

    # Required chain dimensions
    pitch_mm: float
    roller_diameter_mm: float
    inner_width_mm: float
    pin_diameter_mm: float
    plate_thickness_mm: float

    # Optional chain/manufacturer dimensions
    roller_width_mm: Optional[float] = None

    plate_end_radius_mm: Optional[float] = None
    plate_relief_radius_mm: Optional[float] = None

    bushing_outer_diameter_mm: Optional[float] = None
    bushing_inner_diameter_mm: Optional[float] = None

    side_clearance_mm: float = DEFAULT_SIDE_CLEARANCE_MM

    bend_start_ratio: float = DEFAULT_BEND_START_RATIO
    bend_end_ratio: float = DEFAULT_BEND_END_RATIO

    pin_head_diameter_mm: Optional[float] = None
    pin_head_thickness_mm: Optional[float] = None
    pin_projection_mm: Optional[float] = None

    web_sections: int = DEFAULT_WEB_SECTIONS

    def resolved(self) -> "OffsetLinkSpec":

        P = float(self.pitch_mm)
        Dr = float(self.roller_diameter_mm)
        E = float(self.inner_width_mm)
        Dp = float(self.pin_diameter_mm)
        T = float(self.plate_thickness_mm)

        if min(P, Dr, E, Dp, T) <= 0.0:
            raise ValueError(
                "Pitch, roller diameter, inner width, pin diameter "
                "and plate thickness must all be positive."
            )

        roller_width = (
            float(self.roller_width_mm)
            if self.roller_width_mm is not None
            else E
        )

        end_radius = (
            float(self.plate_end_radius_mm)
            if self.plate_end_radius_mm is not None
            else DEFAULT_END_RADIUS_RATIO * P
        )

        relief_radius = (
            float(self.plate_relief_radius_mm)
            if self.plate_relief_radius_mm is not None
            else DEFAULT_RELIEF_RADIUS_RATIO * P
        )

        bushing_od = (
            float(self.bushing_outer_diameter_mm)
            if self.bushing_outer_diameter_mm is not None
            else max(
                1.25 * Dp,
                0.58 * Dr,
            )
        )

        bushing_id = (
            float(self.bushing_inner_diameter_mm)
            if self.bushing_inner_diameter_mm is not None
            else Dp + max(
                0.05,
                0.001 * P,
            )
        )

        if bushing_id >= bushing_od:
            bushing_od = (
                bushing_id
                + max(
                    0.50,
                    0.03 * P,
                )
            )

        pin_head_diameter = (
            float(self.pin_head_diameter_mm)
            if self.pin_head_diameter_mm is not None
            else 1.35 * Dp
        )

        pin_head_thickness = (
            float(self.pin_head_thickness_mm)
            if self.pin_head_thickness_mm is not None
            else 0.30 * Dp
        )

        pin_projection = (
            float(self.pin_projection_mm)
            if self.pin_projection_mm is not None
            else max(
                0.50,
                0.20 * Dp,
            )
        )

        if not (
            0.0 < self.bend_start_ratio
            < self.bend_end_ratio
            < 1.0
        ):
            raise ValueError(
                "Bend ratios must satisfy "
                "0 < bend_start_ratio < bend_end_ratio < 1."
            )

        return replace(
            self,
            pitch_mm=P,
            roller_diameter_mm=Dr,
            inner_width_mm=E,
            pin_diameter_mm=Dp,
            plate_thickness_mm=T,
            roller_width_mm=roller_width,
            plate_end_radius_mm=end_radius,
            plate_relief_radius_mm=relief_radius,
            bushing_outer_diameter_mm=bushing_od,
            bushing_inner_diameter_mm=bushing_id,
            pin_head_diameter_mm=pin_head_diameter,
            pin_head_thickness_mm=pin_head_thickness,
            pin_projection_mm=pin_projection,
            web_sections=max(
                12,
                int(self.web_sections),
            ),
        )


# ============================================================
# CHAIN-DATA ADAPTER
# ============================================================

def _get_value(
    source: Any,
    names,
    default=None,
):

    for name in names:

        if isinstance(source, Mapping):

            if (
                name in source
                and source[name] is not None
            ):
                return source[name]

        else:

            if hasattr(source, name):

                value = getattr(
                    source,
                    name,
                )

                if value is not None:
                    return value

    return default


def _required(
    source: Any,
    names,
    label: str,
) -> float:

    value = _get_value(
        source,
        names,
    )

    if value is None:
        raise KeyError(
            f"Missing {label}. "
            f"Expected one of: {names}"
        )

    return float(value)


def spec_from_chain_data(
    chain_data: Any,
    **overrides,
) -> OffsetLinkSpec:

    spec = OffsetLinkSpec(

        pitch_mm=_required(
            chain_data,
            (
                "pitch_P_mm",
                "pitch_mm",
                "pitch",
                "P",
                "p",
            ),
            "pitch",
        ),

        roller_diameter_mm=_required(
            chain_data,
            (
                "roller_diameter_R_mm",
                "roller_diameter_mm",
                "roller_diameter",
                "Dr",
                "R",
            ),
            "roller diameter",
        ),

        inner_width_mm=_required(
            chain_data,
            (
                "inner_width_E_mm",
                "inner_width_mm",
                "inner_width",
                "E",
            ),
            "inner width",
        ),

        pin_diameter_mm=_required(
            chain_data,
            (
                "pin_diameter_G_mm",
                "pin_diameter_mm",
                "pin_diameter",
                "G",
                "Dp",
            ),
            "pin diameter",
        ),

        plate_thickness_mm=_required(
            chain_data,
            (
                "plate_thickness_T_mm",
                "plate_thickness_mm",
                "plate_thickness",
                "T",
            ),
            "plate thickness",
        ),

        roller_width_mm=_get_value(
            chain_data,
            (
                "roller_width_mm",
                "roller_length_mm",
                "roller_length_Lr_mm",
            ),
        ),

        bushing_outer_diameter_mm=_get_value(
            chain_data,
            (
                "bushing_outer_diameter_mm",
                "bushing_od_mm",
                "bushing_diameter_mm",
            ),
        ),

        bushing_inner_diameter_mm=_get_value(
            chain_data,
            (
                "bushing_inner_diameter_mm",
                "bushing_id_mm",
            ),
        ),
    )

    if overrides:

        valid_fields = set(
            spec.__dataclass_fields__.keys()
        )

        unknown = (
            set(overrides)
            - valid_fields
        )

        if unknown:
            raise KeyError(
                f"Unknown OffsetLinkSpec overrides: "
                f"{sorted(unknown)}"
            )

        spec = replace(
            spec,
            **overrides,
        )

    return spec.resolved()


def resolve_spec(
    source: Any,
    **overrides,
) -> OffsetLinkSpec:

    if isinstance(
        source,
        OffsetLinkSpec,
    ):

        spec = source

        if overrides:
            spec = replace(
                spec,
                **overrides,
            )

        return spec.resolved()

    return spec_from_chain_data(
        source,
        **overrides,
    )


# ============================================================
# EXACT X-Z PROFILE GEOMETRY
# ============================================================

def reference_profile_geometry(
    source: Any,
    **overrides,
) -> Dict[str, float]:

    spec = resolve_spec(
        source,
        **overrides,
    )

    P = spec.pitch_mm
    Re = spec.plate_end_radius_mm
    Rr = spec.plate_relief_radius_mm

    # Both end lobes have the same radius in the current
    # reference profile.
    #
    # Relief-circle center lies on X=P/2. External tangency to
    # either end lobe gives:
    #
    #   sqrt((P/2)^2 + zc^2) = Re + Rr

    distance = (
        Re + Rr
    )

    half_pitch = (
        P / 2.0
    )

    if distance <= half_pitch:
        raise ValueError(
            "Invalid plate profile: Re + Rr must be larger "
            "than P/2."
        )

    zc = math.sqrt(
        distance * distance
        - half_pitch * half_pitch
    )

    tangent_scale = (
        Re / distance
    )

    tangent_x = (
        half_pitch
        * tangent_scale
    )

    tangent_z = (
        zc
        * tangent_scale
    )

    return {
        "P":
            P,

        "end_radius":
            Re,

        "relief_radius":
            Rr,

        "relief_center_x":
            half_pitch,

        "relief_center_z":
            zc,

        "pin_tangent_x":
            tangent_x,

        "pin_tangent_z":
            tangent_z,

        "roller_tangent_x":
            P - tangent_x,

        "roller_tangent_z":
            tangent_z,

        "waist_half_height":
            zc - Rr,

        "waist_total_height":
            2.0 * (
                zc - Rr
            ),
    }


def _plate_half_height(
    x: float,
    geometry: Dict[str, float],
) -> float:
    """
    Exact positive-Z outer boundary of the 2D plate profile.
    """

    P = geometry["P"]
    Re = geometry["end_radius"]
    Rr = geometry["relief_radius"]

    tx0 = geometry["pin_tangent_x"]
    tx1 = geometry["roller_tangent_x"]

    if x <= tx0:

        value = (
            Re * Re
            - x * x
        )

        return math.sqrt(
            max(
                0.0,
                value,
            )
        )

    if x >= tx1:

        dx = (
            x - P
        )

        value = (
            Re * Re
            - dx * dx
        )

        return math.sqrt(
            max(
                0.0,
                value,
            )
        )

    xc = (
        geometry[
            "relief_center_x"
        ]
    )

    zc = (
        geometry[
            "relief_center_z"
        ]
    )

    dx = (
        x - xc
    )

    value = (
        Rr * Rr
        - dx * dx
    )

    if value < -1.0e-7:
        raise ValueError(
            "X coordinate is outside the relief-circle domain."
        )

    return (
        zc
        - math.sqrt(
            max(
                0.0,
                value,
            )
        )
    )


# ============================================================
# AXIAL PLATE SPACING / BEND
# ============================================================

def functional_plate_spacing(
    source: Any,
    **overrides,
):

    spec = resolve_spec(
        source,
        **overrides,
    )

    T = (
        spec.plate_thickness_mm
    )

    # Roller/bushing end:
    # plates flank the roller.
    narrow_inner_spacing = (
        spec.roller_width_mm
    )

    # Pin end:
    # plates must embrace the adjacent inner/roller link.
    adjacent_inner_link_outer_width = (
        spec.inner_width_mm
        + 2.0 * T
    )

    wide_inner_spacing = (
        adjacent_inner_link_outer_width
        + 2.0 * spec.side_clearance_mm
    )

    return (
        narrow_inner_spacing,
        wide_inner_spacing,
    )


def _smoothstep(
    u: float,
) -> float:
    """
    Quintic smoothstep:
    zero first and second derivative at both ends.
    """

    u = max(
        0.0,
        min(
            1.0,
            float(u),
        ),
    )

    return (
        6.0 * u**5
        - 15.0 * u**4
        + 10.0 * u**3
    )


def _plate_center_y(
    x: float,
    sign: float,
    spec: OffsetLinkSpec,
):

    narrow, wide = (
        functional_plate_spacing(
            spec
        )
    )

    T = (
        spec.plate_thickness_mm
    )

    y_pin = (
        sign
        * (
            wide / 2.0
            + T / 2.0
        )
    )

    y_roller = (
        sign
        * (
            narrow / 2.0
            + T / 2.0
        )
    )

    x0 = (
        spec.bend_start_ratio
        * spec.pitch_mm
    )

    x1 = (
        spec.bend_end_ratio
        * spec.pitch_mm
    )

    if x <= x0:
        return y_pin

    if x >= x1:
        return y_roller

    u = (
        (x - x0)
        / (x1 - x0)
    )

    s = _smoothstep(
        u
    )

    return (
        y_pin
        + s
        * (
            y_roller
            - y_pin
        )
    )


# ============================================================
# ROBUST CROSS-SECTION LOFT
# ============================================================

def _rectangular_section_wire(
    x: float,
    y_center: float,
    thickness: float,
    half_height: float,
):
    """
    Create one closed planar rectangle in the Y-Z plane.

    All cross-sections have exactly four edges and the same
    orientation, which makes Part.makeLoft much more reliable
    than lofting non-planar perimeter wires.
    """

    if half_height <= EPS:
        raise ValueError(
            "Plate cross-section height is zero or negative."
        )

    y0 = (
        y_center
        - thickness / 2.0
    )

    y1 = (
        y_center
        + thickness / 2.0
    )

    z0 = (
        -half_height
    )

    z1 = (
        +half_height
    )

    p1 = App.Vector(
        x,
        y0,
        z0,
    )

    p2 = App.Vector(
        x,
        y1,
        z0,
    )

    p3 = App.Vector(
        x,
        y1,
        z1,
    )

    p4 = App.Vector(
        x,
        y0,
        z1,
    )

    return Part.makePolygon([
        p1,
        p2,
        p3,
        p4,
        p1,
    ])


def _build_web_stations(
    spec: OffsetLinkSpec,
    geometry: Dict[str, float],
):
    """
    Generate X stations for the central web.

    The web overlaps both circular lobes slightly, so Boolean
    fusion has real volume intersection instead of coincident
    faces only.
    """

    P = spec.pitch_mm

    tx0 = (
        geometry[
            "pin_tangent_x"
        ]
    )

    tx1 = (
        geometry[
            "roller_tangent_x"
        ]
    )

    overlap = max(
        0.12,
        0.008 * P,
    )

    x_start = max(
        0.05 * P,
        tx0 - overlap,
    )

    x_end = min(
        0.95 * P,
        tx1 + overlap,
    )

    stations = {
        x_start,
        x_end,
        P / 2.0,
        spec.bend_start_ratio * P,
        spec.bend_end_ratio * P,
        tx0,
        tx1,
    }

    for index in range(
        spec.web_sections + 1
    ):

        u = (
            index
            / spec.web_sections
        )

        x = (
            x_start
            + u
            * (
                x_end
                - x_start
            )
        )

        stations.add(
            x
        )

    return sorted(
        x
        for x in stations
        if (
            x_start - EPS
            <= x
            <= x_end + EPS
        )
    )


def _make_plate_web(
    spec: OffsetLinkSpec,
    sign: float,
    geometry: Dict[str, float],
):
    """
    Build the bent central plate web from planar Y-Z sections.
    """

    stations = (
        _build_web_stations(
            spec,
            geometry,
        )
    )

    wires = []

    for x in stations:

        half_height = (
            _plate_half_height(
                x,
                geometry,
            )
        )

        y_center = (
            _plate_center_y(
                x,
                sign,
                spec,
            )
        )

        wires.append(
            _rectangular_section_wire(
                x,
                y_center,
                spec.plate_thickness_mm,
                half_height,
            )
        )

    # Ruled=True intentionally:
    # avoids OCC trying to fit a global spline skin through many
    # slightly offset sections. With enough stations the visual
    # result is smooth and the solid is robust.
    web = Part.makeLoft(
        wires,
        True,   # solid
        True,   # ruled
    )

    if web.isNull():
        raise RuntimeError(
            "Central offset-plate web could not be lofted."
        )

    return web


# ============================================================
# OFFSET PLATE
# ============================================================

def make_offset_plate(
    source: Any,
    side: str,
    **overrides,
):

    spec = resolve_spec(
        source,
        **overrides,
    )

    geometry = (
        reference_profile_geometry(
            spec
        )
    )

    side_name = (
        side
        .lower()
        .strip()
    )

    if side_name == "left":
        sign = -1.0

    elif side_name == "right":
        sign = +1.0

    else:
        raise ValueError(
            "side must be 'left' or 'right'."
        )

    P = spec.pitch_mm
    T = spec.plate_thickness_mm
    Re = spec.plate_end_radius_mm

    narrow, wide = (
        functional_plate_spacing(
            spec
        )
    )

    y_pin = (
        sign
        * (
            wide / 2.0
            + T / 2.0
        )
    )

    y_roller = (
        sign
        * (
            narrow / 2.0
            + T / 2.0
        )
    )

    # --------------------------------------------------------
    # Exact circular end lobes
    # --------------------------------------------------------

    pin_lobe = Part.makeCylinder(
        Re,
        T,
        App.Vector(
            0.0,
            y_pin - T / 2.0,
            0.0,
        ),
        App.Vector(
            0.0,
            1.0,
            0.0,
        ),
    )

    roller_lobe = Part.makeCylinder(
        Re,
        T,
        App.Vector(
            P,
            y_roller - T / 2.0,
            0.0,
        ),
        App.Vector(
            0.0,
            1.0,
            0.0,
        ),
    )

    # --------------------------------------------------------
    # Robust bent/waisted web
    # --------------------------------------------------------

    web = _make_plate_web(
        spec,
        sign,
        geometry,
    )

    # --------------------------------------------------------
    # Fuse the three overlapping solids
    # --------------------------------------------------------

    plate = pin_lobe.fuse(
        web
    )

    plate = plate.fuse(
        roller_lobe
    )

    if plate.isNull():
        raise RuntimeError(
            f"{side_name} plate fusion returned a null shape."
        )

    # --------------------------------------------------------
    # Functional holes
    # --------------------------------------------------------

    y_extent = (
        max(
            abs(y_pin),
            abs(y_roller),
        )
        + T
        + 5.0
    )

    hole_length = (
        2.0
        * y_extent
    )

    # Pin-end plate hole
    pin_hole = Part.makeCylinder(
        spec.pin_diameter_mm / 2.0,
        hole_length,
        App.Vector(
            0.0,
            -y_extent,
            0.0,
        ),
        App.Vector(
            0.0,
            1.0,
            0.0,
        ),
    )

    # Roller/bushing-end plate hole
    bushing_hole = Part.makeCylinder(
        spec.bushing_outer_diameter_mm / 2.0,
        hole_length,
        App.Vector(
            P,
            -y_extent,
            0.0,
        ),
        App.Vector(
            0.0,
            1.0,
            0.0,
        ),
    )

    plate = plate.cut(
        pin_hole
    )

    plate = plate.cut(
        bushing_hole
    )

    if plate.isNull():
        raise RuntimeError(
            f"{side_name} plate became null after hole cuts."
        )

    # removeSplitter can occasionally be more fragile than the
    # original valid Boolean result, so accept it only when the
    # cleaned shape remains valid.
    try:

        cleaned = (
            plate.removeSplitter()
        )

        if (
            not cleaned.isNull()
            and cleaned.isValid()
        ):
            plate = cleaned

    except Exception:
        pass

    if not plate.isValid():
        raise RuntimeError(
            f"Invalid {side_name} offset plate after Boolean operations."
        )

    if len(plate.Solids) != 1:
        raise RuntimeError(
            f"{side_name} offset plate should contain one solid; "
            f"got {len(plate.Solids)}."
        )

    return plate


# ============================================================
# ROLLER
# ============================================================

def make_roller(
    source: Any,
    **overrides,
):

    spec = resolve_spec(
        source,
        **overrides,
    )

    P = spec.pitch_mm
    width = spec.roller_width_mm

    outer_radius = (
        spec.roller_diameter_mm
        / 2.0
    )

    bore_radius = (
        spec.bushing_outer_diameter_mm
        / 2.0
        + 0.02
    )

    if bore_radius >= outer_radius:
        raise ValueError(
            "Roller bore radius is not smaller than roller radius."
        )

    outer = Part.makeCylinder(
        outer_radius,
        width,
        App.Vector(
            P,
            -width / 2.0,
            0.0,
        ),
        App.Vector(
            0.0,
            1.0,
            0.0,
        ),
    )

    bore = Part.makeCylinder(
        bore_radius,
        width + 2.0,
        App.Vector(
            P,
            -width / 2.0 - 1.0,
            0.0,
        ),
        App.Vector(
            0.0,
            1.0,
            0.0,
        ),
    )

    roller = outer.cut(
        bore
    )

    if roller.isNull() or not roller.isValid():
        raise RuntimeError(
            "Invalid roller."
        )

    return roller


# ============================================================
# BUSHING
# ============================================================

def make_bushing(
    source: Any,
    **overrides,
):

    spec = resolve_spec(
        source,
        **overrides,
    )

    P = spec.pitch_mm
    T = spec.plate_thickness_mm

    length = (
        spec.roller_width_mm
        + 2.0 * T
    )

    outer_radius = (
        spec.bushing_outer_diameter_mm
        / 2.0
    )

    inner_radius = (
        spec.bushing_inner_diameter_mm
        / 2.0
    )

    if inner_radius >= outer_radius:
        raise ValueError(
            "Bushing inner radius is not smaller than outer radius."
        )

    outer = Part.makeCylinder(
        outer_radius,
        length,
        App.Vector(
            P,
            -length / 2.0,
            0.0,
        ),
        App.Vector(
            0.0,
            1.0,
            0.0,
        ),
    )

    bore = Part.makeCylinder(
        inner_radius,
        length + 2.0,
        App.Vector(
            P,
            -length / 2.0 - 1.0,
            0.0,
        ),
        App.Vector(
            0.0,
            1.0,
            0.0,
        ),
    )

    bushing = outer.cut(
        bore
    )

    if bushing.isNull() or not bushing.isValid():
        raise RuntimeError(
            "Invalid bushing."
        )

    return bushing


# ============================================================
# CONNECTING PIN
# ============================================================

def make_connecting_pin(
    source: Any,
    **overrides,
):

    spec = resolve_spec(
        source,
        **overrides,
    )

    _, wide = (
        functional_plate_spacing(
            spec
        )
    )

    T = (
        spec.plate_thickness_mm
    )

    outer_plate_width = (
        wide
        + 2.0 * T
    )

    projection = (
        spec.pin_projection_mm
    )

    shaft_length = (
        outer_plate_width
        + 2.0 * projection
    )

    shaft_start_y = (
        -shaft_length / 2.0
    )

    shaft = Part.makeCylinder(
        spec.pin_diameter_mm / 2.0,
        shaft_length,
        App.Vector(
            0.0,
            shaft_start_y,
            0.0,
        ),
        App.Vector(
            0.0,
            1.0,
            0.0,
        ),
    )

    head_t = (
        spec.pin_head_thickness_mm
    )

    head = Part.makeCylinder(
        spec.pin_head_diameter_mm / 2.0,
        head_t,
        App.Vector(
            0.0,
            shaft_start_y - head_t,
            0.0,
        ),
        App.Vector(
            0.0,
            1.0,
            0.0,
        ),
    )

    pin = shaft.fuse(
        head
    )

    try:

        cleaned = (
            pin.removeSplitter()
        )

        if (
            not cleaned.isNull()
            and cleaned.isValid()
        ):
            pin = cleaned

    except Exception:
        pass

    if pin.isNull() or not pin.isValid():
        raise RuntimeError(
            "Invalid connecting pin."
        )

    return pin


# ============================================================
# COMPLETE OFFSET LINK
# ============================================================

def build_offset_link_shapes(
    source: Any,
    **overrides,
):

    spec = resolve_spec(
        source,
        **overrides,
    )

    shapes = {

        "OffsetPlateLeft":
            make_offset_plate(
                spec,
                "left",
            ),

        "OffsetPlateRight":
            make_offset_plate(
                spec,
                "right",
            ),

        "Roller":
            make_roller(
                spec,
            ),

        "Bushing":
            make_bushing(
                spec,
            ),

        "ConnectingPin":
            make_connecting_pin(
                spec,
            ),
    }

    for name, shape in shapes.items():

        if shape.isNull():
            raise RuntimeError(
                f"{name} is null."
            )

        if not shape.isValid():
            raise RuntimeError(
                f"{name} is invalid."
            )

    return shapes


def create_offset_link_shape(
    source: Any,
    **overrides,
):

    shapes = (
        build_offset_link_shapes(
            source,
            **overrides,
        )
    )

    compound = Part.makeCompound(
        list(
            shapes.values()
        )
    )

    if compound.isNull():
        raise RuntimeError(
            "OffsetLink compound is null."
        )

    return compound


# ============================================================
# PUBLIC CREATION FUNCTION
# ============================================================

def create_offset_link(
    *args,
    doc=None,
    chain_spec=None,
    name="OffsetLink",
    label=None,
    **overrides,
):
    """
    Supported forms:

        create_offset_link(chain_spec)
            -> returns Part compound

        create_offset_link(doc, chain_spec)
            -> returns Part::Feature

        create_offset_link(
            chain_spec,
            doc=doc
        )
            -> returns Part::Feature
    """

    if len(args) > 2:
        raise TypeError(
            "create_offset_link accepts at most two positional arguments."
        )

    if len(args) == 1:

        if hasattr(
            args[0],
            "addObject",
        ):
            doc = args[0]

        else:
            chain_spec = args[0]

    elif len(args) == 2:

        if hasattr(
            args[0],
            "addObject",
        ):
            doc = args[0]
            chain_spec = args[1]

        else:
            chain_spec = args[0]
            doc = args[1]

    if chain_spec is None:
        raise TypeError(
            "No chain specification supplied."
        )

    spec = resolve_spec(
        chain_spec,
        **overrides,
    )

    shape = (
        create_offset_link_shape(
            spec
        )
    )

    if doc is None:
        return shape

    obj = doc.addObject(
        "Part::Feature",
        name,
    )

    obj.Label = (
        label
        if label is not None
        else name
    )

    obj.Shape = shape

    obj.addProperty(
        "App::PropertyLength",
        "Pitch",
        "OffsetLink",
    )
    obj.Pitch = spec.pitch_mm

    obj.addProperty(
        "App::PropertyString",
        "JointAType",
        "Interface",
    )
    obj.JointAType = "ConnectingPin"

    obj.addProperty(
        "App::PropertyString",
        "JointBType",
        "Interface",
    )
    obj.JointBType = "RollerBushing"

    obj.addProperty(
        "App::PropertyString",
        "ReferencePlane",
        "Interface",
    )
    obj.ReferencePlane = "Chain center plane: Y=0"

    obj.addProperty(
        "App::PropertyString",
        "PlateGeometry",
        "Documentation",
    )
    obj.PlateGeometry = (
        "Circular end lobes + tangent concave relief arcs; "
        "bent web generated from planar Y-Z loft sections"
    )

    doc.recompute()

    return obj


# ============================================================
# REPORT / VALIDATION
# ============================================================

def offset_link_report(
    source: Any,
    **overrides,
):

    spec = resolve_spec(
        source,
        **overrides,
    )

    g = (
        reference_profile_geometry(
            spec
        )
    )

    narrow, wide = (
        functional_plate_spacing(
            spec
        )
    )

    T = spec.plate_thickness_mm

    y_pin_abs = (
        wide / 2.0
        + T / 2.0
    )

    y_roller_abs = (
        narrow / 2.0
        + T / 2.0
    )

    return {
        "pitch_mm":
            spec.pitch_mm,

        "plate_thickness_mm":
            T,

        "roller_diameter_mm":
            spec.roller_diameter_mm,

        "roller_width_mm":
            spec.roller_width_mm,

        "pin_diameter_mm":
            spec.pin_diameter_mm,

        "end_radius_mm":
            spec.plate_end_radius_mm,

        "relief_radius_mm":
            spec.plate_relief_radius_mm,

        "waist_half_height_mm":
            g["waist_half_height"],

        "waist_total_height_mm":
            g["waist_total_height"],

        "bend_start_x_mm":
            spec.bend_start_ratio
            * spec.pitch_mm,

        "bend_end_x_mm":
            spec.bend_end_ratio
            * spec.pitch_mm,

        "narrow_spacing_mm":
            narrow,

        "wide_spacing_mm":
            wide,

        "plate_center_shift_mm":
            abs(
                y_pin_abs
                - y_roller_abs
            ),

        "pin_tangent_x_mm":
            g["pin_tangent_x"],

        "roller_tangent_x_mm":
            g["roller_tangent_x"],
    }


def print_offset_link_report(
    source: Any,
    **overrides,
):

    r = offset_link_report(
        source,
        **overrides,
    )

    print()
    print("=" * 68)
    print("OFFSET LINK GEOMETRY")
    print("=" * 68)

    labels = [
        ("P", "pitch_mm"),
        ("Plate thickness", "plate_thickness_mm"),
        ("Roller diameter", "roller_diameter_mm"),
        ("Roller width", "roller_width_mm"),
        ("Pin diameter", "pin_diameter_mm"),
        ("End radius", "end_radius_mm"),
        ("Relief radius", "relief_radius_mm"),
        ("Waist half-height", "waist_half_height_mm"),
        ("Waist total height", "waist_total_height_mm"),
        ("Pin tangent X", "pin_tangent_x_mm"),
        ("Roller tangent X", "roller_tangent_x_mm"),
        ("Bend start", "bend_start_x_mm"),
        ("Bend end", "bend_end_x_mm"),
        ("Narrow spacing", "narrow_spacing_mm"),
        ("Wide spacing", "wide_spacing_mm"),
        ("Plate center shift", "plate_center_shift_mm"),
    ]

    for label, key in labels:

        print(
            f"{label:22s} = "
            f"{r[key]:.4f} mm"
        )

    print("=" * 68)


def validate_offset_link(
    source: Any,
    **overrides,
):

    spec = resolve_spec(
        source,
        **overrides,
    )

    shapes = (
        build_offset_link_shapes(
            spec
        )
    )

    compound = Part.makeCompound(
        list(
            shapes.values()
        )
    )

    return {
        "joint_distance_mm":
            spec.pitch_mm,

        "component_count":
            len(shapes),

        "components":
            list(shapes.keys()),

        "all_components_valid":
            all(
                shape.isValid()
                for shape in shapes.values()
            ),

        "component_solids":
            {
                name: len(shape.Solids)
                for name, shape
                in shapes.items()
            },

        "compound_valid":
            compound.isValid(),

        "compound_null":
            compound.isNull(),
    }


# ============================================================
# PREVIEW
# ============================================================

def create_offset_link_preview(
    source: Any,
    document_name="OffsetLinkPreview",
    **overrides,
):

    spec = resolve_spec(
        source,
        **overrides,
    )

    if document_name in App.listDocuments():

        App.closeDocument(
            document_name
        )

    doc = App.newDocument(
        document_name
    )

    shapes = (
        build_offset_link_shapes(
            spec
        )
    )

    objects = {}

    for name, shape in shapes.items():

        obj = doc.addObject(
            "Part::Feature",
            name,
        )

        obj.Label = name
        obj.Shape = shape

        objects[name] = obj

    doc.recompute()

    try:

        import FreeCADGui as Gui

        Gui.activeDocument().activeView().viewAxonometric()

        Gui.activeDocument().activeView().fitAll()

    except Exception:
        pass

    return (
        doc,
        objects,
    )


# ============================================================
# ASA 80 REFERENCE
# ============================================================

def asa80_reference_spec():

    return OffsetLinkSpec(

        pitch_mm=25.40,

        roller_diameter_mm=15.88,

        inner_width_mm=15.75,

        pin_diameter_mm=7.92,

        plate_thickness_mm=3.20,

        roller_width_mm=17.02,

        plate_end_radius_mm=10.40,

        plate_relief_radius_mm=12.00,

        bend_start_ratio=(
            8.92 / 25.40
        ),

        bend_end_ratio=(
            14.90 / 25.40
        ),

        web_sections=32,

    ).resolved()


def preview_asa80_reference():

    spec = (
        asa80_reference_spec()
    )

    print_offset_link_report(
        spec
    )

    validation = None

    try:
        validation = (
            validate_offset_link(
                spec
            )
        )

        print()
        print("Validation:")
        print(validation)

    except Exception as error:

        print()
        print(
            "Validation failed before preview:"
        )

        print(
            repr(error)
        )

        raise

    return create_offset_link_preview(

        spec,

        document_name=
            "ASA80_OffsetLink_Reference",
    )
