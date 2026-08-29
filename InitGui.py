"""Register the Chain Drive workbench in FreeCAD.

FreeCAD executes ``InitGui.py`` rather than importing it normally, so
``__file__`` is not guaranteed to exist here.
"""

from pathlib import Path
import sys

import FreeCADGui as Gui


def _resolve_module_dir():
    for entry in sys.path:
        if not entry:
            continue
        candidate = Path(entry)
        if candidate.name == "ChainDrive" and (candidate / "package.xml").is_file():
            return candidate.absolute()
    raise RuntimeError("Could not resolve the installed ChainDrive module directory.")


MODULE_DIR = _resolve_module_dir()


class ChainDriveWorkbench(Gui.Workbench):
    MenuText = "Chain Drive"
    ToolTip = "Parametric ASA/ANSI sprockets and rigid-link chain drives"
    Icon = str(MODULE_DIR / "Resources" / "icons" / "ASAChainDriveWorkbench.svg")

    def Initialize(self):
        from chain_drive_commands import register_commands
        command_list = register_commands()
        self.appendToolbar("Chain Drive", command_list)
        self.appendMenu("Chain Drive", command_list)

    def Activated(self):
        return None

    def Deactivated(self):
        return None

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(ChainDriveWorkbench())
