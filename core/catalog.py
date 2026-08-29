"""Read the ENCO ASA chain catalog without third-party dependencies."""

from __future__ import annotations

import csv
from pathlib import Path


NUMERIC_COLUMNS = (
    "pitch_P_in_decimal",
    "pitch_P_mm",
    "inner_width_E_mm",
    "roller_diameter_R_mm",
    "plate_height_H_mm",
    "pin_diameter_G_mm",
    "overall_width_L_mm",
    "plate_thickness_T_mm",
    "breaking_load_kgf",
    "weight_kg_per_m",
)

REQUIRED_COLUMNS = (
    "asa_size",
    "pitch_P_mm",
    "inner_width_E_mm",
    "roller_diameter_R_mm",
    "plate_height_H_mm",
    "pin_diameter_G_mm",
    "overall_width_L_mm",
    "plate_thickness_T_mm",
)


def normalize_asa_size(value: object) -> str:
    """Return a catalog key such as ``80`` from common ASA spellings."""
    normalized = str(value).upper().replace("ASA", "").strip()
    if "-" in normalized:
        normalized = normalized.split("-", 1)[0].strip()
    if normalized.endswith(".0"):
        normalized = normalized[:-2]
    return normalized


def to_float(value: object) -> float:
    """Parse both Brazilian decimal-comma and decimal-point numbers."""
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        raise ValueError("Empty numeric value in chain catalog.")

    if "," in text and "." in text:
        # The last separator is the decimal separator.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    return float(text)


def _detect_delimiter(csv_path: Path) -> str:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(4096)
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
    except csv.Error:
        return ";"


def load_catalog(csv_path: str | Path) -> dict[str, dict[str, object]]:
    """Load and validate the CSV, indexed by normalized ASA size."""
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Chain catalog not found: {csv_path}")

    delimiter = _detect_delimiter(csv_path)
    catalog: dict[str, dict[str, object]] = {}

    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=delimiter)
        fieldnames = tuple(reader.fieldnames or ())
        missing = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
        if missing:
            raise ValueError(
                "Catalog is missing required column(s): " + ", ".join(missing)
            )

        for line_number, row in enumerate(reader, start=2):
            if not row or not any(str(value or "").strip() for value in row.values()):
                continue

            size = normalize_asa_size(row["asa_size"])
            if not size:
                raise ValueError(f"Missing ASA size at CSV line {line_number}.")

            data: dict[str, object] = {
                key: (value.strip() if isinstance(value, str) else value)
                for key, value in row.items()
                if key is not None
            }
            for column in NUMERIC_COLUMNS:
                if column in data and str(data[column]).strip():
                    try:
                        data[column] = to_float(data[column])
                    except ValueError as exc:
                        raise ValueError(
                            f"Invalid value for {column!r} at CSV line {line_number}: "
                            f"{data[column]!r}"
                        ) from exc

            data["asa_size"] = size
            data["pitch_mm"] = data["pitch_P_mm"]
            data["inner_width_mm"] = data["inner_width_E_mm"]
            data["roller_diameter_mm"] = data["roller_diameter_R_mm"]
            data["plate_height_mm"] = data["plate_height_H_mm"]
            data["pin_diameter_mm"] = data["pin_diameter_G_mm"]
            data["overall_width_mm"] = data["overall_width_L_mm"]
            data["plate_thickness_mm"] = data["plate_thickness_T_mm"]
            catalog[size] = data

    if not catalog:
        raise ValueError(f"Chain catalog is empty: {csv_path}")
    return catalog


def get_available_sizes(catalog: dict[str, dict[str, object]]) -> list[str]:
    def sort_key(value: str):
        try:
            return (0, int(value))
        except ValueError:
            return (1, value)

    return sorted(catalog, key=sort_key)


def get_chain_data(
    catalog: dict[str, dict[str, object]], asa_size: object
) -> dict[str, object]:
    size = normalize_asa_size(asa_size)
    try:
        return catalog[size]
    except KeyError as exc:
        available = ", ".join(get_available_sizes(catalog))
        raise ValueError(f"ASA {size} not found. Available sizes: {available}") from exc
