# -*- coding: utf-8 -*-

__title__ = 'Trim face dialog - FreeCAD command'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'FreeCAD command registration for trim face dialog'

import os
import FreeCAD
import FreeCADGui

from freecad.Curves import ICONPATH
from .dialog_panel import TrimFaceDialogTaskPanel

TOOL_ICON = os.path.join(ICONPATH, 'trimFace.svg')


class TrimFaceDialogCommand:
    def Activated(self):
        FreeCAD.Console.PrintMessage("=" * 60 + "\n")
        FreeCAD.Console.PrintMessage("TRIM FACE DIALOG - FLUID NX-STYLE v3.0\n")
        FreeCAD.Console.PrintMessage("Loading from: Curves Fork addon\n")
        FreeCAD.Console.PrintMessage("October 2025 - Refactored by Claude\n")
        FreeCAD.Console.PrintMessage("=" * 60 + "\n")

        panel = TrimFaceDialogTaskPanel()
        FreeCADGui.Control.showDialog(panel)

    def GetResources(self):
        return {
            'Pixmap': TOOL_ICON,
            'MenuText': 'Trim Face Dialog [NX-STYLE v3.0]',
            'ToolTip': 'FLUID WORKFLOW - Trim a face with automatic step progression (October 2025)'
        }


FreeCADGui.addCommand('TrimDialog', TrimFaceDialogCommand())
