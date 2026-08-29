"""FreeCAD GUI registration smoke test; the process exits when complete."""

import FreeCAD as App
import FreeCADGui as Gui


expected = {
    "ChainDrive_GenerateChain",
    "ChainDrive_GenerateSprocket",
    "ChainDrive_GenerateChainDrive",
}
workbenches = Gui.listWorkbenches()
assert "ChainDriveWorkbench" in workbenches, sorted(workbenches)
Gui.activateWorkbench("ChainDriveWorkbench")
assert Gui.activeWorkbench().name() == "ChainDriveWorkbench"
Gui.activateWorkbench("PartWorkbench")
Gui.activateWorkbench("ChainDriveWorkbench")
assert Gui.activeWorkbench().name() == "ChainDriveWorkbench"
for name in expected:
    assert Gui.Command.get(name) is not None, name
print("GUI_SMOKE_OK")
App.quit()

