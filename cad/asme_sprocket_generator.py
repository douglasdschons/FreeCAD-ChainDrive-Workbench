import math
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Part


INCH_TO_MM = 25.4

# ASME B29.1M Table 9B - maximum flange thickness for single sprockets, mm
ASME_SINGLE_FLANGE_WIDTH_MM = {
    35: 4.29,
    40: 7.21,
    50: 8.71,
    60: 11.66,
    80: 14.60,
    100: 17.58,
    120: 23.47,
    140: 23.47,
    160: 29.36,
}


# ============================================================
# 2D GEOMETRY HELPERS
# Local coordinates:
#   u = tangential coordinate
#   v = radial coordinate
#
# FreeCAD mapping:
#   X = v
#   Y = sprocket axis
#   Z = u
# ============================================================

def distance_2d(p1, p2):
    return math.hypot(
        p2[0] - p1[0],
        p2[1] - p1[1],
    )


def mirror_uv(point):
    return (
        -point[0],
        point[1],
    )


def uv_to_vector(point, y_value):
    u, v = point

    return App.Vector(
        v,
        y_value,
        u,
    )


def line_circle_intersections(
    line_point,
    line_direction,
    circle_center,
    radius,
):
    px, py = line_point
    dx, dy = line_direction
    cx, cy = circle_center

    norm = math.hypot(dx, dy)

    if norm <= 0:
        raise ValueError(
            "Zero line direction."
        )

    dx /= norm
    dy /= norm

    ox = px - cx
    oy = py - cy

    b = 2.0 * (
        ox * dx
        + oy * dy
    )

    c = (
        ox * ox
        + oy * oy
        - radius * radius
    )

    discriminant = (
        b * b
        - 4.0 * c
    )

    if discriminant < -1e-10:
        return []

    discriminant = max(
        0.0,
        discriminant,
    )

    root = math.sqrt(
        discriminant
    )

    t1 = (
        -b + root
    ) / 2.0

    t2 = (
        -b - root
    ) / 2.0

    return [
        (
            (
                px + t1 * dx,
                py + t1 * dy,
            ),
            t1,
        ),
        (
            (
                px + t2 * dx,
                py + t2 * dy,
            ),
            t2,
        ),
    ]


def circle_centers_from_points_radius(
    p1,
    p2,
    radius,
):
    x1, y1 = p1
    x2, y2 = p2

    dx = x2 - x1
    dy = y2 - y1

    chord = math.hypot(
        dx,
        dy,
    )

    if chord <= 1e-12:
        raise ValueError(
            "Coincident points cannot define the arc center."
        )

    if chord > (
        2.0 * radius
        + 1e-10
    ):
        raise ValueError(
            "Requested arc radius is smaller than half the chord."
        )

    mx = (
        x1 + x2
    ) / 2.0

    my = (
        y1 + y2
    ) / 2.0

    h = math.sqrt(
        max(
            0.0,
            radius * radius
            - (chord / 2.0) ** 2,
        )
    )

    nx = (
        -dy / chord
    )

    ny = (
        dx / chord
    )

    return [
        (
            mx + h * nx,
            my + h * ny,
        ),
        (
            mx - h * nx,
            my - h * ny,
        ),
    ]


def short_arc_midpoint(
    p1,
    p2,
    center,
):
    cx, cy = center

    angle_1 = math.atan2(
        p1[1] - cy,
        p1[0] - cx,
    )

    angle_2 = math.atan2(
        p2[1] - cy,
        p2[0] - cx,
    )

    delta = (
        (
            angle_2
            - angle_1
            + math.pi
        )
        % (
            2.0 * math.pi
        )
        - math.pi
    )

    middle_angle = (
        angle_1
        + delta / 2.0
    )

    radius = distance_2d(
        center,
        p1,
    )

    return (
        cx
        + radius
        * math.cos(
            middle_angle
        ),
        cy
        + radius
        * math.sin(
            middle_angle
        ),
    )


def make_short_arc(
    p1,
    p2,
    center,
    y_value,
):
    midpoint = short_arc_midpoint(
        p1,
        p2,
        center,
    )

    return Part.Arc(
        uv_to_vector(
            p1,
            y_value,
        ),
        uv_to_vector(
            midpoint,
            y_value,
        ),
        uv_to_vector(
            p2,
            y_value,
        ),
    ).toShape()


# ============================================================
# ASME B29.1 / GEARS TOOTH CONSTRUCTION
# ============================================================

def calculate_asme_tooth_geometry(
    pitch_mm,
    roller_diameter_mm,
    teeth,
):
    P = float(
        pitch_mm
    )

    Dr = float(
        roller_diameter_mm
    )

    N = int(
        teeth
    )

    if (
        P <= 0
        or Dr <= 0
        or N < 5
    ):
        raise ValueError(
            "Invalid pitch, roller diameter, or tooth count."
        )


    # --------------------------------------------------------
    # Fundamental pitch geometry
    # --------------------------------------------------------

    half_pitch_angle = (
        math.pi / N
    )

    pitch_diameter = (
        P
        / math.sin(
            half_pitch_angle
        )
    )

    pitch_radius = (
        pitch_diameter
        / 2.0
    )


    # --------------------------------------------------------
    # ASME seating curve
    #
    # Ds = 1.005 Dr + 0.003 in
    # R  = Ds / 2
    # --------------------------------------------------------

    seating_diameter = (
        1.005
        * Dr
        + 0.003
        * INCH_TO_MM
    )

    seating_radius = (
        seating_diameter
        / 2.0
    )


    # --------------------------------------------------------
    # Construction angles
    # --------------------------------------------------------

    A_deg = (
        35.0
        + 60.0 / N
    )

    B_deg = (
        18.0
        - 56.0 / N
    )

    A = math.radians(
        A_deg
    )

    B = math.radians(
        B_deg
    )


    # --------------------------------------------------------
    # Auxiliary dimensions
    # --------------------------------------------------------

    ac = (
        0.8
        * Dr
    )

    M = (
        ac
        * math.cos(
            A
        )
    )

    T = (
        ac
        * math.sin(
            A
        )
    )

    E = (
        1.3025
        * Dr
        + 0.0015
        * INCH_TO_MM
    )

    yz_length = (
        Dr
        * (
            1.4
            * math.sin(
                math.radians(
                    17.0
                    - 64.0 / N
                )
            )
            -
            0.8
            * math.sin(
                math.radians(
                    18.0
                    - 56.0 / N
                )
            )
        )
    )

    ab = (
        1.4
        * Dr
    )

    W = (
        ab
        * math.cos(
            half_pitch_angle
        )
    )

    V = (
        ab
        * math.sin(
            half_pitch_angle
        )
    )

    F = (
        Dr
        * (
            0.8
            * math.cos(
                math.radians(
                    18.0
                    - 56.0 / N
                )
            )
            +
            1.4
            * math.cos(
                math.radians(
                    17.0
                    - 64.0 / N
                )
            )
            -
            1.3025
        )
        -
        0.0015
        * INCH_TO_MM
    )

    H_squared = (
        F * F
        -
        (
            1.4
            * Dr
            - P / 2.0
        ) ** 2
    )

    if H_squared <= 0:
        raise ValueError(
            f"Invalid ASME geometry: H²={H_squared}."
        )

    H = math.sqrt(
        H_squared
    )

    S = (
        P
        / 2.0
        * math.cos(
            half_pitch_angle
        )
        +
        H
        * math.sin(
            half_pitch_angle
        )
    )


    # ========================================================
    # GEARS CAD CONSTRUCTION POINTS
    # ========================================================

    # Step 4:
    # point a = top point of pitch circle
    a = (
        0.0,
        pitch_radius,
    )


    # Step 7:
    # offsets M and T locate point c
    c = (
        M,
        pitch_radius
        + T,
    )


    # Step 8:
    # line cx at angle A.
    # x is obtained from the ACTUAL intersection of cx
    # with the seating circle centered at a.
    cx_direction = (
        -math.cos(
            A
        ),
        -math.sin(
            A
        ),
    )

    x_intersections = (
        line_circle_intersections(
            c,
            cx_direction,
            a,
            seating_radius,
        )
    )

    positive_x_intersections = [
        item
        for item
        in x_intersections
        if item[1] >= -1e-10
    ]

    if not positive_x_intersections:
        raise ValueError(
            "Line cx does not intersect the seating circle."
        )

    # The GEARS profile uses the farther intersection.
    x, cx_distance = max(
        positive_x_intersections,
        key=lambda item: item[1],
    )


    # Step 9:
    # line cy has length E and angle B from cx
    cy_angle = (
        A - B
    )

    cy_unit = (
        -math.cos(
            cy_angle
        ),
        -math.sin(
            cy_angle
        ),
    )

    y = (
        c[0]
        + E
        * cy_unit[0],
        c[1]
        + E
        * cy_unit[1],
    )


    # Step 10:
    # arc xy has radius E.
    #
    # Do NOT hard-code c as the center.
    # Solve both possible centers geometrically and select
    # the solution belonging to the GEARS construction.
    xy_centers = (
        circle_centers_from_points_radius(
            x,
            y,
            E,
        )
    )

    xy_center = min(
        xy_centers,
        key=lambda point:
            distance_2d(
                point,
                c,
            ),
    )


    # Steps 12-13:
    # point b via W and V offsets
    b = (
        -W,
        pitch_radius
        - V,
    )


    # Step 11:
    # yz is perpendicular to cy.
    #
    # There are two mathematical possibilities.
    # Choose the one that satisfies tangency with the
    # circle centered at b with radius F.
    perpendicular_1 = (
        -cy_unit[1],
        cy_unit[0],
    )

    perpendicular_2 = (
        cy_unit[1],
        -cy_unit[0],
    )

    z_candidates = [
        (
            y[0]
            + yz_length
            * perpendicular_1[0],
            y[1]
            + yz_length
            * perpendicular_1[1],
        ),
        (
            y[0]
            + yz_length
            * perpendicular_2[0],
            y[1]
            + yz_length
            * perpendicular_2[1],
        ),
    ]

    z = min(
        z_candidates,
        key=lambda point:
            abs(
                distance_2d(
                    point,
                    b,
                )
                - F
            ),
    )


    # Step 14:
    # theoretical tooth tip:
    # intersection of the F circle with a radial line
    # at 180/N from the tooth-space centerline.
    tip_direction = (
        -math.sin(
            half_pitch_angle
        ),
        math.cos(
            half_pitch_angle
        ),
    )

    tip_intersections = (
        line_circle_intersections(
            (
                0.0,
                0.0,
            ),
            tip_direction,
            b,
            F,
        )
    )

    positive_tip_intersections = [
        (
            point,
            parameter,
        )
        for point, parameter
        in tip_intersections
        if parameter > 0
    ]

    if not positive_tip_intersections:
        raise ValueError(
            "Cannot locate theoretical tooth tip."
        )

    tooth_tip, tooth_tip_radius = max(
        positive_tip_intersections,
        key=lambda item: item[1],
    )


    # Point L:
    # deepest point of the seating curve
    L = (
        0.0,
        pitch_radius
        - seating_radius,
    )


    # ========================================================
    # GEOMETRIC RESIDUALS
    # ========================================================

    return {
        "P":
            P,

        "Dr":
            Dr,

        "N":
            N,

        "PD":
            pitch_diameter,

        "Rp":
            pitch_radius,

        "Ds":
            seating_diameter,

        "R":
            seating_radius,

        "A_deg":
            A_deg,

        "B_deg":
            B_deg,

        "ac":
            ac,

        "M":
            M,

        "T":
            T,

        "E":
            E,

        "yz":
            yz_length,

        "ab":
            ab,

        "W":
            W,

        "V":
            V,

        "F":
            F,

        "H":
            H,

        "S":
            S,

        "a":
            a,

        "b":
            b,

        "c":
            c,

        "x":
            x,

        "y":
            y,

        "z":
            z,

        "L":
            L,

        "xy_center":
            xy_center,

        "tooth_tip":
            tooth_tip,

        "tooth_tip_radius":
            tooth_tip_radius,

        "cx_distance":
            cx_distance,

        "xy_center_to_c_error":
            distance_2d(
                xy_center,
                c,
            ),

        "tangency_z_error":
            abs(
                distance_2d(
                    z,
                    b,
                )
                - F
            ),

        "seating_x_error":
            abs(
                distance_2d(
                    x,
                    a,
                )
                - seating_radius
            ),

        "arc_xy_x_error":
            abs(
                distance_2d(
                    x,
                    xy_center,
                )
                - E
            ),

        "arc_xy_y_error":
            abs(
                distance_2d(
                    y,
                    xy_center,
                )
                - E
            ),
    }


# ============================================================
# CORRECTED TOOTH-SPACE CUTTER
# ============================================================

def create_tooth_space_cutter(
    geometry,
    flange_width_mm,
    outside_diameter_mm,
):
    flange_width = float(
        flange_width_mm
    )

    outside_radius = (
        float(
            outside_diameter_mm
        )
        / 2.0
    )


    # --------------------------------------------------------
    # Left half of GEARS profile
    # --------------------------------------------------------

    a = geometry["a"]
    b = geometry["b"]

    x = geometry["x"]
    y = geometry["y"]
    z = geometry["z"]

    L = geometry["L"]

    xy_center = (
        geometry[
            "xy_center"
        ]
    )

    tooth_tip_left = (
        geometry[
            "tooth_tip"
        ]
    )


    # --------------------------------------------------------
    # Mirror around tooth-space radial centerline
    # --------------------------------------------------------

    tooth_tip_right = (
        mirror_uv(
            tooth_tip_left
        )
    )

    z_right = (
        mirror_uv(
            z
        )
    )

    y_right = (
        mirror_uv(
            y
        )
    )

    x_right = (
        mirror_uv(
            x
        )
    )

    b_right = (
        mirror_uv(
            b
        )
    )

    xy_center_right = (
        mirror_uv(
            xy_center
        )
    )


    # --------------------------------------------------------
    # Cutter spans slightly beyond both flange faces
    # --------------------------------------------------------

    margin_y = 1.0

    y_plane = (
        -flange_width
        / 2.0
        - margin_y
    )

    extrusion_length = (
        flange_width
        + 2.0
        * margin_y
    )


    # ========================================================
    # PROFILE:
    #
    # theoretical tip
    #   -> F arc
    #   -> z
    #   -> line yz
    #   -> y
    #   -> E arc xy
    #   -> x
    #   -> seating arc R
    #   -> L
    #
    # and mirror.
    # ========================================================

    edges = [

        # F topping curve:
        make_short_arc(
            tooth_tip_left,
            z,
            b,
            y_plane,
        ),

        # yz:
        Part.makeLine(
            uv_to_vector(
                z,
                y_plane,
            ),
            uv_to_vector(
                y,
                y_plane,
            ),
        ),

        # xy:
        make_short_arc(
            y,
            x,
            xy_center,
            y_plane,
        ),

        # seating curve:
        make_short_arc(
            x,
            L,
            a,
            y_plane,
        ),

        # mirrored seating curve:
        make_short_arc(
            L,
            x_right,
            a,
            y_plane,
        ),

        # mirrored xy:
        make_short_arc(
            x_right,
            y_right,
            xy_center_right,
            y_plane,
        ),

        # mirrored yz:
        Part.makeLine(
            uv_to_vector(
                y_right,
                y_plane,
            ),
            uv_to_vector(
                z_right,
                y_plane,
            ),
        ),

        # mirrored F curve:
        make_short_arc(
            z_right,
            tooth_tip_right,
            b_right,
            y_plane,
        ),
    ]


    # ========================================================
    # CLOSE CUTTER OUTSIDE THE SPROCKET
    # ========================================================

    half_pitch_angle = (
        math.pi
        / geometry["N"]
    )

    far_radius = max(
        outside_radius
        + 5.0,
        geometry[
            "tooth_tip_radius"
        ]
        + 2.0,
    )

    far_right = (
        far_radius
        * math.sin(
            half_pitch_angle
        ),
        far_radius
        * math.cos(
            half_pitch_angle
        ),
    )

    far_middle = (
        0.0,
        far_radius,
    )

    far_left = (
        -far_right[0],
        far_right[1],
    )


    edges.extend([
        Part.makeLine(
            uv_to_vector(
                tooth_tip_right,
                y_plane,
            ),
            uv_to_vector(
                far_right,
                y_plane,
            ),
        ),

        Part.Arc(
            uv_to_vector(
                far_right,
                y_plane,
            ),
            uv_to_vector(
                far_middle,
                y_plane,
            ),
            uv_to_vector(
                far_left,
                y_plane,
            ),
        ).toShape(),

        Part.makeLine(
            uv_to_vector(
                far_left,
                y_plane,
            ),
            uv_to_vector(
                tooth_tip_left,
                y_plane,
            ),
        ),
    ])


    wire = Part.Wire(
        edges
    )

    if not wire.isClosed():
        raise RuntimeError(
            "Tooth-space cutter wire is not closed."
        )


    face = Part.Face(
        wire
    )


    cutter = face.extrude(
        App.Vector(
            0.0,
            extrusion_length,
            0.0,
        )
    )


    if cutter.isNull():
        raise RuntimeError(
            "Tooth-space cutter could not be created."
        )


    return cutter


# ============================================================
# AXIAL BODY - ASME SECTION A + ENCO COMMERCIAL BODY
# ============================================================

def create_revolved_body(
    pitch_mm,
    inner_width_mm,
    flange_width_mm,
    outside_diameter_mm,
    hub_diameter_mm,
    total_length_mm,
    bore_diameter_mm,
):
    P = float(
        pitch_mm
    )

    inner_width = float(
        inner_width_mm
    )

    flange_width = float(
        flange_width_mm
    )

    outside_radius = (
        float(
            outside_diameter_mm
        )
        / 2.0
    )

    hub_radius = (
        float(
            hub_diameter_mm
        )
        / 2.0
    )

    bore_radius = (
        float(
            bore_diameter_mm
        )
        / 2.0
    )

    total_length = float(
        total_length_mm
    )


    # ASME tooth-section chamfer
    h = (
        0.5
        * P
    )

    g = min(
        P / 8.0,
        inner_width / 3.0,
    )


    half_flange = (
        flange_width
        / 2.0
    )

    top_half_width = (
        half_flange
        - g
    )

    chamfer_start_radius = (
        outside_radius
        - h
    )


    if top_half_width <= 0:
        raise ValueError(
            "ASME chamfer consumes the full flange width."
        )


    if (
        chamfer_start_radius
        <= hub_radius
    ):
        raise ValueError(
            "ASME Section A chamfer reaches the hub. "
            "This sprocket requires a manufacturer-specific axial profile."
        )


    if (
        bore_radius <= 0
        or bore_radius >= hub_radius
    ):
        raise ValueError(
            "Invalid bore/hub dimensions."
        )


    # Tooth track is centered on Y = 0.
    y_left = (
        -half_flange
    )

    y_right = (
        half_flange
    )


    # ENCO L is measured from the left sprocket face
    # to the end of the unilateral hub.
    y_hub_end = (
        y_left
        + total_length
    )


    points = [

        App.Vector(
            bore_radius,
            y_left,
            0,
        ),

        App.Vector(
            chamfer_start_radius,
            y_left,
            0,
        ),

        App.Vector(
            outside_radius,
            -top_half_width,
            0,
        ),

        App.Vector(
            outside_radius,
            top_half_width,
            0,
        ),

        App.Vector(
            chamfer_start_radius,
            y_right,
            0,
        ),

        App.Vector(
            hub_radius,
            y_right,
            0,
        ),

        App.Vector(
            hub_radius,
            y_hub_end,
            0,
        ),

        App.Vector(
            bore_radius,
            y_hub_end,
            0,
        ),

        App.Vector(
            bore_radius,
            y_left,
            0,
        ),
    ]


    wire = Part.makePolygon(
        points
    )

    face = Part.Face(
        wire
    )


    return face.revolve(
        App.Vector(
            0,
            0,
            0,
        ),
        App.Vector(
            0,
            1,
            0,
        ),
        360.0,
    )


# ============================================================
# GENERATE ONE SPROCKET
# ============================================================

def _add_length_property(
    obj,
    name,
    value,
    group,
):
    obj.addProperty(
        "App::PropertyLength",
        name,
        group,
    )

    setattr(
        obj,
        name,
        float(
            value
        ),
    )


def create_sprocket(
    doc,
    chain_data,
    sprocket_data,
    bore_diameter_mm=None,
):
    asa = int(
        sprocket_data[
            "asa"
        ]
    )

    teeth = int(
        sprocket_data[
            "teeth_z"
        ]
    )


    # Chain data
    P = float(
        chain_data[
            "pitch_P_mm"
        ]
    )

    Dr = float(
        chain_data[
            "roller_diameter_R_mm"
        ]
    )

    inner_width = float(
        chain_data[
            "inner_width_E_mm"
        ]
    )


    # ENCO commercial data
    outside_diameter = float(
        sprocket_data[
            "outside_diameter_mm"
        ]
    )

    hub_diameter = float(
        sprocket_data[
            "hub_diameter_mm"
        ]
    )

    total_length = float(
        sprocket_data[
            "total_length_mm"
        ]
    )

    pilot_bore = float(
        sprocket_data[
            "pilot_bore_mm"
        ]
    )

    maximum_bore = float(
        sprocket_data[
            "maximum_bore_mm"
        ]
    )


    bore = (
        pilot_bore
        if bore_diameter_mm is None
        else float(
            bore_diameter_mm
        )
    )


    if not (
        pilot_bore
        <= bore
        <= maximum_bore
    ):
        raise ValueError(
            f"Bore must be between "
            f"{pilot_bore:.2f} and "
            f"{maximum_bore:.2f} mm."
        )


    if (
        asa
        not in ASME_SINGLE_FLANGE_WIDTH_MM
    ):
        raise KeyError(
            f"No ASME single-sprocket flange width "
            f"configured for ASA {asa}."
        )


    flange_width = (
        ASME_SINGLE_FLANGE_WIDTH_MM[
            asa
        ]
    )


    geometry = (
        calculate_asme_tooth_geometry(
            P,
            Dr,
            teeth,
        )
    )


    # ENCO DE is used as the actual CAD blank diameter.
    # It should normally be below the ASME pointed diameter.
    if (
        outside_diameter
        / 2.0
        >
        geometry[
            "tooth_tip_radius"
        ]
        + 1e-6
    ):
        raise ValueError(
            f"Catalog outside diameter "
            f"({outside_diameter:.3f} mm) exceeds "
            f"the theoretical pointed diameter "
            f"({2.0 * geometry['tooth_tip_radius']:.3f} mm)."
        )


    # --------------------------------------------------------
    # 1. Revolved body
    # --------------------------------------------------------

    sprocket_shape = (
        create_revolved_body(
            P,
            inner_width,
            flange_width,
            outside_diameter,
            hub_diameter,
            total_length,
            bore,
        )
    )


    # --------------------------------------------------------
    # 2. One corrected ASME/GEARS tooth-space cutter
    # --------------------------------------------------------

    base_cutter = (
        create_tooth_space_cutter(
            geometry,
            flange_width,
            outside_diameter,
        )
    )


    # --------------------------------------------------------
    # 3. Circular pattern
    # --------------------------------------------------------

    axis_y = App.Vector(
        0,
        1,
        0,
    )

    cutters = []


    for index in range(
        teeth
    ):
        cutter = (
            base_cutter.copy()
        )

        cutter.rotate(
            App.Vector(
                0,
                0,
                0,
            ),
            axis_y,
            index
            * 360.0
            / teeth,
        )

        cutters.append(
            cutter
        )


    # Try one compound Boolean first.
    # Fall back to sequential cuts if OCC rejects it.
    try:
        pattern_tool = (
            Part.makeCompound(
                cutters
            )
        )

        result = (
            sprocket_shape.cut(
                pattern_tool
            )
        )

        if result.isNull():
            raise RuntimeError(
                "Compound cut returned a null shape."
            )

        sprocket_shape = (
            result
        )

    except Exception:
        for cutter in cutters:
            sprocket_shape = (
                sprocket_shape.cut(
                    cutter
                )
            )


    try:
        sprocket_shape = (
            sprocket_shape.removeSplitter()
        )
    except Exception:
        pass


    if (
        sprocket_shape.isNull()
        or not sprocket_shape.isValid()
    ):
        raise RuntimeError(
            "Generated sprocket shape is invalid."
        )


    if (
        len(
            sprocket_shape.Solids
        )
        != 1
    ):
        raise RuntimeError(
            f"Expected one solid; got "
            f"{len(sprocket_shape.Solids)}."
        )


    # --------------------------------------------------------
    # FreeCAD object
    # --------------------------------------------------------

    sprocket = doc.addObject(
        "Part::Feature",
        "Sprocket",
    )

    sprocket.Label = (
        f"ENCO ASA {asa}-1 | "
        f"{teeth}T | "
        f"ASME B29.1"
    )

    sprocket.Shape = (
        sprocket_shape
    )


    sprocket.addProperty(
        "App::PropertyString",
        "Manufacturer",
        "Catalog",
    )

    sprocket.Manufacturer = (
        "ENCO"
    )


    sprocket.addProperty(
        "App::PropertyString",
        "CatalogReference",
        "Catalog",
    )

    sprocket.CatalogReference = str(
        sprocket_data[
            "reference"
        ]
    )


    sprocket.addProperty(
        "App::PropertyInteger",
        "ASA",
        "Chain",
    )

    sprocket.ASA = (
        asa
    )


    sprocket.addProperty(
        "App::PropertyInteger",
        "Teeth",
        "Geometry",
    )

    sprocket.Teeth = (
        teeth
    )


    dimensions = {
        "Pitch":
            P,

        "RollerDiameter":
            Dr,

        "PitchDiameter":
            geometry[
                "PD"
            ],

        "OutsideDiameter":
            outside_diameter,

        "SeatingDiameter":
            geometry[
                "Ds"
            ],

        "SeatingRadius":
            geometry[
                "R"
            ],

        "FlangeWidth":
            flange_width,

        "HubDiameter":
            hub_diameter,

        "TotalLength":
            total_length,

        "BoreDiameter":
            bore,

        "PilotBore":
            pilot_bore,

        "MaximumBore":
            maximum_bore,
    }


    for name, value in (
        dimensions.items()
    ):
        _add_length_property(
            sprocket,
            name,
            value,
            "Dimensions",
        )


    sprocket.addProperty(
        "App::PropertyString",
        "ProfileStandard",
        "Profile",
    )

    sprocket.ProfileStandard = (
        "ASME B29.1 theoretical tooth form / "
        "GEARS CAD construction"
    )


    sprocket.addProperty(
        "App::PropertyString",
        "ReferencePlane",
        "Interface",
    )

    sprocket.ReferencePlane = (
        "Y=0 is the center plane of the "
        "toothed flange / chain"
    )


    doc.recompute()


    return (
        sprocket,
        geometry,
    )


# ============================================================
# DOCUMENT / FILE GENERATION
# ============================================================

def _unique_document_name(
    base_name,
):
    name = (
        base_name
    )

    index = 1


    while (
        name
        in App.listDocuments()
    ):
        name = (
            f"{base_name}_"
            f"{index:02d}"
        )

        index += 1


    return (
        name
    )


def _unique_output_path(
    path,
):
    path = Path(
        path
    )


    if not path.exists():
        return (
            path
        )


    index = 1


    while True:
        candidate = (
            path.with_name(
                f"{path.stem}_"
                f"{index:02d}"
                f"{path.suffix}"
            )
        )

        if not candidate.exists():
            return (
                candidate
            )

        index += 1


def generate_sprocket_file(
    chain_data,
    sprocket_data,
    bore_diameter_mm,
    output_dir,
):
    asa = int(
        sprocket_data[
            "asa"
        ]
    )

    teeth = int(
        sprocket_data[
            "teeth_z"
        ]
    )

    bore = float(
        bore_diameter_mm
    )


    document_name = (
        _unique_document_name(
            f"ENCO_ASA"
            f"{asa}_"
            f"{teeth}T_ASME"
        )
    )


    doc = App.newDocument(
        document_name
    )


    try:
        sprocket, geometry = (
            create_sprocket(
                doc,
                chain_data,
                sprocket_data,
                bore,
            )
        )


        output_directory = Path(
            output_dir
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )


        bore_tag = (
            f"{bore:.2f}"
            .replace(
                ".",
                "p",
            )
        )


        output_path = (
            _unique_output_path(
                output_directory
                /
                (
                    f"ENCO_ASA"
                    f"{asa}_"
                    f"{teeth}T_"
                    f"B{bore_tag}_"
                    f"ASME.FCStd"
                )
            )
        )


        doc.saveAs(
            str(
                output_path
            )
        )


        if getattr(App, "GuiUp", False):
            Gui.activeDocument().activeView().viewAxonometric()
            Gui.activeDocument().activeView().fitAll()


        return (
            doc,
            sprocket,
            geometry,
            output_path,
        )


    except Exception:
        App.closeDocument(
            doc.Name
        )

        raise
