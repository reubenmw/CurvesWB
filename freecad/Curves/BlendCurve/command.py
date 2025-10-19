"""FreeCAD command registration for Blend Curve tool.

This module registers the BlendCurve command with FreeCAD's GUI system,
making it available in menus and toolbars. The command opens an interactive
dialog for creating smooth blend curves between two edges.
"""

import os
import FreeCAD
import FreeCADGui

from freecad.Curves import ICONPATH
from .dialog_panel import BlendCurveTaskPanel

# Icon path for the blend curve tool
TOOL_ICON = os.path.join(ICONPATH, "blend.svg")

# Translation function for internationalisation
translate = FreeCAD.Qt.translate


class BlendCurveCommand:
    """FreeCAD command class for creating blend curves.

    This command opens the BlendCurve task panel dialog, which allows users
    to interactively create smooth transition curves between two edges with
    control over continuity (G0-G3), scale, position, and trimming options.
    """

    def Activated(self):
        """Called when the command is activated from menu or toolbar.

        Opens the BlendCurve task panel dialog in FreeCAD's task view.
        """
        FreeCAD.Console.PrintMessage("=" * 60 + "\n")
        FreeCAD.Console.PrintMessage("Blend Curve tool activated\n")
        FreeCAD.Console.PrintMessage("=" * 60 + "\n")

        # Create and show the task panel dialog
        panel = BlendCurveTaskPanel()
        FreeCADGui.Control.showDialog(panel)

    def GetResources(self):
        """Return command resources (icon, menu text, tooltip).

        Returns:
            dict: Command resources for FreeCAD GUI
        """
        return {
            "Pixmap": TOOL_ICON,
            "MenuText": translate("BlendCurve", "Blend Curve"),
            "ToolTip": translate(
                "BlendCurve",
                "Create smooth blend curve between two edges with G0-G3 continuity",
            ),
        }


# Register command with FreeCAD GUI system
FreeCADGui.addCommand("BlendCurve", BlendCurveCommand())
