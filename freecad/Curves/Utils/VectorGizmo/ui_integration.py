# -*- coding: utf-8 -*-
'''
Standardized UI integration helper for VectorGizmo.

This class provides a standardized way to integrate the VectorGizmo with
Qt dialogs and input fields. It handles bidirectional synchronization between
the 3D gizmo and X/Y/Z input fields, as well as common UI patterns.

Example:
    # In your dialog class:
    from freecad.Curves.Utils.VectorGizmo import VectorGizmo, VectorGizmoUI
    
    def __init__(self):
        # ... other initialization ...
        
        # Create gizmo
        self.vector_gizmo = VectorGizmo(
            position=FreeCAD.Vector(0, 0, 0),
            direction=FreeCAD.Vector(1, 0, 0)
        )
        
        # Create UI integration helper
        self.vector_ui = VectorGizmoUI(
            gizmo=self.vector_gizmo,
            dialog=self,
            x_field=self.form.vectorXEdit,
            y_field=self.form.vectorYEdit,
            z_field=self.form.vectorZEdit,
            smart_default_enabled=True
        )
    
    def cleanup(self):
        # Clean up both gizmo and UI helper
        if hasattr(self, 'vector_ui'):
            self.vector_ui.cleanup()
'''

import FreeCAD
from PySide import QtCore


class VectorGizmoUI:
    """
    Standardized UI integration helper for VectorGizmo.
    
    This class handles the common patterns for integrating a VectorGizmo
    with Qt input fields, including bidirectional synchronization, smart defaults,
    and cleanup management.
    
    Args:
        gizmo (VectorGizmo): The VectorGizmo instance to integrate
        dialog: The parent dialog object (usually 'self' in dialog classes)
        x_field: Qt input field for X component
        y_field: Qt input field for Y component  
        z_field: Qt input field for Z component
        smart_default_enabled (bool): Enable smart default for zero vectors
        smart_default_callback (callable): Function to get default direction
    """

    def __init__(self, gizmo, dialog, x_field, y_field, z_field, 
                 smart_default_enabled=True, smart_default_callback=None):
        self.gizmo = gizmo
        self.dialog = dialog
        self.x_field = x_field
        self.y_field = y_field
        self.z_field = z_field
        self.smart_default_enabled = smart_default_enabled
        self.smart_default_callback = smart_default_callback

        # Connect input field signals
        self._setup_field_connections()

        # Set up gizmo callback
        self.gizmo.on_direction_changed.append(self._on_gizmo_direction_changed)

        # Initialize fields with current gizmo direction
        self._update_fields_from_gizmo()

    def _setup_field_connections(self):
        """Connect Qt signals from input fields."""
        self.x_field.editingFinished.connect(self._on_field_changed)
        self.y_field.editingFinished.connect(self._on_field_changed)
        self.z_field.editingFinished.connect(self._on_field_changed)

    def _on_field_changed(self):
        """
        Handle input field changes.
        
        Called when user finishes editing any of the X/Y/Z fields.
        Updates the gizmo direction and applies smart default if needed.
        """
        try:
            # Get values from fields
            x_text = self.x_field.text().strip()
            y_text = self.y_field.text().strip()
            z_text = self.z_field.text().strip()

            x = float(x_text) if x_text else 0.0
            y = float(y_text) if y_text else 0.0
            z = float(z_text) if z_text else 0.0

            direction = FreeCAD.Vector(x, y, z)

            # Apply smart default if enabled and vector is zero
            if self.smart_default_enabled and direction.Length < 1e-6:
                direction = self._get_smart_default()
                if direction:
                    self._update_fields_from_vector(direction)
                    FreeCAD.Console.PrintMessage("Applied smart default for zero vector\n")

            # Update gizmo
            self.gizmo.set_direction(direction)

            # Notify dialog of change (if dialog has this method)
            if hasattr(self.dialog, 'on_vector_direction_changed'):
                self.dialog.on_vector_direction_changed(direction)

        except ValueError as e:
            FreeCAD.Console.PrintWarning(f"Invalid vector input: {str(e)}\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error handling field change: {str(e)}\n")

    def _on_gizmo_direction_changed(self, direction):
        """
        Handle gizmo direction changes.
        
        Called when the gizmo direction changes (e.g., from future 3D manipulation).
        Updates the input fields to match the new direction.
        """
        self._update_fields_from_vector(direction)

    def _update_fields_from_gizmo(self):
        """Update input fields with current gizmo direction."""
        direction = self.gizmo.get_direction()
        self._update_fields_from_vector(direction)

    def _update_fields_from_vector(self, vector):
        """
        Update input fields with values from a vector.
        
        Args:
            vector (FreeCAD.Vector): Vector to display in fields
        """
        # Block signals to prevent recursion
        self.x_field.blockSignals(True)
        self.y_field.blockSignals(True)
        self.z_field.blockSignals(True)

        try:
            self.x_field.setText(f"{vector.x:.3f}")
            self.y_field.setText(f"{vector.y:.3f}")
            self.z_field.setText(f"{vector.z:.3f}")
        finally:
            self.x_field.blockSignals(False)
            self.y_field.blockSignals(False)
            self.z_field.blockSignals(False)

    def _get_smart_default(self):
        """
        Get smart default direction for zero vectors.
        
        Returns:
            FreeCAD.Vector or None: Default direction, or None if unavailable
        """
        # Use custom callback if provided
        if self.smart_default_callback:
            try:
                result = self.smart_default_callback()
                if result and hasattr(result, 'Length') and result.Length > 1e-6:
                    return result
            except Exception as e:
                FreeCAD.Console.PrintWarning(f"Smart default callback failed: {str(e)}\n")

        # Try common default sources
        try:
            # Check if dialog has a method to get face normal
            if hasattr(self.dialog, '_get_face_normal_for_vector'):
                return self.dialog._get_face_normal_for_vector()
            
            # Check if dialog has a face object
            if hasattr(self.dialog, 'logic') and hasattr(self.dialog.logic, 'face_object'):
                face_obj = self.dialog.logic.face_object
                if face_obj:
                    face_shape = face_obj[0].Shape.getElement(face_obj[1])
                    u_mid = (face_shape.ParameterRange[0] + face_shape.ParameterRange[1]) / 2.0
                    v_mid = (face_shape.ParameterRange[2] + face_shape.ParameterRange[3]) / 2.0
                    return face_shape.normalAt(u_mid, v_mid)
            
            # Fall back to Z-axis
            return FreeCAD.Vector(0, 0, 1)
            
        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Could not determine smart default: {str(e)}\n")
            return None

    # Public API Methods

    def get_vector(self):
        """
        Get current vector from input fields.
        
        Returns:
            FreeCAD.Vector: Current vector (normalized)
        """
        try:
            x_text = self.x_field.text().strip()
            y_text = self.y_field.text().strip()
            z_text = self.z_field.text().strip()

            x = float(x_text) if x_text else 0.0
            y = float(y_text) if y_text else 0.0
            z = float(z_text) if z_text else 0.0

            vector = FreeCAD.Vector(x, y, z)
            
            # Apply smart default if needed
            if self.smart_default_enabled and vector.Length < 1e-6:
                smart_default = self._get_smart_default()
                if smart_default:
                    vector = smart_default
            
            return vector.normalize()
            
        except (ValueError, AttributeError):
            return FreeCAD.Vector(0, 0, 1)  # Safe default

    def set_vector(self, vector):
        """
        Set both the input fields and gizmo to a new vector.
        
        Args:
            vector (FreeCAD.Vector): New vector to set
        """
        if vector.Length > 1e-6:
            self.gizmo.set_direction(vector)
            self._update_fields_from_vector(vector)

    def set_fields_enabled(self, enabled):
        """
        Enable or disable the input fields.
        
        Args:
            enabled (bool): Whether to enable the fields
        """
        self.x_field.setEnabled(enabled)
        self.y_field.setEnabled(enabled)
        self.z_field.setEnabled(enabled)

    def show_gizmo(self):
        """Show the gizmo."""
        self.gizmo.show()

    def hide_gizmo(self):
        """Hide the gizmo."""
        self.gizmo.hide()

    def is_gizmo_visible(self):
        """
        Check if the gizmo is visible.
        
        Returns:
            bool: True if visible, False if hidden
        """
        return self.gizmo.is_visible()

    def set_gizmo_position(self, position):
        """
        Set the gizmo position.
        
        Args:
            position (FreeCAD.Vector): New position for gizmo base
        """
        self.gizmo.set_position(position)

    def set_gizmo_scaling(self, arrow_length=None, arrow_size=None):
        """
        Set gizmo scaling parameters.
        
        Args:
            arrow_length (float, optional): New arrow length in mm
            arrow_size (float, optional): New arrow size in mm
        """
        if arrow_length is not None:
            self.gizmo.set_arrow_length(arrow_length)
        if arrow_size is not None:
            self.gizmo.set_arrow_size(arrow_size)

    def clear_fields(self):
        """Clear all input fields."""
        self.x_field.setText("")
        self.y_field.setText("")
        self.z_field.setText("")

    def validate_fields(self):
        """
        Validate the current input fields.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            x_text = self.x_field.text().strip()
            y_text = self.y_field.text().strip()
            z_text = self.z_field.text().strip()

            x = float(x_text) if x_text else 0.0
            y = float(y_text) if y_text else 0.0
            z = float(z_text) if z_text else 0.0

            vector = FreeCAD.Vector(x, y, z)
            
            if vector.Length < 1e-6:
                if self.smart_default_enabled:
                    return (True, "Smart default will be applied")
                else:
                    return (False, "Vector cannot be zero length")
            
            return (True, "Valid vector")
            
        except ValueError as e:
            return (False, f"Invalid number format: {str(e)}")
        except Exception as e:
            return (False, f"Validation error: {str(e)}")

    # Color and Appearance

    def set_gizmo_color(self, color):
        """
        Set the gizmo color.
        
        Args:
            color (tuple): RGB color tuple (r, g, b) with values 0.0-1.0
        """
        self.gizmo.set_color(color)

    def set_gizmo_normal(self):
        """Set gizmo to normal color state."""
        self.gizmo.set_color_normal()

    def set_gizmo_hover(self):
        """Set gizmo to hover color state."""
        self.gizmo.set_color_hover()

    def set_gizmo_dragging(self):
        """Set gizmo to dragging color state."""
        self.gizmo.set_color_dragging()

    def set_gizmo_invalid(self):
        """Set gizmo to invalid color state."""
        self.gizmo.set_color_invalid()

    # Cleanup

    def cleanup(self):
        """
        Clean up resources.
        
        This should be called when the dialog is closing to properly
        clean up both the gizmo and disconnect signals.
        """
        try:
            # Disconnect signals
            try:
                self.x_field.editingFinished.disconnect(self._on_field_changed)
                self.y_field.editingFinished.disconnect(self._on_field_changed)
                self.z_field.editingFinished.disconnect(self._on_field_changed)
            except:
                pass  # Signals might already be disconnected

            # Remove callback from gizmo
            if self._on_gizmo_direction_changed in self.gizmo.on_direction_changed:
                self.gizmo.on_direction_changed.remove(self._on_gizmo_direction_changed)

            # Clean up gizmo
            self.gizmo.cleanup()

            FreeCAD.Console.PrintMessage("VectorGizmoUI cleaned up\n")
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error cleaning up VectorGizmoUI: {str(e)}\n")

    def __del__(self):
        """Destructor - ensure cleanup on deletion."""
        self.cleanup()


# Utility Functions

def create_standard_vector_ui(dialog, gizmo_name="vector", 
                            smart_default_enabled=True,
                            smart_default_callback=None):
    """
    Utility function to create a standard vector UI setup.
    
    This is a convenience function for common patterns where the dialog
    follows standard naming conventions for vector fields.
    
    Args:
        dialog: The parent dialog object
        gizmo_name (str): Base name for gizmo and fields (e.g., "vector")
        smart_default_enabled (bool): Enable smart default for zero vectors
        smart_default_callback (callable): Function to get default direction
        
    Returns:
        tuple: (gizmo, ui_helper) - The created gizmo and UI helper
        
    Example:
        # In dialog __init__:
        self.vector_gizmo, self.vector_ui = create_standard_vector_ui(
            self, 
            gizmo_name="vector",
            smart_default_callback=self._get_face_normal
        )
    """
    try:
        # Try to access fields using standard naming convention
        x_field = getattr(dialog.form, f"{gizmo_name.capitalize()}XEdit")
        y_field = getattr(dialog.form, f"{gizmo_name.capitalize()}YEdit")
        z_field = getattr(dialog.form, f"{gizmo_name.capitalize()}ZEdit")
        
        # Create gizmo with default parameters
        from .vector_gizmo import VectorGizmo
        gizmo = VectorGizmo(
            position=FreeCAD.Vector(0, 0, 0),
            direction=FreeCAD.Vector(1, 0, 0)
        )
        
        # Create UI helper
        ui_helper = VectorGizmoUI(
            gizmo=gizmo,
            dialog=dialog,
            x_field=x_field,
            y_field=y_field,
            z_field=z_field,
            smart_default_enabled=smart_default_enabled,
            smart_default_callback=smart_default_callback
        )
        
        return gizmo, ui_helper
        
    except AttributeError as e:
        FreeCAD.Console.PrintError(f"Could not create standard vector UI: {str(e)}\n")
        FreeCAD.Console.PrintError("Ensure dialog has fields named {gizmo}XEdit, {gizmo}YEdit, {gizmo}ZEdit\n")
        return None, None
