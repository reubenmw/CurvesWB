# -*- coding: utf-8 -*-
import os
import FreeCAD
import FreeCADGui

from freecad.Curves import ICONPATH
from .dialog_panel import TrimFaceDialogTaskPanel

TOOL_ICON = os.path.join(ICONPATH, 'trimFace.svg')

# Translation function
translate = FreeCAD.Qt.translate


class TrimFaceDialogCommand:
    def Activated(self):
        FreeCAD.Console.PrintMessage("=" * 60 + "\n")
        FreeCAD.Console.PrintMessage("Trim Face activiated...\n")
        FreeCAD.Console.PrintMessage("=" * 60 + "\n")

        panel = TrimFaceDialogTaskPanel()
        FreeCADGui.Control.showDialog(panel)

    def GetResources(self):
        return {
            'Pixmap': TOOL_ICON,
            'MenuText': translate('TrimFaceDialog', 'Trim Face Dialog'),
            'ToolTip': translate('TrimFaceDialog', 'Trim a face using curves projection of camera direction, normal, or custom vector direction'),
        }


FreeCADGui.addCommand('TrimDialog', TrimFaceDialogCommand())
