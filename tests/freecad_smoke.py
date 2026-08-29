"""Run with FreeCADCmd, not ordinary CPython."""

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App

from application import generate_chain, generate_chain_drive, generate_sprocket
from cad.offset_link_generator import create_offset_link_shape
from cad.templates import create_inner_template, create_outer_template
from core.catalog import get_chain_data, load_catalog


def valid(shape):
    return shape is not None and not shape.isNull() and shape.isValid()


catalog = load_catalog(ROOT / "data" / "chains" / "enco_asa_chains.csv")
chain = get_chain_data(catalog, 80)
doc = App.newDocument("TemplateSmoke")
inner = create_inner_template(doc, chain)
outer = create_outer_template(doc, chain)
offset_shape = create_offset_link_shape(chain)
doc.recompute()
assert valid(inner.Shape)
assert valid(outer.Shape)
assert valid(offset_shape)
App.closeDocument(doc.Name)

started = time.perf_counter()
sprocket_doc, sprocket, _geometry, _path, _hit = generate_sprocket(80, 11)
assert valid(sprocket.Shape)
sprocket_seconds = time.perf_counter() - started
App.closeDocument(sprocket_doc.Name)

started = time.perf_counter()
chain_result = generate_chain(80, 11, 20, 400.0, save=False)
assert len(chain_result["links"]) == 47
assert all(valid(item.LinkedObject.Shape) for item in chain_result["links"])
chain_seconds = time.perf_counter() - started
App.closeDocument(chain_result["document"].Name)

started = time.perf_counter()
drive = generate_chain_drive(80, 11, 20, 400.0, save=False)
assert valid(drive["small_sprocket"].Shape)
assert valid(drive["large_sprocket"].Shape)
assert len(drive["links"]) == 47
drive_seconds = time.perf_counter() - started
App.closeDocument(drive["document"].Name)

print("CAD_SMOKE_OK")
print(f"sprocket_seconds={sprocket_seconds:.6f}")
print(f"chain_47_seconds={chain_seconds:.6f}")
print(f"full_drive_seconds={drive_seconds:.6f}")

