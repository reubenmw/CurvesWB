# Task panel UI and workflow management for blend curve dialog

import os
import FreeCAD
import FreeCADGui
from PySide import QtGui, QtCore
from PySide.QtCore import Qt

from .blend_logic import BlendCurveLogic
from .selection_handlers import (
    SelectionGate,
    EdgeSelectionObserver,
    BlendPointSelectionObserver,
)
from .preview_overlay import BlendCurvePreview

# Translation function
translate = FreeCAD.Qt.translate


class BlendCurveTaskPanel:
    """Task panel for creating blend curves between two edges"""

    def __init__(self, edit_object=None):
        """Initialize the task panel.

        Args:
            edit_object: Optional existing BlendCurve object to edit
        """
        self.logic = BlendCurveLogic()
        self.preview = BlendCurvePreview()
        self.edit_object = edit_object  # Store for later use

        # Load the UI form from .ui file (Qt Designer interface)
        self.form = FreeCADGui.PySideUic.loadUi(
            os.path.join(os.path.dirname(__file__), "blend_curve_dialog.ui")
        )

        # UI References - Section 1: First Curve
        self.curve1_line_edit = self.form.curve1LineEdit
        self.curve1_select_button = self.form.curve1SelectButton
        self.curve1_scale_slider = self.form.curve1ScaleSlider
        self.curve1_scale_spinbox = self.form.curve1ScaleSpinBox
        self.curve1_flip_scale_button = self.form.curve1FlipScaleButton
        self.curve1_position_slider = self.form.curve1PositionSlider
        self.curve1_position_spinbox = self.form.curve1PositionSpinBox
        self.curve1_flip_position_button = self.form.curve1FlipPositionButton
        self.curve1_continuity_combobox = self.form.curve1ContinuityComboBox

        # UI References - Section 2: Second Curve
        self.curve2_groupbox = self.form.curve2GroupBox
        self.curve2_line_edit = self.form.curve2LineEdit
        self.curve2_select_button = self.form.curve2SelectButton
        self.curve2_scale_slider = self.form.curve2ScaleSlider
        self.curve2_scale_spinbox = self.form.curve2ScaleSpinBox
        self.curve2_flip_scale_button = self.form.curve2FlipScaleButton
        self.curve2_position_slider = self.form.curve2PositionSlider
        self.curve2_position_spinbox = self.form.curve2PositionSpinBox
        self.curve2_flip_position_button = self.form.curve2FlipPositionButton
        self.curve2_continuity_combobox = self.form.curve2ContinuityComboBox

        # UI References - Advanced Options

        self.symmetric_mode_checkbox = self.form.symmetricModeCheckBox
        self.tension_slider = self.form.tensionSlider
        self.tension_value_label = self.form.tensionValueLabel
        self.auto_extend_checkbox = self.form.autoExtendCheckBox

        # UI References - Trim Controls

        self.trim_groupbox = self.form.trimGroupBox
        self.trim1_combobox = self.form.trim1ComboBox
        self.trim2_combobox = self.form.trim2ComboBox

        # UI References - Common

        self.status_label = self.form.statusLabel
        self.apply_button = self.form.applyButton
        self.cancel_button = self.form.cancelButton

        # State Variables

        self.curve1_obj = None
        self.curve1_subname = None
        self.curve1_curve_length = 0.0  # Store actual curve length
        self.curve1_scale_direction = 1  # 1 or -1
        self.curve1_position_direction = 1  # 1 = from start, -1 = from end

        self.curve2_obj = None
        self.curve2_subname = None
        self.curve2_curve_length = 0.0  # Store actual curve length
        self.curve2_scale_direction = 1  # 1 or -1
        self.curve2_position_direction = 1  # 1 = from start, -1 = from end

        self.selection_gate = None
        self.selection_observer = None
        self.active_curve_selection = None  # 'curve1' or 'curve2'

        # Edge highlighting
        self.highlighted_edges = []  # List of (obj, subname) tuples for cleanup

        # Connect Event Handlers

        # Curve 1 Controls
        self.curve1_select_button.clicked.connect(
            lambda: self.start_curve_selection("curve1")
        )
        self.curve1_scale_slider.valueChanged.connect(
            self.on_curve1_scale_slider_changed
        )
        self.curve1_scale_spinbox.valueChanged.connect(
            self.on_curve1_scale_spinbox_changed
        )
        self.curve1_flip_scale_button.clicked.connect(
            lambda: self.flip_scale_direction("curve1")
        )
        self.curve1_position_slider.valueChanged.connect(
            self.on_curve1_position_slider_changed
        )
        self.curve1_position_spinbox.valueChanged.connect(
            self.on_curve1_position_spinbox_changed
        )
        self.curve1_flip_position_button.clicked.connect(
            lambda: self.flip_position("curve1")
        )
        self.curve1_continuity_combobox.currentIndexChanged.connect(
            self.on_curve1_params_changed
        )

        # Curve 2 Controls
        self.curve2_select_button.clicked.connect(
            lambda: self.start_curve_selection("curve2")
        )
        self.curve2_scale_slider.valueChanged.connect(
            self.on_curve2_scale_slider_changed
        )
        self.curve2_scale_spinbox.valueChanged.connect(
            self.on_curve2_scale_spinbox_changed
        )
        self.curve2_flip_scale_button.clicked.connect(
            lambda: self.flip_scale_direction("curve2")
        )
        self.curve2_position_slider.valueChanged.connect(
            self.on_curve2_position_slider_changed
        )
        self.curve2_position_spinbox.valueChanged.connect(
            self.on_curve2_position_spinbox_changed
        )
        self.curve2_flip_position_button.clicked.connect(
            lambda: self.flip_position("curve2")
        )
        self.curve2_continuity_combobox.currentIndexChanged.connect(
            self.on_curve2_params_changed
        )

        # Advanced Options
        self.symmetric_mode_checkbox.toggled.connect(self.on_symmetric_mode_toggled)
        self.tension_slider.valueChanged.connect(self.on_tension_changed)
        self.auto_extend_checkbox.toggled.connect(self.on_auto_extend_toggled)

        # Trim Controls
        self.trim_groupbox.toggled.connect(self.on_trim_enabled_toggled)
        self.trim1_combobox.currentIndexChanged.connect(self.on_trim_params_changed)
        self.trim2_combobox.currentIndexChanged.connect(self.on_trim_params_changed)

        # Buttons
        self.apply_button.clicked.connect(self.on_apply)
        self.cancel_button.clicked.connect(self.on_cancel)

        # Initialize

        # If editing an existing object, load its parameters; otherwise handle pre-selection
        if self.edit_object:
            self.load_from_object()
        else:
            self.handle_pre_selection()

        self.update_ui_state()

    # Pre-Selection Handling

    def handle_pre_selection(self):
        """Handle pre-selected curves when tool is activated"""
        pre_selected = FreeCADGui.Selection.getSelectionEx()

        valid_curves = []
        for sel in pre_selected:
            for subname in sel.SubElementNames:
                if subname.startswith("Edge"):
                    valid_curves.append((sel.Object, subname))
                    if len(valid_curves) >= 2:
                        break
            if len(valid_curves) >= 2:
                break

        if len(valid_curves) >= 2:
            # Auto-populate both curves
            self.set_curve("curve1", valid_curves[0][0], valid_curves[0][1])
            self.set_curve("curve2", valid_curves[1][0], valid_curves[1][1])
            self.update_status(
                translate(
                    "BlendCurve",
                    "Two curves selected. Adjust parameters and click Apply.",
                ),
                "success",
            )
        elif len(valid_curves) == 1:
            # Auto-populate curve 1 only, then auto-start curve 2 selection
            self.set_curve("curve1", valid_curves[0][0], valid_curves[0][1])
            self.update_status(
                translate("BlendCurve", "First curve selected. Select second curve."),
                "info",
            )
            # Automatically start curve 2 selection
            self.start_curve_selection("curve2")
        else:
            # No curves pre-selected - automatically start curve 1 selection
            self.update_status(
                translate("BlendCurve", "Select first curve to begin..."), "info"
            )
            # Automatically start curve 1 selection
            self.start_curve_selection("curve1")

    def load_from_object(self):
        """Load parameters from an existing BlendCurve object for editing"""
        if not self.edit_object:
            return

        try:
            # Check if the object has the required properties
            if not hasattr(self.edit_object, 'Curve1Object') or not hasattr(self.edit_object, 'Curve2Object'):
                FreeCAD.Console.PrintWarning("Object missing blend curve properties, cannot edit\n")
                self.handle_pre_selection()
                return

            # Load Curve 1 parameters
            curve1_obj = self.edit_object.Curve1Object
            curve1_subname = self.edit_object.Curve1SubName
            curve1_scale = self.edit_object.Curve1Scale
            curve1_position = self.edit_object.Curve1Position
            curve1_continuity = self.edit_object.Curve1Continuity

            # Load Curve 2 parameters
            curve2_obj = self.edit_object.Curve2Object
            curve2_subname = self.edit_object.Curve2SubName
            curve2_scale = self.edit_object.Curve2Scale
            curve2_position = self.edit_object.Curve2Position
            curve2_continuity = self.edit_object.Curve2Continuity

            # Set curves in the UI
            if curve1_obj and curve1_subname:
                self.set_curve("curve1", curve1_obj, curve1_subname)
                # Set scale (handle negative values for direction)
                self.curve1_scale_direction = 1 if curve1_scale >= 0 else -1
                self.curve1_scale_spinbox.setValue(abs(curve1_scale))
                # Set position
                self.curve1_position_spinbox.setValue(curve1_position)
                # Set continuity
                self.curve1_continuity_combobox.setCurrentIndex(curve1_continuity)

            if curve2_obj and curve2_subname:
                self.set_curve("curve2", curve2_obj, curve2_subname)
                # Set scale (handle negative values for direction)
                self.curve2_scale_direction = 1 if curve2_scale >= 0 else -1
                self.curve2_scale_spinbox.setValue(abs(curve2_scale))
                # Set position
                self.curve2_position_spinbox.setValue(curve2_position)
                # Set continuity
                self.curve2_continuity_combobox.setCurrentIndex(curve2_continuity)

            self.update_status(
                translate("BlendCurve", "Editing existing blend curve. Adjust parameters and click Apply."),
                "info"
            )

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error loading blend curve parameters: {str(e)}\n")
            import traceback
            FreeCAD.Console.PrintError(traceback.format_exc())
            # Fall back to normal selection mode
            self.handle_pre_selection()

    # Curve Selection

    def start_curve_selection(self, curve_id):
        """Start edge selection mode for curve1 or curve2"""
        self.active_curve_selection = curve_id
        FreeCADGui.Selection.clearSelection()

        # Set up selection gate and observer
        self.cleanup_selection()
        self.selection_gate = SelectionGate("edge")
        FreeCADGui.Selection.addSelectionGate(self.selection_gate)

        self.selection_observer = EdgeSelectionObserver(self, curve_id)
        FreeCADGui.Selection.addObserver(self.selection_observer)

        curve_num = "1" if curve_id == "curve1" else "2"
        self.update_status(
            translate("BlendCurve", f"Select curve {curve_num}..."), "info"
        )

    def on_edge_selected(self, curve_id, obj, subname):
        """Called when an edge is selected"""
        # Validate selection
        if not self.validate_curve_selection(curve_id, obj, subname):
            # Clear the invalid selection and keep selection mode active
            FreeCADGui.Selection.clearSelection()
            # Selection mode stays active - user can try again
            return

        self.set_curve(curve_id, obj, subname)
        self.cleanup_selection()
        self.active_curve_selection = None
        self.update_ui_state()

        # Auto-progression: If curve 1 was just selected and curve 2 is not yet selected,
        # automatically start curve 2 selection
        if curve_id == "curve1" and not self.curve2_obj:
            self.update_status(
                translate("BlendCurve", "First curve selected. Select second curve."),
                "info",
            )
            self.start_curve_selection("curve2")

    def set_curve(self, curve_id, obj, subname):
        """Set the curve object and update UI"""
        # Get the edge shape to calculate length
        try:
            edge_shape = obj.Shape.getElement(subname)
            curve_length = edge_shape.Length
        except:
            curve_length = 100.0  # Default fallback

        if curve_id == "curve1":
            self.curve1_obj = obj
            self.curve1_subname = subname
            self.curve1_curve_length = curve_length
            display_text = f"{obj.Label}.{subname}"
            self.curve1_line_edit.setText(display_text)
            # Update position spinbox range
            self.curve1_position_spinbox.setMaximum(curve_length)
            # Highlight the edge (Curve 1)
            self.highlight_edge(obj, subname, "curve1")
        else:  # curve2
            self.curve2_obj = obj
            self.curve2_subname = subname
            self.curve2_curve_length = curve_length
            display_text = f"{obj.Label}.{subname}"
            self.curve2_line_edit.setText(display_text)
            # Update position spinbox range
            self.curve2_position_spinbox.setMaximum(curve_length)
            # Highlight the edge (Curve 2)
            self.highlight_edge(obj, subname, "curve2")

            # When both curves are selected, update scale slider ranges
            if self.curve1_obj is not None:
                self.update_scale_slider_ranges()
                # Trigger preview now that both curves are available
                self.update_preview()

    def update_scale_slider_ranges(self):
        """
        Update scale slider ranges based on the distance between the two curves.
        Called automatically when both curves are selected.
        """
        # Get edge shapes and calculate distance
        edge1 = self.curve1_obj.Shape.getElement(self.curve1_subname)
        edge2 = self.curve2_obj.Shape.getElement(self.curve2_subname)
        distance = edge1.distToShape(edge2)[0]

        # Calculate scale ranges based on distance
        if distance < 1.0:
            min_scale = 0.1
            max_scale = 10.0
        else:
            min_scale = distance * 0.1
            max_scale = distance * 3.0

        # Convert to slider units (multiply by 100) and update ranges
        min_slider = int(min_scale * 100)
        max_slider = int(max_scale * 100)

        self.curve1_scale_slider.setMinimum(min_slider)
        self.curve1_scale_slider.setMaximum(max_slider)
        self.curve2_scale_slider.setMinimum(min_slider)
        self.curve2_scale_slider.setMaximum(max_slider)

        # Sync sliders to current spinbox values (with signal blocking)
        curve1_current = self.curve1_scale_spinbox.value()
        curve2_current = self.curve2_scale_spinbox.value()

        self.curve1_scale_slider.blockSignals(True)
        self.curve1_scale_slider.setValue(int(curve1_current * 100))
        self.curve1_scale_slider.blockSignals(False)

        self.curve2_scale_slider.blockSignals(True)
        self.curve2_scale_slider.setValue(int(curve2_current * 100))
        self.curve2_scale_slider.blockSignals(False)

        FreeCAD.Console.PrintMessage(
            f"Scale ranges: {min_scale:.2f}-{max_scale:.2f} (distance: {distance:.2f}mm)\n"
        )

    def validate_curve_selection(self, curve_id, obj, subname):
        """Validate curve selection and show appropriate alerts"""
        # Check if it's actually a curve/edge
        if not subname.startswith("Edge"):
            self.update_status(
                translate("BlendCurve", "⚠️ Selected object is not a curve"), "error"
            )
            return False

        # Check if same curve selected twice
        other_obj = self.curve2_obj if curve_id == "curve1" else self.curve1_obj
        other_subname = (
            self.curve2_subname if curve_id == "curve1" else self.curve1_subname
        )

        if other_obj is not None and obj == other_obj and subname == other_subname:
            self.update_status(
                translate("BlendCurve", "⚠️ Cannot use the same curve twice"), "error"
            )
            return False

        # Validate for degenerate curves
        try:
            edge = obj.Shape.getElement(subname)

            # Check if edge has valid length
            if edge.Length < 0.001:  # Less than 0.001mm is considered degenerate
                self.update_status(
                    translate("BlendCurve", "⚠️ Selected curve is too small or degenerate"), "error"
                )
                return False

            # Check if edge has valid parameter range
            if hasattr(edge, 'FirstParameter') and hasattr(edge, 'LastParameter'):
                param_range = abs(edge.LastParameter - edge.FirstParameter)
                if param_range < 1e-7:  # Nearly zero parameter range
                    self.update_status(
                        translate("BlendCurve", "⚠️ Selected curve has invalid parameter range"), "error"
                    )
                    return False

        except Exception as e:
            self.update_status(
                translate("BlendCurve", f"⚠️ Error validating curve: {str(e)}"), "error"
            )
            return False

        # Validate curve compatibility (both curves must be valid edges)
        try:
            edge = obj.Shape.getElement(subname)
            # Ensure it's actually a curve (has Curve property)
            if not hasattr(edge, 'Curve'):
                self.update_status(
                    translate("BlendCurve", "⚠️ Selected element is not a valid curve"), "error"
                )
                return False
        except Exception as e:
            self.update_status(
                translate("BlendCurve", f"⚠️ Invalid curve selection: {str(e)}"), "error"
            )
            return False

        return True

    def highlight_edge(self, obj, subname, curve_id):
        """
        Highlight an edge with a theme-aware color.

        Args:
            obj: FreeCAD object containing the edge
            subname: Subobject name (e.g., "Edge1")
            curve_id: "curve1" or "curve2" to determine which color to use
        """
        try:
            # Get theme-aware highlight colors from FreeCAD preferences
            color = self._get_highlight_color(curve_id)

            # Add to selection with highlight color
            # FreeCAD will show the edge in the specified color
            FreeCADGui.Selection.addSelection(obj, subname)

            # Store for cleanup
            self.highlighted_edges.append((obj, subname))

            # Set the highlight color on the object's view provider
            if hasattr(obj, "ViewObject") and obj.ViewObject:
                # Store original line color if not already stored
                if not hasattr(self, "_original_line_colors"):
                    self._original_line_colors = {}

                if obj.Name not in self._original_line_colors:
                    self._original_line_colors[obj.Name] = obj.ViewObject.LineColor

                # Set temporary highlight color
                obj.ViewObject.LineColor = color
                obj.ViewObject.LineWidth = 3.0  # Make it thicker for visibility

        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Could not highlight edge: {str(e)}\n")

    def _get_highlight_color(self, curve_id):
        """
        Get theme-aware highlight color for the specified curve.

        Args:
            curve_id: "curve1" or "curve2"

        Returns:
            RGB tuple (r, g, b) with values 0.0-1.0
        """
        try:
            # Try to get FreeCAD's selection color from preferences
            param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View")

            # SelectionColor is stored as unsigned integer (RGBA packed)
            selection_color_int = param.GetUnsigned(
                "SelectionColor", 0x1CAD1C00
            )  # Default green

            # Convert packed integer to RGB (0.0-1.0 range)
            # Format: 0xRRGGBBAA
            r = ((selection_color_int >> 24) & 0xFF) / 255.0
            g = ((selection_color_int >> 16) & 0xFF) / 255.0
            b = ((selection_color_int >> 8) & 0xFF) / 255.0

            # For curve2, use a slightly different shade (more blue)
            if curve_id == "curve2":
                # Shift towards blue
                return (r * 0.5, g * 0.7, min(1.0, b * 1.3))
            else:
                return (r, g, b)

        except Exception as e:
            FreeCAD.Console.PrintWarning(
                f"Could not get theme color, using fallback: {str(e)}\n"
            )
            # Fallback colors if preference reading fails
            if curve_id == "curve2":
                return (0.0, 0.5, 1.0)  # Blue
            else:
                return (0.0, 1.0, 0.0)  # Green

    def clear_highlights(self):
        """Remove all edge highlights"""
        try:
            # Restore original line colors
            if hasattr(self, "_original_line_colors"):
                for obj_name, color in self._original_line_colors.items():
                    obj = FreeCAD.ActiveDocument.getObject(obj_name)
                    if obj and hasattr(obj, "ViewObject") and obj.ViewObject:
                        obj.ViewObject.LineColor = color
                        obj.ViewObject.LineWidth = 2.0  # Restore default width

                self._original_line_colors = {}

            # Clear selection
            FreeCADGui.Selection.clearSelection()

            # Clear tracking list
            self.highlighted_edges = []

        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Could not clear highlights: {str(e)}\n")

    # UI State Management & Conditional Rendering

    def update_ui_state(self):
        """Update UI state based on current selections and settings"""
        # Section 2 (Curve 2) - Enable only if Curve 1 is selected
        curve1_selected = self.curve1_obj is not None
        self.curve2_groupbox.setEnabled(curve1_selected)

        # Section 3 (Trim) - Enable only if both curves are selected
        both_curves_selected = curve1_selected and self.curve2_obj is not None
        self.trim_groupbox.setEnabled(both_curves_selected)

        # Apply button - Enable only if both curves selected and all validation passes
        self.update_apply_button()

        # Update status message
        if not curve1_selected:
            self.update_status(
                translate("BlendCurve", "Select first curve to begin..."), "info"
            )
        elif not self.curve2_obj:
            self.update_status(
                translate("BlendCurve", "Select second curve..."), "info"
            )

    def update_apply_button(self):
        """Update apply button enabled/disabled state"""
        can_apply = (
            # Both curves must be selected
            self.curve1_obj is not None
            and self.curve2_obj is not None
            # Scale values must be non-zero (can be negative for direction flip)
            and self.curve1_scale_spinbox.value() != 0
            and self.curve2_scale_spinbox.value() != 0
            # Position values must be within valid range
            and 0 <= self.curve1_position_spinbox.value() <= self.curve1_curve_length
            and 0 <= self.curve2_position_spinbox.value() <= self.curve2_curve_length
            # Curves must not be the same
            and not (self.curve1_obj == self.curve2_obj and self.curve1_subname == self.curve2_subname)
        )
        self.apply_button.setEnabled(can_apply)

    # Curve 1 Event Handlers

    def on_curve1_scale_slider_changed(self, value):
        """Update scale spinbox when slider moves"""
        # Convert slider value (integer) to real scale value
        scale_value = value / 100.0

        # Block spinbox signals to prevent circular update
        self.curve1_scale_spinbox.blockSignals(True)
        self.curve1_scale_spinbox.setValue(scale_value)
        self.curve1_scale_spinbox.blockSignals(False)

        # Trigger parameter change handler
        self.on_curve1_params_changed()

    def on_curve1_scale_spinbox_changed(self, value):
        """Update scale slider when spinbox changes"""
        # Convert real scale value to slider value (integer)
        slider_value = int(value * 100)

        # Block slider signals to prevent circular update
        self.curve1_scale_slider.blockSignals(True)
        self.curve1_scale_slider.setValue(slider_value)
        self.curve1_scale_slider.blockSignals(False)

        # Trigger parameter change handler
        self.on_curve1_params_changed()

    def on_curve1_position_slider_changed(self, value):
        """Update position spinbox when slider moves (slider: 0-100 maps to 0-length)"""
        if self.curve1_curve_length > 0:
            position_mm = (value / 100.0) * self.curve1_curve_length
            # Block signals to prevent circular updates
            self.curve1_position_spinbox.blockSignals(True)
            self.curve1_position_spinbox.setValue(position_mm)
            self.curve1_position_spinbox.blockSignals(False)

        self.on_curve1_params_changed()

    def on_curve1_position_spinbox_changed(self, value):
        """Update position slider when spinbox changes"""
        if self.curve1_curve_length > 0:
            slider_value = int((value / self.curve1_curve_length) * 100)
            # Block signals to prevent circular updates
            self.curve1_position_slider.blockSignals(True)
            self.curve1_position_slider.setValue(slider_value)
            self.curve1_position_slider.blockSignals(False)

        self.on_curve1_params_changed()

    def flip_scale_direction(self, curve_id):
        """Flip the scale direction for the specified curve"""
        if curve_id == "curve1":
            self.curve1_scale_direction *= -1
            FreeCAD.Console.PrintMessage(
                f"Curve 1 scale direction: {self.curve1_scale_direction}\n"
            )
        else:
            self.curve2_scale_direction *= -1
            FreeCAD.Console.PrintMessage(
                f"Curve 2 scale direction: {self.curve2_scale_direction}\n"
            )

        # Trigger preview update
        self.update_preview()

    def flip_position(self, curve_id):
        """
        Flip position measurement from start/end of curve.
        E.g., 10mm from start becomes 10mm from end (value stays 10mm).
        """
        if curve_id == "curve1":
            # Toggle direction flag
            self.curve1_position_direction *= -1
            FreeCAD.Console.PrintMessage(
                f"Curve 1 position direction: {'from end' if self.curve1_position_direction == -1 else 'from start'}\n"
            )
        else:
            # Toggle direction flag
            self.curve2_position_direction *= -1
            FreeCAD.Console.PrintMessage(
                f"Curve 2 position direction: {'from end' if self.curve2_position_direction == -1 else 'from start'}\n"
            )

        # Trigger preview update to show the new position
        self.update_preview()

    def on_curve1_params_changed(self):
        """Called when any curve 1 parameter changes"""
        # If symmetric mode is on, mirror to curve 2
        if self.symmetric_mode_checkbox.isChecked():
            self.mirror_curve1_to_curve2()

        # Trigger preview update
        self.update_preview()

    # Curve 2 Event Handlers

    def on_curve2_scale_slider_changed(self, value):
        """Update scale spinbox when slider moves"""
        # Convert slider value (integer) to real scale value
        scale_value = value / 100.0

        # Block spinbox signals to prevent circular update
        self.curve2_scale_spinbox.blockSignals(True)
        self.curve2_scale_spinbox.setValue(scale_value)
        self.curve2_scale_spinbox.blockSignals(False)

        # Trigger parameter change handler
        self.on_curve2_params_changed()

    def on_curve2_scale_spinbox_changed(self, value):
        """Update scale slider when spinbox changes"""
        # Convert real scale value to slider value (integer)
        slider_value = int(value * 100)

        # Block slider signals to prevent circular update
        self.curve2_scale_slider.blockSignals(True)
        self.curve2_scale_slider.setValue(slider_value)
        self.curve2_scale_slider.blockSignals(False)

        # Trigger parameter change handler
        self.on_curve2_params_changed()

    def on_curve2_position_slider_changed(self, value):
        """Update position spinbox when slider moves"""
        if self.curve2_curve_length > 0:
            position_mm = (value / 100.0) * self.curve2_curve_length
            # Block signals to prevent circular updates
            self.curve2_position_spinbox.blockSignals(True)
            self.curve2_position_spinbox.setValue(position_mm)
            self.curve2_position_spinbox.blockSignals(False)

        self.on_curve2_params_changed()

    def on_curve2_position_spinbox_changed(self, value):
        """Update position slider when spinbox changes"""
        if self.curve2_curve_length > 0:
            slider_value = int((value / self.curve2_curve_length) * 100)
            # Block signals to prevent circular updates
            self.curve2_position_slider.blockSignals(True)
            self.curve2_position_slider.setValue(slider_value)
            self.curve2_position_slider.blockSignals(False)

        self.on_curve2_params_changed()

    def on_curve2_params_changed(self):
        """Called when any curve 2 parameter changes"""
        # Trigger preview update
        self.update_preview()

    # Advanced Options Event Handlers

    def on_symmetric_mode_toggled(self, checked):
        """Handle symmetric mode toggle"""
        if checked:
            # Mirror curve 1 settings to curve 2
            self.mirror_curve1_to_curve2()
            # Lock curve 2 controls (except selection)
            self.set_curve2_controls_locked(True)
        else:
            # Unlock curve 2 controls
            self.set_curve2_controls_locked(False)

    def mirror_curve1_to_curve2(self):
        """Mirror all Curve 1 settings to Curve 2"""
        # Mirror scale (absolute value only, preserve direction)
        self.curve2_scale_slider.setValue(self.curve1_scale_slider.value())
        self.curve2_scale_spinbox.setValue(self.curve1_scale_spinbox.value())
        # DO NOT overwrite curve2_scale_direction - user can flip independently

        # Mirror position as PERCENTAGE, not absolute mm (preserve direction)
        # Slider is already 0-100 percentage, so copy directly
        position_percentage = self.curve1_position_slider.value()
        self.curve2_position_slider.setValue(position_percentage)

        # Calculate curve2's mm value from the percentage
        if self.curve2_curve_length > 0:
            position_mm_curve2 = (
                position_percentage / 100.0
            ) * self.curve2_curve_length
            self.curve2_position_spinbox.blockSignals(True)
            self.curve2_position_spinbox.setValue(position_mm_curve2)
            self.curve2_position_spinbox.blockSignals(False)
        # DO NOT overwrite curve2_position_direction - user can flip independently

        # Mirror continuity
        self.curve2_continuity_combobox.setCurrentIndex(
            self.curve1_continuity_combobox.currentIndex()
        )

    def set_curve2_controls_locked(self, locked):
        """Lock or unlock Curve 2 parameter controls (not selection)"""
        # Disable/enable sliders and spinboxes, but keep flip buttons enabled
        self.curve2_scale_slider.setEnabled(not locked)
        self.curve2_scale_spinbox.setEnabled(not locked)
        # Keep flip buttons always enabled in symmetric mode
        # self.curve2_flip_scale_button.setEnabled(not locked)  # Always enabled
        self.curve2_position_slider.setEnabled(not locked)
        self.curve2_position_spinbox.setEnabled(not locked)
        # Keep flip buttons always enabled in symmetric mode
        # self.curve2_flip_position_button.setEnabled(not locked)  # Always enabled
        self.curve2_continuity_combobox.setEnabled(not locked)

    def on_tension_changed(self, value):
        """Update tension value label and preview"""
        normalized_value = value / 100.0
        self.tension_value_label.setText(f"{normalized_value:.2f}")
        self.update_preview()

    def on_auto_extend_toggled(self, checked):
        """Handle auto-extend toggle"""
        if checked:
            # Show info message about auto-extend feature
            self.update_status(
                translate("BlendCurve", "ℹ️ Auto-extend enabled: Curves will be extended if needed to reach blend points"),
                "info"
            )
        self.update_preview()

    # Trim Controls Event Handlers

    def on_trim_enabled_toggled(self, checked):
        """Handle trim groupbox toggle"""
        if checked:
            # Show info about trim feature
            trim1_mode = self.trim1_combobox.currentText()
            trim2_mode = self.trim2_combobox.currentText()
            self.update_status(
                translate("BlendCurve", f"✂️ Trim enabled: Curve 1 [{trim1_mode}], Curve 2 [{trim2_mode}]"),
                "info"
            )
        else:
            self.update_status(
                translate("BlendCurve", "Trim disabled: Original curves will be preserved"),
                "info"
            )
        self.update_preview()

    def on_trim_params_changed(self):
        """Handle trim parameter changes"""
        self.update_preview()

    # Preview Management

    def update_preview(self):
        """Update the live preview of the blend curve"""
        # Only show preview if both curves are selected
        if not (self.curve1_obj and self.curve2_obj):
            self.clear_preview()
            return

        try:
            # Gather parameters (same as for final curve creation)
            params = self.gather_parameters()

            # Get the edges
            edge1 = self.curve1_obj.Shape.getElement(self.curve1_subname)
            edge2 = self.curve2_obj.Shape.getElement(self.curve2_subname)

            # Convert position (mm) to parameter
            if edge1.Length > 0:
                param1 = edge1.FirstParameter + (
                    params["curve1_position"] / edge1.Length
                ) * (edge1.LastParameter - edge1.FirstParameter)
            else:
                param1 = edge1.FirstParameter

            if edge2.Length > 0:
                param2 = edge2.FirstParameter + (
                    params["curve2_position"] / edge2.Length
                ) * (edge2.LastParameter - edge2.FirstParameter)
            else:
                param2 = edge2.FirstParameter

            # Import PointOnEdge and BlendCurve from blend_curve module
            from freecad.Curves.blend_curve import BlendCurve, PointOnEdge

            # Create PointOnEdge objects
            point1 = PointOnEdge(edge1, param1, params["curve1_continuity"])
            point2 = PointOnEdge(edge2, param2, params["curve2_continuity"])

            # Create blend curve
            blend_curve = BlendCurve(point1, point2)
            # Use signed scales to allow direction flipping
            blend_curve.scale1 = params["curve1_scale"]
            blend_curve.scale2 = params["curve2_scale"]
            blend_curve.perform()

            # Update preview overlay with the generated shape
            self.preview.update_preview(blend_curve.shape)

        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Preview update failed: {str(e)}\n")
            self.clear_preview()

    def clear_preview(self):
        """Clear the preview visualization"""
        if self.preview:
            self.preview.clear_preview()

    # Status Updates

    def update_status(self, message, status_type="info"):
        """
        Update status label with colored message
        status_type: 'info', 'success', 'warning', 'error'
        """
        self.status_label.setText(message)

        # Update styling based on status type
        if status_type == "error":
            style = "color: #cc0000; font-style: italic; padding: 6px; background-color: #ffe6e6; border-radius: 3px;"
        elif status_type == "warning":
            style = "color: #cc6600; font-style: italic; padding: 6px; background-color: #fff3e6; border-radius: 3px;"
        elif status_type == "success":
            style = "color: #009900; font-style: italic; padding: 6px; background-color: #e6ffe6; border-radius: 3px;"
        else:  # info
            style = "color: #0066cc; font-style: italic; padding: 6px; background-color: #f0f0f0; border-radius: 3px;"

        self.status_label.setStyleSheet(style)

    # Apply / Cancel

    def on_apply(self):
        """Apply the blend curve operation"""
        try:
            if self.edit_object:
                self.update_status(
                    translate("BlendCurve", "Updating blend curve..."), "info"
                )
            else:
                self.update_status(
                    translate("BlendCurve", "Creating blend curve..."), "info"
                )

            # Gather all parameters
            params = self.gather_parameters()

            # If editing, update the existing object; otherwise create new
            if self.edit_object:
                # Update properties
                self.edit_object.Curve1Object = params["curve1_obj"]
                self.edit_object.Curve1SubName = params["curve1_subname"]
                self.edit_object.Curve1Scale = params["curve1_scale"]
                self.edit_object.Curve1Position = params["curve1_position"]
                self.edit_object.Curve1Continuity = params["curve1_continuity"]

                self.edit_object.Curve2Object = params["curve2_obj"]
                self.edit_object.Curve2SubName = params["curve2_subname"]
                self.edit_object.Curve2Scale = params["curve2_scale"]
                self.edit_object.Curve2Position = params["curve2_position"]
                self.edit_object.Curve2Continuity = params["curve2_continuity"]

                # Regenerate the blend curve with new parameters
                result_obj = self.logic.execute_blend(params)
                # Update the shape on the existing object
                self.edit_object.Shape = result_obj.Shape

                # Remove the temporary object created by execute_blend
                FreeCAD.ActiveDocument.removeObject(result_obj.Name)
                FreeCAD.ActiveDocument.recompute()
            else:
                # Create new blend curve
                result_obj = self.logic.execute_blend(params)
                # Store the created object reference
                self.created_object = result_obj

            # Clean up and close dialog
            self.cleanup()
            FreeCADGui.Control.closeDialog()

        except Exception as e:
            error_msg = translate("BlendCurve", f"❌ Blend operation failed: {str(e)}")
            self.update_status(error_msg, "error")
            FreeCAD.Console.PrintError(f"Blend operation failed: {str(e)}\n")

    def gather_parameters(self):
        """Gather all parameters from UI controls"""
        # Get scale with direction from state variable
        curve1_scale = self.curve1_scale_spinbox.value() * self.curve1_scale_direction
        curve2_scale = self.curve2_scale_spinbox.value() * self.curve2_scale_direction

        # Position in mm from spinbox, adjusted for direction
        # If direction is -1 (from end), calculate: length - value
        curve1_position_raw = self.curve1_position_spinbox.value()
        if self.curve1_position_direction == -1:
            curve1_position = self.curve1_curve_length - curve1_position_raw
        else:
            curve1_position = curve1_position_raw

        curve2_position_raw = self.curve2_position_spinbox.value()
        if self.curve2_position_direction == -1:
            curve2_position = self.curve2_curve_length - curve2_position_raw
        else:
            curve2_position = curve2_position_raw

        return {
            # Curve 1
            "curve1_obj": self.curve1_obj,
            "curve1_subname": self.curve1_subname,
            "curve1_scale": curve1_scale,
            "curve1_position": curve1_position,
            "curve1_continuity": self.curve1_continuity_combobox.currentIndex(),
            # Curve 2
            "curve2_obj": self.curve2_obj,
            "curve2_subname": self.curve2_subname,
            "curve2_scale": curve2_scale,
            "curve2_position": curve2_position,
            "curve2_continuity": self.curve2_continuity_combobox.currentIndex(),
            # Advanced options
            "tension": self.tension_slider.value() / 100.0,
            "auto_extend": self.auto_extend_checkbox.isChecked(),
            # Trim options
            "trim_enabled": self.trim_groupbox.isChecked(),
            "trim1_mode": self.trim1_combobox.currentIndex(),
            "trim2_mode": self.trim2_combobox.currentIndex(),
        }

    def on_cancel(self):
        """Cancel and close dialog"""
        self.cleanup()
        FreeCADGui.Control.closeDialog()

    # FreeCAD Task Panel Interface

    def accept(self):
        """Called when dialog accepts"""
        try:
            params = self.gather_parameters()
            self.logic.execute_blend(params)
            self.cleanup()
            return True
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error: {str(e)}\n")
            self.cleanup()
            return False

    def reject(self):
        """Called when dialog rejects"""
        self.cleanup()
        return True

    def needsFullSpace(self):
        """Return True to hide the default Ok/Cancel buttons"""
        return True

    def getStandardButtons(self):
        """Return 0 to hide all standard buttons"""
        return 0

    # Cleanup

    def cleanup_selection(self):
        """Clean up selection observers and gates"""
        if self.selection_observer:
            try:
                FreeCADGui.Selection.removeObserver(self.selection_observer)
            except:
                pass
            self.selection_observer = None

        if self.selection_gate:
            try:
                FreeCADGui.Selection.removeSelectionGate()
            except:
                pass
            self.selection_gate = None

    def cleanup(self):
        """Clean up resources"""
        self.cleanup_selection()
        self.clear_highlights()
        if self.preview:
            self.preview.remove_from_scene()

    def __del__(self):
        """Destructor"""
        self.cleanup()
