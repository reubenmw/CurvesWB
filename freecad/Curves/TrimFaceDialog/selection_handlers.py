# -*- coding: utf-8 -*-
# Selection gates and observers for trim face dialog


class SelectionGate:
    """Selection gate to control what user can select in 3D view"""

    def __init__(self, mode):
        self.mode = mode

    def allow(self, doc_name, obj_name, subname):
        if self.mode == "edge":
            return "Edge" in subname
        elif self.mode == "face":
            return "Face" in subname
        return False


class EdgeSelectionObserver:
    """Observer for edge selection events"""

    def __init__(self, parent):
        self.parent = parent

    def addSelection(self, doc_name, obj_name, sub_name, pos):
        import FreeCAD

        if "Edge" in sub_name:
            obj = FreeCAD.ActiveDocument.getObject(obj_name)
            self.parent.on_edge_selected(obj, sub_name)


class FaceSelectionObserver:
    """Observer for face selection events"""

    def __init__(self, parent):
        self.parent = parent

    def addSelection(self, doc_name, obj_name, sub_name, pos):
        import FreeCAD

        if "Face" in sub_name:
            obj = FreeCAD.ActiveDocument.getObject(obj_name)
            self.parent.on_face_selected(obj, sub_name)


class PointSelectionObserver:
    """Observer for point selection events"""

    def __init__(self, parent):
        self.parent = parent

    def addSelection(self, doc_name, obj_name, sub_name, pos):
        from PySide import QtCore

        QtCore.QTimer.singleShot(100, lambda: self.parent.check_picked_point())


class HoverPointCallback:
    """Callback for hover-based point preview during point selection.

    This class handles mouse movement events in the 3D view and updates
    the transparent preview to show which region will be deleted.
    """

    def __init__(self, parent):
        self.parent = parent
        self.view = None
        self.callback_node = None

    def install(self):
        """Install the hover callback on the active view"""
        try:
            import FreeCADGui
            from pivy import coin

            self.view = FreeCADGui.ActiveDocument.ActiveView

            # Create event callback node
            self.callback_node = coin.SoEventCallback()
            self.callback_node.addEventCallback(
                coin.SoLocation2Event.getClassTypeId(), self.on_mouse_move
            )

            # Add to scene graph
            scene = self.view.getSceneGraph()
            scene.insertChild(self.callback_node, 0)

            import FreeCAD

            FreeCAD.Console.PrintMessage(
                "Hover preview installed - move mouse over face\n"
            )

        except Exception as e:
            import FreeCAD

            FreeCAD.Console.PrintError(f"Failed to install hover callback: {str(e)}\n")

    def remove(self):
        """Remove the hover callback"""
        try:
            if self.view and self.callback_node:
                scene = self.view.getSceneGraph()
                scene.removeChild(self.callback_node)
                self.callback_node = None
                self.view = None

                import FreeCAD

                FreeCAD.Console.PrintMessage("Hover preview removed\n")
        except Exception as e:
            import FreeCAD

            FreeCAD.Console.PrintError(f"Failed to remove hover callback: {str(e)}\n")

    def on_mouse_move(self, user_data, event_callback):
        """Called when mouse moves over the 3D view"""
        try:
            from pivy import coin
            import FreeCADGui

            event = event_callback.getEvent()

            if not isinstance(event, coin.SoLocation2Event):
                return

            # Get mouse position
            pos = event.getPosition()

            # Extract x, y coordinates from SbVec2s
            mouse_x = pos[0]
            mouse_y = pos[1]

            # Get point under cursor using raycasting
            view = FreeCADGui.ActiveDocument.ActiveView
            info = view.getObjectInfo((mouse_x, mouse_y))

            if info and "x" in info:
                # We have a point on the surface
                import FreeCAD

                hover_point = FreeCAD.Vector(info["x"], info["y"], info["z"])
                self.parent.update_hover_preview(hover_point)

        except Exception as e:
            # Silently ignore errors during rapid mouse movement
            pass
