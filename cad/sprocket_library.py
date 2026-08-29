"""Incremental on-disk library for validated ASME/ENCO sprockets."""

from __future__ import annotations

from pathlib import Path

import FreeCAD as App

from cad.asme_sprocket_generator import (
    calculate_asme_tooth_geometry,
    generate_sprocket_file,
)


PROFILE_ID = "ASME_B29_1_GEARS_V1"


def _bore_tag(bore_diameter_mm):
    return f"{float(bore_diameter_mm):.2f}".replace(".", "p")


def library_file_name(sprocket_data, bore_diameter_mm):
    manufacturer = str(sprocket_data.get("manufacturer", "ENCO")).upper()
    asa = int(sprocket_data["asa"])
    teeth = int(sprocket_data["teeth_z"])
    return (
        f"{manufacturer}_ASA{asa}_{teeth}T_"
        f"B{_bore_tag(bore_diameter_mm)}_ASME.FCStd"
    )


def _quantity_value(value):
    return float(getattr(value, "Value", value))


def _document_for_path(file_path):
    target = str(Path(file_path).resolve()).replace("\\", "/").casefold()
    for doc in App.listDocuments().values():
        current = str(getattr(doc, "FileName", "") or "")
        if current and current.replace("\\", "/").casefold() == target:
            return doc, False
    return App.openDocument(str(file_path)), True


def _find_sprocket_object(doc, sprocket_data, bore_diameter_mm):
    expected_asa = int(sprocket_data["asa"])
    expected_teeth = int(sprocket_data["teeth_z"])
    expected_bore = float(bore_diameter_mm)
    candidates = []
    for obj in doc.Objects:
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        if not obj.Shape.isValid() or len(obj.Shape.Solids) != 1:
            continue
        if "ASA" not in obj.PropertiesList or "Teeth" not in obj.PropertiesList:
            continue
        if int(obj.ASA) != expected_asa or int(obj.Teeth) != expected_teeth:
            continue
        if "BoreDiameter" in obj.PropertiesList:
            if abs(_quantity_value(obj.BoreDiameter) - expected_bore) > 1.0e-6:
                continue
        candidates.append(obj)
    if len(candidates) != 1:
        raise RuntimeError(
            f"Library file must contain exactly one matching valid sprocket; "
            f"found {len(candidates)} in {doc.FileName}."
        )
    return candidates[0]


def _candidate_paths(
    library_dir,
    sprocket_data,
    bore_diameter_mm,
    additional_search_dirs=None,
):
    file_name = library_file_name(sprocket_data, bore_diameter_mm)
    directories = [Path(library_dir)]
    directories.extend(Path(path) for path in (additional_search_dirs or []))
    seen = set()
    for directory in directories:
        resolved = str(directory.resolve()).casefold()
        if resolved in seen:
            continue
        seen.add(resolved)
        yield directory / file_name


def find_library_file(
    library_dir,
    sprocket_data,
    bore_diameter_mm,
    additional_search_dirs=None,
):
    for candidate in _candidate_paths(
        library_dir,
        sprocket_data,
        bore_diameter_mm,
        additional_search_dirs,
    ):
        if not candidate.is_file():
            continue
        doc, opened_here = _document_for_path(candidate)
        try:
            _find_sprocket_object(doc, sprocket_data, bore_diameter_mm)
        finally:
            if opened_here:
                App.closeDocument(doc.Name)
        return candidate.resolve()
    return None


def ensure_library_file(
    chain_data,
    sprocket_data,
    bore_diameter_mm,
    library_dir,
    additional_search_dirs=None,
):
    existing = find_library_file(
        library_dir,
        sprocket_data,
        bore_diameter_mm,
        additional_search_dirs,
    )
    if existing is not None:
        return existing, True

    library_dir = Path(library_dir)
    library_dir.mkdir(parents=True, exist_ok=True)
    doc, sprocket, geometry, output_path = generate_sprocket_file(
        chain_data=chain_data,
        sprocket_data=sprocket_data,
        bore_diameter_mm=float(bore_diameter_mm),
        output_dir=library_dir,
    )
    expected = library_dir / library_file_name(sprocket_data, bore_diameter_mm)
    if Path(output_path).resolve() != expected.resolve():
        App.closeDocument(doc.Name)
        raise RuntimeError(
            "The library key unexpectedly produced a non-deterministic file name: "
            f"{output_path}"
        )
    App.closeDocument(doc.Name)
    return Path(output_path).resolve(), False


def load_library_shape(file_path, sprocket_data, bore_diameter_mm):
    doc, opened_here = _document_for_path(file_path)
    try:
        sprocket = _find_sprocket_object(doc, sprocket_data, bore_diameter_mm)
        return sprocket.Shape.copy()
    finally:
        if opened_here:
            App.closeDocument(doc.Name)


def _add_property_once(obj, property_type, name, group):
    if name not in obj.PropertiesList:
        obj.addProperty(property_type, name, group)


def add_sprocket_from_library(
    target_doc,
    chain_data,
    sprocket_data,
    bore_diameter_mm,
    library_dir,
    additional_search_dirs=None,
    object_name="Sprocket",
    label=None,
):
    file_path, cache_hit = ensure_library_file(
        chain_data,
        sprocket_data,
        bore_diameter_mm,
        library_dir,
        additional_search_dirs,
    )
    shape = load_library_shape(file_path, sprocket_data, bore_diameter_mm)
    obj = target_doc.addObject("Part::Feature", object_name)
    asa = int(sprocket_data["asa"])
    teeth = int(sprocket_data["teeth_z"])
    obj.Label = label or f"ENCO ASA {asa}-1 | {teeth}T | ASME B29.1"
    obj.Shape = shape

    for property_type, name, value, group in (
        ("App::PropertyString", "Manufacturer", "ENCO", "Catalog"),
        (
            "App::PropertyString",
            "CatalogReference",
            str(sprocket_data["reference"]),
            "Catalog",
        ),
        ("App::PropertyInteger", "ASA", asa, "Chain"),
        ("App::PropertyInteger", "Teeth", teeth, "Geometry"),
        (
            "App::PropertyLength",
            "BoreDiameter",
            float(bore_diameter_mm),
            "Dimensions",
        ),
        ("App::PropertyString", "ProfileID", PROFILE_ID, "Library"),
        ("App::PropertyString", "LibrarySource", str(file_path), "Library"),
        ("App::PropertyBool", "LibraryCacheHit", bool(cache_hit), "Library"),
    ):
        _add_property_once(obj, property_type, name, group)
        setattr(obj, name, value)

    if getattr(App, "GuiUp", False):
        obj.ViewObject.ShapeColor = (0.72, 0.72, 0.75)
    geometry = calculate_asme_tooth_geometry(
        float(chain_data["pitch_P_mm"]),
        float(chain_data["roller_diameter_R_mm"]),
        teeth,
    )
    target_doc.recompute()
    return obj, geometry, file_path, cache_hit


def open_or_create_sprocket_document(
    chain_data,
    sprocket_data,
    bore_diameter_mm,
    library_dir,
    additional_search_dirs=None,
):
    existing = find_library_file(
        library_dir,
        sprocket_data,
        bore_diameter_mm,
        additional_search_dirs,
    )
    if existing is not None:
        doc, _ = _document_for_path(existing)
        sprocket = _find_sprocket_object(doc, sprocket_data, bore_diameter_mm)
        geometry = calculate_asme_tooth_geometry(
            float(chain_data["pitch_P_mm"]),
            float(chain_data["roller_diameter_R_mm"]),
            int(sprocket_data["teeth_z"]),
        )
        if getattr(App, "GuiUp", False):
            try:
                import FreeCADGui as Gui

                Gui.activeDocument().activeView().viewAxonometric()
                Gui.activeDocument().activeView().fitAll()
            except Exception:
                pass
        return doc, sprocket, geometry, existing, True

    doc, sprocket, geometry, output_path = generate_sprocket_file(
        chain_data=chain_data,
        sprocket_data=sprocket_data,
        bore_diameter_mm=float(bore_diameter_mm),
        output_dir=library_dir,
    )
    return doc, sprocket, geometry, Path(output_path).resolve(), False
