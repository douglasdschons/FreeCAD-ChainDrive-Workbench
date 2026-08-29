"""FreeCAD GUI commands exposed by the Chain Drive workbench.

The module name is deliberately addon-specific to avoid colliding with other
installed FreeCAD workbenches that also ship a top-level ``commands.py``.
"""

from pathlib import Path

import FreeCADGui as Gui


APP_ROOT = Path(__file__).resolve().parent
ICON_DIR = APP_ROOT / "Resources" / "icons"


class _OpenGeneratorCommand:
    def __init__(self, mode, menu_text, tooltip, icon):
        self.mode = mode
        self.menu_text = menu_text
        self.tooltip = tooltip
        self.icon = icon

    def GetResources(self):
        return {
            "Pixmap": str(ICON_DIR / self.icon),
            "MenuText": self.menu_text,
            "ToolTip": self.tooltip,
        }

    def Activated(self):
        from gui.unified_dialog import show_dialog
        show_dialog(APP_ROOT, initial_mode=self.mode)

    def IsActive(self):
        return True


COMMANDS = {
    "ChainDrive_GenerateChain": _OpenGeneratorCommand(
        "chain", "Generate Chain", "Generate an exact-pitch rigid-link chain", "GenerateChainDrive.svg"
    ),
    "ChainDrive_GenerateSprocket": _OpenGeneratorCommand(
        "single", "Generate Sprocket", "Generate one catalog-backed sprocket", "GenerateChainDrive.svg"
    ),
    "ChainDrive_GenerateChainDrive": _OpenGeneratorCommand(
        "drive", "Generate Chain Drive", "Generate two sprockets and their chain", "GenerateChainDrive.svg"
    ),
}


def register_commands():
    for name, command in COMMANDS.items():
        Gui.addCommand(name, command)
    return list(COMMANDS)
