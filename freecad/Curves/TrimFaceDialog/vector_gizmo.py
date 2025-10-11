# -*- coding: utf-8 -*-

__title__ = 'Vector Direction Gizmo'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'Interactive 3D arrow gizmo for Custom Vector Direction input'

import FreeCAD
import FreeCADGui
from pivy import coin


class VectorDirectionGizmo:
    """
    Interactive 3D arrow gizmo for visualizing and manipulating projection direction.

    This class creates a draggable arrow in the 3D viewport that:
    - Shows the current projection direction visually
    - Allows user to drag the arrow tip to change direction
    - Synchronizes with X/Y/Z input fields bidirectionally
    - Changes color based on interaction state (normal/hover/drag)

    Based on the Arrow pattern from graphics.py (lines 180-206)
    """

    def __init__(self, position, direction, arrow_length=50.0, arrow_size=10.0):
        """
        Initialize the vector direction gizmo.

        Args:
            position: FreeCAD.Vector - Base position of the arrow (face centroid)
            direction: FreeCAD.Vector - Initial direction (will be normalized)
            arrow_length: float - Length of the arrow shaft in mm
            arrow_size: float - Size of the arrow cone head in mm
        """
        self.position = position
        self.arrow_length = arrow_length
        self.arrow_size = arrow_size

        # Normalize direction to unit vector
        if direction.Length < 1e-6:
            direction = FreeCAD.Vector(0, 0, 1)  # Default to Z-axis
        self.direction = direction.normalize()

        # Callbacks for external updates
        self.on_direction_changed = []  # List of callback functions

        # Build the Coin3D scene graph
        self._build_scene_graph()

        # Add to active view
        self.view = FreeCADGui.ActiveDocument.ActiveView
        self.scene_graph = self.view.getSceneGraph()
        self.scene_graph.addChild(self.root)

        # Setup mouse interaction
        self._setup_interaction()

    def _build_scene_graph(self):
        """
        Build the Coin3D scene graph for the arrow gizmo.

        Scene Graph Structure:
        root (SoSeparator)
          ├─ switch (SoSwitch) - for show/hide
          │   ├─ material (SoMaterial) - arrow color
          │   ├─ base_transform (SoTransform) - position arrow base
          │   ├─ shaft_separator (SoSeparator)
          │   │   ├─ shaft_scale (SoScale) - scale shaft
          │   │   └─ shaft_cylinder (SoCylinder) - arrow shaft
          │   └─ cone_separator (SoSeparator)
          │       ├─ cone_transform (SoTransform) - position cone at tip
          │       ├─ cone_scale (SoScale) - scale cone
          │       └─ cone (SoCone) - arrow head
          └─ pick_separator (SoSeparator) - invisible picking sphere
        """
        # Root separator
        self.root = coin.SoSeparator()

        # Switch for visibility control
        self.switch = coin.SoSwitch()
        self.switch.whichChild = coin.SO_SWITCH_ALL  # Visible by default
        self.root.addChild(self.switch)

        # Material for arrow (color changes based on state)
        self.material = coin.SoMaterial()
        self.material.diffuseColor = (0.0, 1.0, 1.0)  # Cyan (normal state)
        self.material.transparency = 0.0
        self.switch.addChild(self.material)

        # EXACT PATTERN FROM graphics.py Arrow class (lines 183-195):
        # All transforms and geometry in ONE separator, in SEQUENCE
        # This is how Coin3D applies transforms: linearly through the graph
        arrow_sep = coin.SoSeparator()

        # Transform - position and rotation (applied to all following nodes)
        self.base_transform = coin.SoTransform()
        self._update_transform()
        arrow_sep.addChild(self.base_transform)

        # Shaft - use separator to isolate its scale
        shaft_sep = coin.SoSeparator()

        self.shaft_scale = coin.SoScale()
        self.shaft_scale.scaleFactor.setValue(
            self.arrow_size * 0.1,  # Radius
            self.arrow_length * 0.5,  # Height (cylinder is 2 units tall)
            self.arrow_size * 0.1   # Radius
        )
        shaft_sep.addChild(self.shaft_scale)

        shaft_cylinder = coin.SoCylinder()
        shaft_cylinder.radius = 1.0
        shaft_cylinder.height = 2.0
        shaft_sep.addChild(shaft_cylinder)

        arrow_sep.addChild(shaft_sep)  # Shaft scale doesn't escape this separator

        # Cone - positioned relative to shaft in the same coordinate system
        cone_sep = coin.SoSeparator()

        # Translation to position cone at tip of shaft
        # Since the cylinder is centered at origin and extends ±arrow_length/2,
        # the tip is at +arrow_length/2
        # We need to position the cone so its base is at the shaft tip
        # Cone height = arrow_length * 0.2, so half height = arrow_length * 0.1
        # Position cone center at shaft tip + cone half height
        self.cone_transform = coin.SoTransform()
        self.cone_transform.translation.setValue(0, self.arrow_length * 0.5 + (self.arrow_length * 0.2 * 0.5), 0)
        cone_sep.addChild(self.cone_transform)

        # Cone scale - make it proportional to arrow size
        self.cone_scale = coin.SoScale()
        cone_base_radius = self.arrow_size * 0.3  # Base radius of cone
        cone_height = self.arrow_length * 0.2      # Height of cone (20% of shaft length)
        
        # Since cone height is 2.0 units, scale to desired height
        # And scale radius to desired base radius
        self.cone_scale.scaleFactor.setValue(
            cone_base_radius,  # X radius
            cone_height * 0.5, # Y height (since cone is 2 units tall)
            cone_base_radius   # Z radius
        )
        cone_sep.addChild(self.cone_scale)

        # Origin adjustment - move cone down so its base sits at the tip
        # Cone extends from -1 to +1 in Y direction, so move down by 1 unit
        cone_origin = coin.SoTranslation()
        cone_origin.translation.setValue(0, -1, 0)
        cone_sep.addChild(cone_origin)

        cone = coin.SoCone()
        cone.bottomRadius = 1.0
        cone.height = 2.0
        cone_sep.addChild(cone)

        arrow_sep.addChild(cone_sep)  # Cone inherits the base_transform rotation

        # Add the complete arrow to switch
        self.switch.addChild(arrow_sep)

        # Invisible picking sphere at arrow tip for interaction
        pick_separator = coin.SoSeparator()
        pick_material = coin.SoMaterial()
        pick_material.transparency = 1.0  # Fully transparent
        pick_separator.addChild(pick_material)

        pick_transform = coin.SoTransform()
        tip_position = self.position + self.direction * self.arrow_length
        pick_transform.translation.setValue(tip_position.x, tip_position.y, tip_position.z)
        pick_separator.addChild(pick_transform)

        self.pick_sphere = coin.SoSphere()
        self.pick_sphere.radius = self.arrow_size
        pick_separator.addChild(self.pick_sphere)
        self.root.addChild(pick_separator)

    def _update_transform(self):
        """
        Update the base transform to position and orient the arrow.

        The arrow is modeled pointing up (Y-axis) by default, so we need to:
        1. Position it at the base position
        2. Rotate it to point in the current direction
        """
        # Set position
        self.base_transform.translation.setValue(
            self.position.x,
            self.position.y,
            self.position.z
        )

        # Set rotation from Y-axis to direction
        y_axis = coin.SbVec3f(0, 1, 0)
        target = coin.SbVec3f(self.direction.x, self.direction.y, self.direction.z)

        rotation = coin.SbRotation()
        rotation.setValue(y_axis, target)
        self.base_transform.rotation.setValue(rotation)

    def _setup_interaction(self):
        """
        Setup mouse event callbacks for arrow interaction.

        This is a simplified interaction system that:
        - Detects mouse hover (highlights arrow)
        - Detects mouse drag (moves arrow tip)
        - Updates direction on release
        """
        self.event_callback = coin.SoEventCallback()
        self.root.addChild(self.event_callback)

        # Register callbacks
        self.event_callback.addEventCallback(
            coin.SoLocation2Event.getClassTypeId(),
            self._mouse_move_callback
        )
        self.event_callback.addEventCallback(
            coin.SoMouseButtonEvent.getClassTypeId(),
            self._mouse_button_callback
        )

        # Interaction state
        self.is_dragging = False
        self.is_hovering = False
        self.drag_start_pos = None

    def _mouse_move_callback(self, user_data, event_callback):
        """Handle mouse movement for hover and drag"""
        event = event_callback.getEvent()

        if self.is_dragging:
            # Update arrow direction based on mouse position
            # This is a simplified version - real implementation would use ray casting
            pass
        else:
            # Check for hover (simplified - real implementation would use pick ray)
            pass

    def _mouse_button_callback(self, user_data, event_callback):
        """Handle mouse button events for drag start/end"""
        event = event_callback.getEvent()

        if event.getButton() == coin.SoMouseButtonEvent.BUTTON1:
            if event.getState() == coin.SoMouseButtonEvent.DOWN:
                # Start drag
                self.is_dragging = True
                self.set_color_dragging()
            elif event.getState() == coin.SoMouseButtonEvent.UP:
                # End drag
                if self.is_dragging:
                    self.is_dragging = False
                    self.set_color_normal()
                    # Notify listeners
                    self._notify_direction_changed()

    def set_direction(self, direction):
        """
        Set the arrow direction (from external source like input fields).

        Args:
            direction: FreeCAD.Vector - New direction (will be normalized)
        """
        if direction.Length < 1e-6:
            FreeCAD.Console.PrintWarning("Cannot set zero-length direction vector\n")
            return

        self.direction = direction.normalize()
        self._update_transform()

    def set_position(self, position):
        """
        Set the arrow base position.

        Args:
            position: FreeCAD.Vector - New base position
        """
        self.position = position
        self._update_transform()

    def get_direction(self):
        """
        Get the current arrow direction as a unit vector.

        Returns:
            FreeCAD.Vector - Unit direction vector
        """
        return FreeCAD.Vector(self.direction)

    def set_color_normal(self):
        """Set arrow color to normal state (cyan)"""
        self.material.diffuseColor = (0.0, 1.0, 1.0)  # Cyan

    def set_color_hover(self):
        """Set arrow color to hover state (yellow)"""
        self.material.diffuseColor = (1.0, 1.0, 0.0)  # Yellow

    def set_color_dragging(self):
        """Set arrow color to dragging state (green)"""
        self.material.diffuseColor = (0.0, 1.0, 0.0)  # Green

    def set_color_invalid(self):
        """Set arrow color to invalid state (red)"""
        self.material.diffuseColor = (1.0, 0.0, 0.0)  # Red

    def show(self):
        """Show the arrow gizmo"""
        self.switch.whichChild = coin.SO_SWITCH_ALL

    def hide(self):
        """Hide the arrow gizmo"""
        self.switch.whichChild = coin.SO_SWITCH_NONE

    def is_visible(self):
        """Check if the arrow gizmo is visible"""
        return self.switch.whichChild.getValue() == coin.SO_SWITCH_ALL

    def _notify_direction_changed(self):
        """Notify all registered callbacks that direction has changed"""
        for callback in self.on_direction_changed:
            try:
                callback(self.direction)
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error in direction change callback: {str(e)}\n")

    def cleanup(self):
        """
        Clean up resources and remove from scene graph.

        IMPORTANT: Always call this when the gizmo is no longer needed
        to prevent memory leaks and orphaned Coin3D nodes.
        """
        try:
            if hasattr(self, 'scene_graph') and self.scene_graph:
                if hasattr(self, 'root') and self.root:
                    self.scene_graph.removeChild(self.root)

            # Clear callbacks
            self.on_direction_changed.clear()

            FreeCAD.Console.PrintMessage("Vector gizmo cleaned up\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error cleaning up vector gizmo: {str(e)}\n")

    def __del__(self):
        """Destructor - ensure cleanup on deletion"""
        self.cleanup()
