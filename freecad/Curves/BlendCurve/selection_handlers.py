"""Selection handlers for Blend Curve interactive editing.

This module provides selection gates and observers that manage user interaction
during blend curve creation. It filters valid selections and notifies the dialog
when edges or points are selected.

Classes:
    SelectionGate: Filters 3D viewport selections to specific geometry types
    EdgeSelectionObserver: Monitors and responds to edge selection events
    BlendPointSelectionObserver: Monitors point clicks on edges for position selection
"""

import FreeCAD
import FreeCADGui
import Part


class SelectionGate:
    """Selection filter for FreeCAD 3D viewport.

    Restricts user selections to specific geometry types (edges, faces, points).
    This prevents invalid selections and provides immediate visual feedback.

    Attributes:
        selection_type (str): Type of geometry to allow ('edge', 'face', 'point')
    """

    def __init__(self, selection_type):
        """Initialize the selection gate.

        Args:
            selection_type (str): 'edge', 'face', or 'point'
        """
        self.selection_type = selection_type

    def allow(self, doc, obj, sub):
        """Determine if a selection is allowed.

        Called by FreeCAD for each potential selection before highlighting.

        Args:
            doc (str): Document name
            obj (str): Object name
            sub (str): Sub-element name (e.g., "Edge1", "Face3")

        Returns:
            bool: True if selection should be allowed, False otherwise
        """
        if self.selection_type == "edge":
            return "Edge" in sub
        elif self.selection_type == "face":
            return "Face" in sub
        elif self.selection_type == "point":
            return True  # Allow all for point picking
        return False


class EdgeSelectionObserver:
    """Selection observer for edge picking in blend curve workflow.

    Monitors user selections in the 3D viewport and notifies the dialog panel
    when valid edges are selected. Works in conjunction with SelectionGate
    to provide filtered, interactive edge selection.

    Attributes:
        dialog (BlendCurveTaskPanel): The parent dialog panel
        curve_id (str): Which curve is being selected ('curve1' or 'curve2')
    """

    def __init__(self, dialog, curve_id):
        """Initialize the edge selection observer.

        Args:
            dialog (BlendCurveTaskPanel): The BlendCurveTaskPanel instance
            curve_id (str): Which curve ('curve1' or 'curve2')
        """
        self.dialog = dialog
        self.curve_id = curve_id

    def addSelection(self, doc, obj, sub, pnt):
        """Handle edge selection event.

        Called by FreeCAD when user selects an object in the 3D viewport.

        Args:
            doc (str): Document name
            obj (str): Object name
            sub (str): Sub-element name (e.g., "Edge1")
            pnt (FreeCAD.Vector): 3D point where selection occurred
        """
        if "Edge" in sub:
            doc_obj = FreeCAD.ActiveDocument.getObject(obj)
            self.dialog.on_edge_selected(self.curve_id, doc_obj, sub)


class BlendPointSelectionObserver:
    """Selection observer for blend point positioning on edges.

    Monitors point clicks on edges to determine blend point placement.
    Converts 3D click coordinates to curve parameters for precise positioning.

    Note: Currently not actively used in the dialog, but available for future
    point-based positioning features.

    Attributes:
        dialog (BlendCurveTaskPanel): The parent dialog panel
        edge_num (int): Which edge (1 or 2)
    """

    def __init__(self, dialog, edge_num):
        """Initialize the blend point selection observer.

        Args:
            dialog (BlendCurveTaskPanel): The BlendCurveTaskPanel instance
            edge_num (int): Which edge (1 or 2)
        """
        self.dialog = dialog
        self.edge_num = edge_num

    def addSelection(self, doc, obj, sub, pnt):
        """Handle point selection event on edge.

        Converts 3D click point to curve parameter using orthogonal projection.

        Args:
            doc (str): Document name
            obj (str): Object name
            sub (str): Sub-element name (e.g., "Edge1")
            pnt (FreeCAD.Vector): 3D point where user clicked
        """
        if pnt and sub:
            # Get the edge shape from the selection
            edge_shape = obj.Shape.getElement(sub)

            if hasattr(edge_shape, "Curve"):
                # Calculate curve parameter from picked 3D point
                try:
                    param = edge_shape.Curve.parameter(pnt)
                    self.dialog.on_blend_point_selected(self.edge_num, obj, sub, param)
                except Exception as e:
                    FreeCAD.Console.PrintError(
                        f"Error calculating curve parameter: {str(e)}\n"
                    )
