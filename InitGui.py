"""Register the Chain Drive workbench in FreeCAD."""

from pathlib import Path

import FreeCADGui as Gui


MODULE_DIR = Path(__file__).resolve().parent


class ChainDriveWorkbench(Gui.Workbench):
    MenuText = "Chain Drive"
    ToolTip = "Parametric ASA/ANSI sprockets and rigid-link chain drives"
    Icon = str(MODULE_DIR / "Resources" / "icons" / "ASAChainDriveWorkbench.svg")

    def Initialize(self):
        from commands import register_commands
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

