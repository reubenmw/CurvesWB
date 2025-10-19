# -*- coding: utf-8 -*-
import os
import FreeCAD

try:
    import BOPTools.SplitAPI

    splitAPI = BOPTools.SplitAPI
except ImportError:
    FreeCAD.Console.PrintError("Failed importing BOPTools. Fallback to Part API\n")
    import Part

    splitAPI = Part.BOPTools.SplitAPI

from freecad.Curves import ICONPATH

# Module constants
TOOL_ICON = os.path.join(ICONPATH, "trimFace.svg")
DEBUG = False


def debug(string):
    """Debug print helper"""
    if DEBUG:
        FreeCAD.Console.PrintMessage(string)
        FreeCAD.Console.PrintMessage("\n")


# Import main components for easy access
from .selection_handlers import (
    SelectionGate,
    EdgeSelectionObserver,
    FaceSelectionObserver,
    PointSelectionObserver,
)
from .trim_logic import TrimFaceLogic
from .trim_face_object import TrimFaceObject
from .trim_face_vp import TrimFaceViewProvider
from .dialog_panel import TrimFaceDialogTaskPanel
from .command import TrimFaceDialogCommand

# Public API
__all__ = [
    "SelectionGate",
    "EdgeSelectionObserver",
    "FaceSelectionObserver",
    "PointSelectionObserver",
    "TrimFaceLogic",
    "TrimFaceObject",
    "TrimFaceViewProvider",
    "TrimFaceDialogTaskPanel",
    "TrimFaceDialogCommand",
    "TOOL_ICON",
    "DEBUG",
    "debug",
]
