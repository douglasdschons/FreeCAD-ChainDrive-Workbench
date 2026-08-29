"""Approximate App::Link chain scaling; run with FreeCADCmd."""

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
from application import generate_chain


for desired in (430.0, 1100.0, 1750.0):
    started = time.perf_counter()
    generated = generate_chain(80, 11, 20, desired, save=False)
    elapsed = time.perf_counter() - started
    print(
        f"PERF desired_mm={desired:.1f} links={len(generated['links'])} "
        f"templates={len(generated['templates'])} seconds={elapsed:.6f}"
    )
    assert len(generated["templates"]) == 3
    assert all(item.TypeId == "App::Link" for item in generated["links"])
    App.closeDocument(generated["document"].Name)

