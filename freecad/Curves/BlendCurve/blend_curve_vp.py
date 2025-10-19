# ViewProvider for blend curve objects - handles editing and display

import FreeCAD
import FreeCADGui
from .dialog_panel import BlendCurveTaskPanel


class BlendCurveViewProvider:
    """ViewProvider for BlendCurve objects.

    Handles:
    - Double-click editing
    - Opening the task panel for editing
    - Display properties
    """

    def __init__(self, vobj):
        """Initialize the ViewProvider

        Args:
            vobj: The view object (obj.ViewObject)
        """
        vobj.Proxy = self
        self.Object = vobj.Object

    def attach(self, vobj):
        """Called when document is restored

        Args:
            vobj: The view object
        """
        self.Object = vobj.Object

    def getIcon(self):
        """Return the icon path for this object"""
        import os
        from freecad.Curves import ICONPATH

        return os.path.join(ICONPATH, "blend.svg")

    def doubleClicked(self, vobj):
        """Called when user double-clicks the object in tree view.

        This should open the task panel for editing.

        Args:
            vobj: The view object

        Returns:
            True if handled, False otherwise
        """
        self.setEdit(vobj)
        return True

    def setEdit(self, vobj, mode=0):
        """Called when entering edit mode.

        Opens the task panel to edit this blend curve.

        Args:
            vobj: The view object
            mode: Edit mode (0 = default)

        Returns:
            True if edit mode started successfully
        """
        # Create task panel instance with the existing object for editing
        panel = BlendCurveTaskPanel(edit_object=vobj.Object)

        # Open the task panel dialog
        FreeCADGui.Control.showDialog(panel)
        return True

    def unsetEdit(self, vobj, mode=0):
        """Called when leaving edit mode.

        Closes the task panel and cleans up.

        Args:
            vobj: The view object
            mode: Edit mode
        """
        FreeCADGui.Control.closeDialog()

    def __getstate__(self):
        """Save state for serialization"""
        return None

    def __setstate__(self, state):
        """Restore state from serialization"""
        return None
