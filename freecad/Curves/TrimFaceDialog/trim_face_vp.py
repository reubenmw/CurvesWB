# -*- coding: utf-8 -*-

__title__ = 'Trim Face ViewProvider'
__author__ = 'Christophe Grellier (Chris_G) & Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'ViewProvider for trim face objects - handles editing and display'

import FreeCAD
import FreeCADGui

from . import TOOL_ICON


class TrimFaceViewProvider:
    """ViewProvider for TrimFace objects.

    Handles:
    - Double-click editing
    - Opening the task panel for editing
    - Display properties
    - Object hierarchy
    """

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return TOOL_ICON

    def attach(self, vobj):
        self.Object = vobj.Object

    def doubleClicked(self, vobj):
        """Called when user double-clicks the object in tree view

        This should open the task panel for editing the TrimFace object.
        """
        return self.setEdit(vobj, 0)

    def setEdit(self, vobj, mode=0):
        """Open the task panel for editing this TrimFace object

        Args:
            vobj: The view object
            mode: Edit mode (0 = default)

        Returns:
            True if task panel opened successfully
        """
        from .dialog_panel import TrimFaceDialogTaskPanel

        panel = TrimFaceDialogTaskPanel(self.Object)
        FreeCADGui.Control.showDialog(panel)
        return True

    def unsetEdit(self, vobj, mode=0):
        """Close the task panel when editing finishes

        Args:
            vobj: The view object
            mode: Edit mode
        """
        FreeCADGui.Control.closeDialog()

    def claimChildren(self):
        children = []
        if hasattr(self.Object, "DirVector"):
            if self.Object.DirVector:
                children.append(self.Object.DirVector)
        if hasattr(self.Object, "Face"):
            if self.Object.Face:
                children.append(self.Object.Face[0])
        if hasattr(self.Object, "Tool"):
            if self.Object.Tool:
                # For clean hierarchy system, return all tool objects
                # These should be the extended curves that contain the originals
                for tool in self.Object.Tool:
                    if tool and len(tool) > 0:
                        children.append(tool[0])
        return children

    if FreeCAD.Version()[0] == "0" and ".".join(FreeCAD.Version()[1:3]) >= "21.2":

        def dumps(self):
            return {"name": self.Object.Name}

        def loads(self, state):
            self.Object = FreeCAD.ActiveDocument.getObject(state["name"])
            return None

    else:

        def __getstate__(self):
            return {"name": self.Object.Name}

        def __setstate__(self, state):
            self.Object = FreeCAD.ActiveDocument.getObject(state["name"])
            return None
