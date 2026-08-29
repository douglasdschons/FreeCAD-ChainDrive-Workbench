"""Exact rigid-link layout solver for an open two-sprocket chain drive.

The analytical pitch path is used only as the locus of roller centers.  Each
successive center is found by enforcing the real chord length ``|Pi+1-Pi|=P``.
The center distance is then corrected until N rigid pitch steps close exactly.
"""

from __future__ import annotations

from math import asin, atan2, cos, degrees, pi, sin, sqrt
from typing import Callable


Point2D = tuple[float, float]


def calculate_pitch_radius(pitch_mm: float, teeth: int) -> float:
    pitch_mm = float(pitch_mm)
    teeth = int(teeth)
    if pitch_mm <= 0.0:
        raise ValueError("Pitch must be positive.")
    if teeth < 3:
        raise ValueError("Number of sprocket teeth must be at least 3.")
    return pitch_mm / (2.0 * sin(pi / teeth))


def distance_2d(point_a: Point2D, point_b: Point2D) -> float:
    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    return sqrt(dx * dx + dy * dy)


def build_exact_pitch_path(
    pitch_mm: float,
    small_sprocket_teeth: int,
    large_sprocket_teeth: int,
    center_distance_mm: float,
) -> dict[str, object]:
    """Build the exact arcs and common external tangents of the pitch path."""
    r1 = calculate_pitch_radius(pitch_mm, small_sprocket_teeth)
    r2 = calculate_pitch_radius(pitch_mm, large_sprocket_teeth)
    center_distance_mm = float(center_distance_mm)
    radius_difference = r2 - r1

    if center_distance_mm <= abs(radius_difference):
        raise ValueError("Center distance must be greater than |r2-r1|.")

    sine_alpha = radius_difference / center_distance_mm
    cosine_alpha = sqrt(center_distance_mm**2 - radius_difference**2) / center_distance_mm
    alpha = asin(sine_alpha)

    small_center = (0.0, 0.0)
    large_center = (center_distance_mm, 0.0)
    upper_small = (-r1 * sine_alpha, r1 * cosine_alpha)
    lower_small = (-r1 * sine_alpha, -r1 * cosine_alpha)
    lower_large = (
        center_distance_mm - r2 * sine_alpha,
        -r2 * cosine_alpha,
    )
    upper_large = (
        center_distance_mm - r2 * sine_alpha,
        r2 * cosine_alpha,
    )

    segments: list[dict[str, object]] = []

    def add_ccw_arc(
        center: Point2D,
        radius: float,
        start_point: Point2D,
        end_point: Point2D,
        name: str,
    ) -> None:
        start_angle = atan2(start_point[1] - center[1], start_point[0] - center[0])
        end_angle = atan2(end_point[1] - center[1], end_point[0] - center[0])
        while end_angle < start_angle:
            end_angle += 2.0 * pi
        delta_angle = end_angle - start_angle
        segments.append(
            {
                "name": name,
                "type": "arc",
                "length": radius * delta_angle,
                "center": center,
                "radius": radius,
                "start_angle": start_angle,
                "delta_angle": delta_angle,
            }
        )

    def add_line(start_point: Point2D, end_point: Point2D, name: str) -> None:
        segments.append(
            {
                "name": name,
                "type": "line",
                "length": distance_2d(start_point, end_point),
                "start": start_point,
                "end": end_point,
            }
        )

    add_ccw_arc(small_center, r1, upper_small, lower_small, "small_arc")
    add_line(lower_small, lower_large, "lower_span")
    add_ccw_arc(large_center, r2, lower_large, upper_large, "large_arc")
    add_line(upper_large, upper_small, "upper_span")

    cumulative = [0.0]
    for segment in segments:
        cumulative.append(cumulative[-1] + float(segment["length"]))
    total_length = cumulative[-1]

    def point_at(path_coordinate_mm: float) -> Point2D:
        s = path_coordinate_mm % total_length
        for index, segment in enumerate(segments):
            segment_start = cumulative[index]
            segment_end = cumulative[index + 1]
            if s <= segment_end + 1.0e-12:
                local_s = s - segment_start
                if segment["type"] == "line":
                    x0, y0 = segment["start"]  # type: ignore[misc]
                    x1, y1 = segment["end"]  # type: ignore[misc]
                    length = float(segment["length"])
                    if length == 0.0:
                        return (x0, y0)
                    fraction = local_s / length
                    return (x0 + fraction * (x1 - x0), y0 + fraction * (y1 - y0))

                angle = float(segment["start_angle"]) + local_s / float(segment["radius"])
                cx, cy = segment["center"]  # type: ignore[misc]
                radius = float(segment["radius"])
                return (cx + radius * cos(angle), cy + radius * sin(angle))
        return upper_small

    return {
        "pitch_mm": float(pitch_mm),
        "small_sprocket_teeth": int(small_sprocket_teeth),
        "large_sprocket_teeth": int(large_sprocket_teeth),
        "center_distance_mm": center_distance_mm,
        "small_pitch_radius_mm": r1,
        "large_pitch_radius_mm": r2,
        "alpha_rad": alpha,
        "small_center": small_center,
        "large_center": large_center,
        "upper_small_tangent": upper_small,
        "lower_small_tangent": lower_small,
        "lower_large_tangent": lower_large,
        "upper_large_tangent": upper_large,
        "segments": segments,
        "cumulative_segment_lengths": cumulative,
        "total_length_mm": total_length,
        "point_at": point_at,
    }


def find_next_roller_path_coordinate(
    path: dict[str, object],
    current_path_coordinate_mm: float,
    pitch_mm: float,
    tolerance_mm: float = 1.0e-12,
) -> float:
    """Find the first forward point on the path one pitch chord away."""
    point_at: Callable[[float], Point2D] = path["point_at"]  # type: ignore[assignment]
    current_point = point_at(current_path_coordinate_mm)

    def chord_error(delta_s_mm: float) -> float:
        candidate = point_at(current_path_coordinate_mm + delta_s_mm)
        return distance_2d(current_point, candidate) - pitch_mm

    scan_step = pitch_mm / 50.0
    maximum_delta = 5.0 * pitch_mm
    previous_delta = 0.0
    previous_error = chord_error(previous_delta)
    lower = upper = None
    delta = scan_step

    while delta <= maximum_delta + 1.0e-12:
        current_error = chord_error(delta)
        if previous_error <= 0.0 <= current_error:
            lower, upper = previous_delta, delta
            break
        previous_delta, previous_error = delta, current_error
        delta += scan_step

    if lower is None or upper is None:
        raise RuntimeError("Could not locate the next roller on the pitch path.")

    for _ in range(90):
        midpoint = (lower + upper) / 2.0
        error = chord_error(midpoint)
        if abs(error) <= tolerance_mm:
            return current_path_coordinate_mm + midpoint
        if error < 0.0:
            lower = midpoint
        else:
            upper = midpoint
    return current_path_coordinate_mm + (lower + upper) / 2.0


def walk_rigid_chain(
    pitch_mm: float,
    small_sprocket_teeth: int,
    large_sprocket_teeth: int,
    center_distance_mm: float,
    link_count: int,
) -> dict[str, object]:
    path = build_exact_pitch_path(
        pitch_mm,
        small_sprocket_teeth,
        large_sprocket_teeth,
        center_distance_mm,
    )
    point_at: Callable[[float], Point2D] = path["point_at"]  # type: ignore[assignment]
    current_s = 0.0
    path_coordinates = [current_s]
    points = [point_at(current_s)]

    for _ in range(int(link_count)):
        current_s = find_next_roller_path_coordinate(path, current_s, pitch_mm)
        path_coordinates.append(current_s)
        points.append(point_at(current_s))

    return {
        "path": path,
        "path_coordinates_mm": path_coordinates,
        "points_with_closure": points,
        "roller_centers": points[:-1],
        "closure_point": points[-1],
        "closure_residual_mm": current_s - float(path["total_length_mm"]),
    }


def _closure_residual(
    pitch_mm: float,
    small_sprocket_teeth: int,
    large_sprocket_teeth: int,
    center_distance_mm: float,
    link_count: int,
) -> float:
    result = walk_rigid_chain(
        pitch_mm,
        small_sprocket_teeth,
        large_sprocket_teeth,
        center_distance_mm,
        link_count,
    )
    return float(result["closure_residual_mm"])


def solve_center_distance_for_link_count(
    pitch_mm: float,
    small_sprocket_teeth: int,
    large_sprocket_teeth: int,
    desired_center_distance_mm: float,
    link_count: int,
    tolerance_mm: float = 5.0e-10,
) -> tuple[float, dict[str, object]]:
    """Correct center distance so exactly ``link_count`` rigid links close."""
    r1 = calculate_pitch_radius(pitch_mm, small_sprocket_teeth)
    r2 = calculate_pitch_radius(pitch_mm, large_sprocket_teeth)
    physical_minimum = abs(r2 - r1) + max(1.0e-7, pitch_mm * 1.0e-9)
    desired = max(float(desired_center_distance_mm), physical_minimum * 1.001)

    residual_at_desired = _closure_residual(
        pitch_mm, small_sprocket_teeth, large_sprocket_teeth, desired, link_count
    )
    if abs(residual_at_desired) <= tolerance_mm:
        solved = walk_rigid_chain(
            pitch_mm, small_sprocket_teeth, large_sprocket_teeth, desired, link_count
        )
        return desired, solved

    step = max(pitch_mm, desired * 0.05)
    if residual_at_desired < 0.0:
        upper, upper_residual = desired, residual_at_desired
        lower = max(physical_minimum, desired - step)
        lower_residual = _closure_residual(
            pitch_mm, small_sprocket_teeth, large_sprocket_teeth, lower, link_count
        )
        for _ in range(60):
            if lower_residual >= 0.0:
                break
            step *= 1.6
            next_lower = max(physical_minimum, desired - step)
            if next_lower == lower:
                break
            lower = next_lower
            lower_residual = _closure_residual(
                pitch_mm, small_sprocket_teeth, large_sprocket_teeth, lower, link_count
            )
    else:
        lower, lower_residual = desired, residual_at_desired
        upper = desired + step
        upper_residual = _closure_residual(
            pitch_mm, small_sprocket_teeth, large_sprocket_teeth, upper, link_count
        )
        for _ in range(60):
            if upper_residual <= 0.0:
                break
            step *= 1.6
            upper = desired + step
            upper_residual = _closure_residual(
                pitch_mm, small_sprocket_teeth, large_sprocket_teeth, upper, link_count
            )

    if not (lower_residual >= 0.0 and upper_residual <= 0.0):
        raise RuntimeError(
            f"Could not bracket center-distance solution for N={link_count}."
        )

    midpoint = desired
    for _ in range(90):
        midpoint = (lower + upper) / 2.0
        midpoint_residual = _closure_residual(
            pitch_mm,
            small_sprocket_teeth,
            large_sprocket_teeth,
            midpoint,
            link_count,
        )
        if abs(midpoint_residual) <= tolerance_mm:
            break
        if midpoint_residual > 0.0:
            lower = midpoint
        else:
            upper = midpoint

    solved = walk_rigid_chain(
        pitch_mm,
        small_sprocket_teeth,
        large_sprocket_teeth,
        midpoint,
        link_count,
    )
    return midpoint, solved


def calculate_discrete_chain_drive_geometry(
    pitch_mm: float,
    small_sprocket_teeth: int,
    large_sprocket_teeth: int,
    desired_center_distance_mm: float,
    require_even_link_count: bool = False,
    link_count_search_radius: int = 3,
) -> dict[str, object]:
    """Select N, correct center distance, and return FreeCAD-ready link poses."""
    pitch_mm = float(pitch_mm)
    z1 = int(small_sprocket_teeth)
    z2 = int(large_sprocket_teeth)
    desired_center_distance_mm = float(desired_center_distance_mm)
    if desired_center_distance_mm <= 0.0:
        raise ValueError("Desired center distance must be positive.")
    if link_count_search_radius < 0:
        raise ValueError("Link-count search radius cannot be negative.")

    desired_path = build_exact_pitch_path(pitch_mm, z1, z2, desired_center_distance_mm)
    estimated_count = int(round(float(desired_path["total_length_mm"]) / pitch_mm))
    minimum_count = max(4, estimated_count - int(link_count_search_radius))
    maximum_count = estimated_count + int(link_count_search_radius)
    candidate_counts = list(range(minimum_count, maximum_count + 1))
    if require_even_link_count:
        candidate_counts = [count for count in candidate_counts if count % 2 == 0]
    if not candidate_counts:
        candidate_counts = [estimated_count + (estimated_count % 2)]

    candidates: list[tuple[float, int, float, dict[str, object]]] = []
    errors: list[str] = []
    for link_count in candidate_counts:
        try:
            corrected_center, walk = solve_center_distance_for_link_count(
                pitch_mm,
                z1,
                z2,
                desired_center_distance_mm,
                link_count,
            )
        except (RuntimeError, ValueError) as exc:
            errors.append(f"N={link_count}: {exc}")
            continue
        candidates.append(
            (
                abs(corrected_center - desired_center_distance_mm),
                link_count,
                corrected_center,
                walk,
            )
        )

    if not candidates:
        detail = "; ".join(errors) if errors else "no candidates"
        raise RuntimeError(f"No discrete chain solution found ({detail}).")

    _, link_count, corrected_center, walk = min(candidates, key=lambda item: item[0])
    roller_centers: list[Point2D] = walk["roller_centers"]  # type: ignore[assignment]
    link_poses: list[dict[str, object]] = []
    pitch_errors: list[float] = []
    requires_offset = link_count % 2 == 1

    for index, start in enumerate(roller_centers):
        end = roller_centers[(index + 1) % link_count]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = sqrt(dx * dx + dy * dy)
        pitch_errors.append(abs(length - pitch_mm))
        if requires_offset and index == link_count - 1:
            link_type = "offset"
        else:
            link_type = "inner" if index % 2 == 0 else "outer"
        link_poses.append(
            {
                "index": index,
                "type": link_type,
                "x_mm": start[0],
                "y_mm": start[1],
                "angle_deg": degrees(atan2(dy, dx)),
                "length_mm": length,
            }
        )

    path = walk["path"]
    return {
        "pitch_mm": pitch_mm,
        "small_sprocket_teeth": z1,
        "large_sprocket_teeth": z2,
        "desired_center_distance_mm": desired_center_distance_mm,
        "corrected_center_distance_mm": corrected_center,
        "center_correction_mm": corrected_center - desired_center_distance_mm,
        "link_count": link_count,
        "requires_offset_link": requires_offset,
        "discrete_chain_length_mm": link_count * pitch_mm,
        "closure_residual_mm": float(walk["closure_residual_mm"]),
        "maximum_pitch_error_mm": max(pitch_errors, default=0.0),
        "small_pitch_radius_mm": float(path["small_pitch_radius_mm"]),
        "large_pitch_radius_mm": float(path["large_pitch_radius_mm"]),
        "roller_centers": roller_centers,
        "link_poses": link_poses,
        "path": path,
    }


def format_result_report(result: dict[str, object]) -> str:
    """Return a compact report suitable for the GUI or console."""
    return "\n".join(
        (
            "SELECTED EXACT RIGID-LINK SOLUTION",
            "-" * 62,
            f"N = {int(result['link_count'])}",
            f"Requires OffsetLink = {bool(result['requires_offset_link'])}",
            "Corrected center distance = "
            f"{float(result['corrected_center_distance_mm']):.9f} mm",
            f"Center correction = {float(result['center_correction_mm']):+.9f} mm",
            "Discrete chain length N*P = "
            f"{float(result['discrete_chain_length_mm']):.9f} mm",
            f"Closure residual = {float(result['closure_residual_mm']):.12e} mm",
            "Maximum pitch error = "
            f"{float(result['maximum_pitch_error_mm']):.12e} mm",
        )
    )


def plot_result(result: dict[str, object], show_point_indexes: bool = True) -> None:
    """Optional diagnostic plot; matplotlib is imported only on explicit use."""
    import matplotlib.pyplot as plt

    points: list[Point2D] = result["roller_centers"]  # type: ignore[assignment]
    closed = points + points[:1]
    xs = [point[0] for point in closed]
    ys = [point[1] for point in closed]
    plt.figure(figsize=(12, 5))
    plt.plot(xs, ys, "o-", markersize=4)
    if show_point_indexes:
        for index, (x, y) in enumerate(points):
            plt.text(x, y, str(index), fontsize=7)
    plt.axis("equal")
    plt.grid(True)
    plt.title(
        f"Rigid chain: N={result['link_count']}, "
        f"C={float(result['corrected_center_distance_mm']):.6f} mm"
    )
    plt.xlabel("x [mm]")
    plt.ylabel("y [mm]")
    plt.show()
