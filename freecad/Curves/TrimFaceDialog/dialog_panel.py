# -*- coding: utf-8 -*-

__title__ = 'Trim face dialog - Task panel'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'Task panel UI and workflow management for trim face dialog'

import os
import FreeCAD
import FreeCADGui
from PySide import QtGui, QtCore
from PySide.QtCore import Qt

from .trim_logic import TrimFaceLogic
from .selection_handlers import (
    SelectionGate,
    EdgeSelectionObserver,
    FaceSelectionObserver,
    PointSelectionObserver,
    HoverPointCallback
)
from freecad.Curves.Utils.VectorGizmo import VectorGizmo, VectorGizmoUI
from freecad.Curves.Utils.CurveProjectionVisualizer import ProjectionVisualizer
from .preview_overlay import TrimPreviewOverlay

# Translation function
translate = FreeCAD.Qt.translate


class TrimFaceDialogTaskPanel:
    """Fluid NX-style dialog for trim face"""

    def __init__(self):
        self.logic = TrimFaceLogic()

        # Load the UI form from .ui file (Qt Designer interface)
        self.form = FreeCADGui.PySideUic.loadUi(
            os.path.join(os.path.dirname(__file__), "trim_face_dialog.ui"))

        # UI References - Like React refs, but for Qt widgets
        # These give us direct access to UI elements for event handling and updates
        self.status_label = self.form.statusLabel
        self.curve_list = self.form.curveListWidget
        self.clear_curves_button = self.form.clearCurvesButton
        self.remove_curve_button = self.form.removeCurveButton
        
        # Extension controls UI references - Phase 1: Conditional UI elements
        # These are hidden by default and shown when curves are detected as short
        self.extension_group = self.form.extensionGroup
        self.extension_none_radio = self.form.extensionNoneRadio
        self.extension_boundary_radio = self.form.extensionBoundaryRadio
        self.extension_custom_radio = self.form.extensionCustomRadio
        self.extension_distance_edit = self.form.extensionDistanceEdit
        # Other controls
        self.face_label = self.form.faceLabel
        self.point_group = self.form.pointGroup
        self.point_label = self.form.pointLabel
        self.direction_normal_radio = self.form.directionNormalRadio
        self.direction_view_radio = self.form.directionViewRadio
        self.direction_custom_radio = self.form.directionCustomRadio
        self.vector_x_edit = self.form.vectorXEdit
        self.vector_y_edit = self.form.vectorYEdit
        self.vector_z_edit = self.form.vectorZEdit
        self.transparent_preview_check = self.form.transparentPreviewCheck
        self.projection_visualizer_check = self.form.projectionVisualizerCheck
        self.apply_button = self.form.applyButton
        self.cancel_button = self.form.cancelButton

        # Event Handlers (Like onClick in React)
        # Connect UI events to handler methods using Qt's signal/slot system
        self.clear_curves_button.clicked.connect(self.on_clear_curves)
        self.remove_curve_button.clicked.connect(self.on_remove_curve)
        self.form.clearFaceButton.clicked.connect(self.on_clear_face)
        self.form.clearPointButton.clicked.connect(self.on_clear_point)
        self.apply_button.clicked.connect(self.on_apply)
        self.cancel_button.clicked.connect(self.on_cancel)
        
        # Direction radio button connections - event handling pattern
        self.direction_normal_radio.toggled.connect(self.on_direction_changed)
        self.direction_view_radio.toggled.connect(self.on_direction_changed)
        self.direction_custom_radio.toggled.connect(self.on_direction_changed)

        # Vector input field connections - for bidirectional sync with gizmo
        self.vector_x_edit.editingFinished.connect(self._on_vector_field_changed)
        self.vector_y_edit.editingFinished.connect(self._on_vector_field_changed)
        self.vector_z_edit.editingFinished.connect(self._on_vector_field_changed)
        
        # Extension radio button connections - Phase 1 event handling
        # These handle user preference changes for extension mode
        self.extension_none_radio.toggled.connect(self.on_extension_changed)
        self.extension_boundary_radio.toggled.connect(self.on_extension_changed)
        self.extension_custom_radio.toggled.connect(self.on_extension_changed)

        # Transparent preview connection
        self.transparent_preview_check.toggled.connect(self.on_transparent_preview_changed)

        # Projection visualizer connection
        self.projection_visualizer_check.toggled.connect(self.on_projection_visualizer_changed)

        self.workflow_stage = 'edges'
        self.selection_gate = None
        self.selection_observer = None

        # Vector direction gizmo components
        self.vector_gizmo = None
        self.vector_ui = None

        # Projection visualizer component
        self.projection_visualizer = None

        # Transparent preview component
        self.transparent_preview = None

        # Hover callback for real-time preview during point selection
        self.hover_callback = None

        # Disable Apply button and Point group initially
        self.apply_button.setEnabled(False)
        self.point_group.setEnabled(False)

        self.populate_initial_selection()
        self.start_workflow()

    def populate_initial_selection(self):
        """Pre-populate with any selected edges"""
        selection = FreeCADGui.Selection.getSelectionEx()
        if not selection:
            return

        for sel_obj in selection:
            if sel_obj.HasSubObjects:
                for subname in sel_obj.SubElementNames:
                    if 'Edge' in subname:
                        self.logic.add_trimming_curve(sel_obj.Object, subname)
                        display_name = f"{sel_obj.Object.Name}.{subname}"
                        self.curve_list.addItem(display_name)

    def start_workflow(self):
        """Start the fluid workflow"""
        if self.curve_list.count() > 0:
            self.workflow_stage = 'face'
            self.start_face_selection()
        else:
            self.workflow_stage = 'edges'
            self.start_edge_selection()

    def start_edge_selection(self):
        """Start edge selection mode"""
        self.workflow_stage = 'edges'
        self.update_status(translate('TrimFaceDialog', 'Select trimming edges (Ctrl/Shift for multiple)'))

        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.removeSelectionGate()
        self.selection_gate = SelectionGate('edge')
        FreeCADGui.Selection.addSelectionGate(self.selection_gate)

        self.selection_observer = EdgeSelectionObserver(self)
        FreeCADGui.Selection.addObserver(self.selection_observer)

    def on_edge_selected(self, obj, subname):
        """Handle edge selection"""
        self.logic.add_trimming_curve(obj, subname)
        display_name = f"{obj.Name}.{subname}"
        self.curve_list.addItem(display_name)
        self.update_status(translate('TrimFaceDialog', '{0} edge(s) selected').format(self.curve_list.count()))

        modifiers = QtGui.QApplication.keyboardModifiers()
        multi_select = bool(modifiers & (Qt.ControlModifier | Qt.ShiftModifier))

        if not multi_select and self.curve_list.count() > 0:
            QtCore.QTimer.singleShot(100, self.advance_to_face)

    def advance_to_face(self):
        """Advance to face selection"""
        self.stop_edge_selection()
        self.start_face_selection()

    def stop_edge_selection(self):
        """Stop edge selection mode"""
        if self.selection_observer:
            FreeCADGui.Selection.removeObserver(self.selection_observer)
            self.selection_observer = None
        if self.selection_gate:
            FreeCADGui.Selection.removeSelectionGate()
            self.selection_gate = None

    def start_face_selection(self):
        """Start face selection mode"""
        self.workflow_stage = 'face'
        self.update_status(translate('TrimFaceDialog', 'Click on the face to trim'))
        self.update_apply_button()

        FreeCADGui.Selection.clearSelection()
        self.selection_gate = SelectionGate('face')
        FreeCADGui.Selection.addSelectionGate(self.selection_gate)

        self.selection_observer = FaceSelectionObserver(self)
        FreeCADGui.Selection.addObserver(self.selection_observer)

    def on_face_selected(self, obj, subname):
        """
        Handle face selection - Integration Point for Extension Detection
        
        This is where Phase 1 extension detection is triggered in the workflow.
        After face selection, we check if curves need extension and show controls.
        """
        self.logic.set_face_object((obj, subname))
        face_name = f"{obj.Name}.{subname}"
        self.face_label.setText(face_name)
        self.face_label.setStyleSheet("padding: 4px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 3px; color: #155724;")

        # Enable point selection group now that face is selected
        self.point_group.setEnabled(True)

        # Integration Point: Trigger extension detection after face selection
        # This calls the logic layer to check if curves are too short
        self.check_and_show_extension_controls()

        QtCore.QTimer.singleShot(100, self.advance_to_point)

    def advance_to_point(self):
        """Advance to point selection"""
        self.stop_face_selection()
        self.start_point_selection()

    def stop_face_selection(self):
        """Stop face selection mode"""
        if self.selection_observer:
            FreeCADGui.Selection.removeObserver(self.selection_observer)
            self.selection_observer = None
        if self.selection_gate:
            FreeCADGui.Selection.removeSelectionGate()
            self.selection_gate = None

    def start_point_selection(self):
        """Start point selection mode"""
        self.workflow_stage = 'point'
        self.update_status(translate('TrimFaceDialog', 'Hover over the face to preview - Click to select area to DELETE'))
        self.update_apply_button()

        FreeCADGui.Selection.clearSelection()

        self.selection_observer = PointSelectionObserver(self)
        FreeCADGui.Selection.addObserver(self.selection_observer)

        # Install hover callback for real-time preview
        if self.transparent_preview_check.isChecked():
            self.hover_callback = HoverPointCallback(self)
            self.hover_callback.install()

    def check_picked_point(self):
        """Check if a picked point is available"""
        selection = FreeCADGui.Selection.getSelectionEx()

        if selection and len(selection) > 0:
            sel = selection[0]
            if hasattr(sel, 'PickedPoints') and len(sel.PickedPoints) > 0:
                picked_3d = sel.PickedPoints[0]

                if self.logic.face_object:
                    try:
                        face_obj = self.logic.face_object[0]
                        face_subname = self.logic.face_object[1]
                        face_shape = face_obj.Shape.getElement(face_subname)

                        u, v = face_shape.Surface.parameter(picked_3d)
                        self.logic.set_trim_point(picked_3d)

                        self.point_label.setText(translate('TrimFaceDialog', 'Point: ({0:.2f}, {1:.2f}, {2:.2f})').format(picked_3d.x, picked_3d.y, picked_3d.z))
                        self.point_label.setStyleSheet("padding: 4px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 3px; color: #155724;")

                        QtCore.QTimer.singleShot(100, self.complete_workflow)
                    except Exception as e:
                        self.point_label.setText(translate('TrimFaceDialog', 'Error: {0}').format(str(e)))
                        self.point_label.setStyleSheet("padding: 4px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 3px; color: #721c24;")

    def complete_workflow(self):
        """Complete the workflow"""
        self.stop_point_selection()
        self.workflow_stage = 'complete'
        self.update_status(translate('TrimFaceDialog', 'Ready to apply trim operation'))
        self.status_label.setStyleSheet("color: #155724; font-weight: bold; padding: 4px; background-color: #d4edda; border-radius: 3px;")
        self.update_apply_button()

    def stop_point_selection(self):
        """Stop point selection mode"""
        if self.selection_observer:
            FreeCADGui.Selection.removeObserver(self.selection_observer)
            self.selection_observer = None

        # Remove hover callback if active
        if self.hover_callback:
            self.hover_callback.remove()
            self.hover_callback = None

    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)

    def update_apply_button(self):
        """Update apply button state"""
        can_apply = (self.curve_list.count() > 0 and
                     self.logic.face_object is not None and
                     self.logic.trim_point is not None)
        self.apply_button.setEnabled(can_apply)

    def on_direction_changed(self):
        """Handle direction radio button changes"""
        is_custom = self.direction_custom_radio.isChecked()
        self.vector_x_edit.setEnabled(is_custom)
        self.vector_y_edit.setEnabled(is_custom)
        self.vector_z_edit.setEnabled(is_custom)

        # Show/hide vector gizmo based on Custom Vector selection
        if is_custom:
            self._show_vector_gizmo()
        else:
            self._hide_vector_gizmo()

        # Re-check extension needs when direction changes
        if self.logic.face_object is not None:
            self.check_and_show_extension_controls()

        # Update projection visualization if it's active (and only if user explicitly enabled it)
        if self.projection_visualizer_check.isChecked():
            self._hide_projection_visualizer()
            self._show_projection_visualizer()
        # Note: Do NOT automatically activate projection visualizer
        # It should only appear when user explicitly checks the checkbox
        
        # Update transparent preview if it's active
        if self.transparent_preview_check.isChecked():
            self._hide_transparent_preview()
            self._show_transparent_preview()

    def on_extension_changed(self):
        """
        Handle extension radio button changes - Event Handler Pattern
        
        This is like a state management handler in React. When user changes
        extension mode, we update the logic layer and enable/disable related UI.
        
        Event-driven architecture: User action → Handler → State update → UI update
        """
        if self.extension_none_radio.isChecked():
            self.logic.set_extension_mode('none')
            self.extension_distance_edit.setEnabled(False)
        elif self.extension_boundary_radio.isChecked():
            self.logic.set_extension_mode('boundary')
            self.extension_distance_edit.setEnabled(False)
        elif self.extension_custom_radio.isChecked():
            self.logic.set_extension_mode('custom')
            self.extension_distance_edit.setEnabled(True)  # Enable input for custom distance

    def on_transparent_preview_changed(self):
        """
        Handle transparent preview checkbox changes.

        Shows or hides the real-time transparent preview of trim areas
        based on the current selection and projection direction.
        """
        is_checked = self.transparent_preview_check.isChecked()

        if is_checked:
            # Show transparent preview
            self._show_transparent_preview()

            # If we're in point selection mode, install hover callback
            if self.workflow_stage == 'point':
                if self.hover_callback is None:
                    self.hover_callback = HoverPointCallback(self)
                    self.hover_callback.install()
        else:
            # Hide transparent preview
            self._hide_transparent_preview()

            # Remove hover callback if active
            if self.hover_callback:
                self.hover_callback.remove()
                self.hover_callback = None

    def on_projection_visualizer_changed(self):
        """
        Handle projection visualizer checkbox changes.
        
        Shows or hides the curve projection visualization in the 3D viewport
        based on the current selection and projection direction.
        """
        is_checked = self.projection_visualizer_check.isChecked()
        
        if is_checked:
            # Show visualization
            self._show_projection_visualizer()
        else:
            # Hide visualization
            self._hide_projection_visualizer()

    def _show_projection_visualizer(self):
        """Show the projection visualization for current curves and face"""
        try:
            # Check if we have the required objects
            if not self.logic.trimming_curves or not self.logic.face_object:
                FreeCAD.Console.PrintWarning(translate('TrimFaceDialog', 'Cannot show projection visualization: missing curves or face\n'))
                self.projection_visualizer_check.setChecked(False)
                return

            # Create projection visualizer if it doesn't exist
            if self.projection_visualizer is None:
                self.projection_visualizer = ProjectionVisualizer()

            # Get projection direction
            projection_dir = self._get_current_projection_direction()

            # Get first curve and face for visualization
            curve_obj, curve_subname = self.logic.trimming_curves[0]
            face_obj, face_subname = self.logic.face_object

            # Visualize the projection
            self.projection_visualizer.visualize_projection(
                curve_obj, curve_subname, face_obj, face_subname, projection_dir
            )

            FreeCAD.Console.PrintMessage("Projection visualization enabled\n")

        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to show projection visualization: {str(e)}\n")
            self.projection_visualizer_check.setChecked(False)

    def _show_transparent_preview(self):
        """Show the transparent preview for current trim setup"""
        try:
            # Check if we have the required objects
            if not self.logic.trimming_curves or not self.logic.face_object or not self.logic.trim_point:
                FreeCAD.Console.PrintWarning(translate('TrimFaceDialog', 'Cannot show transparent preview: missing curves, face, or trim point\n'))
                self.transparent_preview_check.setChecked(False)
                return

            # Create transparent preview overlay if it doesn't exist
            if self.transparent_preview is None:
                self.transparent_preview = TrimPreviewOverlay()

            # Get projection direction
            projection_dir = self._get_current_projection_direction()

            # Show the preview (with trim_point to determine delete region)
            self.transparent_preview.show_preview(
                self.logic.face_object,
                self.logic.trimming_curves,
                projection_dir,
                self.logic.trim_point  # Pass trim_point for intelligent region selection
            )

            FreeCAD.Console.PrintMessage("Transparent preview enabled\n")

        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to show transparent preview: {str(e)}\n")
            self.transparent_preview_check.setChecked(False)

    def _hide_transparent_preview(self):
        """Hide the transparent preview"""
        if self.transparent_preview is not None:
            try:
                self.transparent_preview.hide_preview()
                FreeCAD.Console.PrintMessage("Transparent preview disabled\n")
            except Exception as e:
                FreeCAD.Console.PrintError(f"Failed to hide transparent preview: {str(e)}\n")

    def update_hover_preview(self, hover_point):
        """
        Update the transparent preview based on hover point.

        Called during point selection when user hovers over the face.
        Shows which region will be deleted in real-time.

        Args:
            hover_point: FreeCAD.Vector of the hover position
        """
        try:
            # Only update if we have the required objects
            if not self.logic.trimming_curves or not self.logic.face_object:
                return

            # Create transparent preview overlay if it doesn't exist
            if self.transparent_preview is None:
                self.transparent_preview = TrimPreviewOverlay()

            # Get projection direction
            projection_dir = self._get_current_projection_direction()

            # Show the preview with the hover point
            self.transparent_preview.show_preview(
                self.logic.face_object,
                self.logic.trimming_curves,
                projection_dir,
                hover_point  # Use hover point to determine delete region
            )

        except Exception as e:
            # Silently ignore errors during hover to avoid console spam
            pass

    def _hide_projection_visualizer(self):
        """Hide the projection visualization"""
        if self.projection_visualizer is not None:
            try:
                self.projection_visualizer.clear_visualization()
                FreeCAD.Console.PrintMessage("Projection visualization disabled\n")
            except Exception as e:
                FreeCAD.Console.PrintError(f"Failed to hide projection visualization: {str(e)}\n")

    def _get_current_projection_direction(self):
        """
        Get the current projection direction based on radio button selection.
        
        Returns:
            FreeCAD.Vector or None: Current projection direction
        """
        if self.direction_normal_radio.isChecked():
            # Use face normal (pass None to let visualizer determine it)
            return None
        elif self.direction_view_radio.isChecked():
            # Use current view direction
            try:
                return FreeCADGui.ActiveDocument.ActiveView.getViewDirection()
            except:
                return None
        elif self.direction_custom_radio.isChecked():
            # Use custom vector if valid
            try:
                x_text = self.vector_x_edit.text().strip()
                y_text = self.vector_y_edit.text().strip()
                z_text = self.vector_z_edit.text().strip()

                x = float(x_text) if x_text else 0.0
                y = float(y_text) if y_text else 0.0
                z = float(z_text) if z_text else 0.0

                custom_vector = FreeCAD.Vector(x, y, z)
                if custom_vector.Length < 1e-6:
                    return None
                return custom_vector
            except:
                return None
        else:
            return None

    def check_and_show_extension_controls(self):
        """
        Check if curves need extension and show/hide extension controls accordingly.
        Uses the currently selected projection direction for accurate detection.
        
        Conditional Rendering Pattern (Qt version):
        In React: {needsExtension && <ExtensionGroup />}
        In Qt: self.extension_group.setVisible(needs_extension)
        
        This method demonstrates the complete Phase 1 workflow:
        1. Get current projection direction from UI
        2. Call logic layer for detection
        3. Show/hide UI based on result
        """
        # Determine the direction to use for checking based on radio button selection
        if self.direction_normal_radio.isChecked():
            # Use face normal - pass None to let logic determine it
            projection_dir = None
        elif self.direction_view_radio.isChecked():
            # Use current view direction
            try:
                projection_dir = FreeCADGui.ActiveDocument.ActiveView.getViewDirection()
            except:
                projection_dir = None
        elif self.direction_custom_radio.isChecked():
            # Use custom vector if valid
            try:
                x = float(self.vector_x_edit.text())
                y = float(self.vector_y_edit.text())
                z = float(self.vector_z_edit.text())
                projection_dir = FreeCAD.Vector(x, y, z)
                if projection_dir.Length < 1e-6:
                    projection_dir = None
            except:
                projection_dir = None
        else:
            projection_dir = None

        # Check coverage using the determined direction
        needs_extension = self.logic.check_curve_coverage(projection_direction=projection_dir)

        if needs_extension:
            # Show the extension group - conditional rendering
            self.extension_group.setVisible(True)
            FreeCAD.Console.PrintMessage("Extension controls shown - curve may be shorter than surface\n")
        else:
            # Hide the extension group - clean interface when not needed
            self.extension_group.setVisible(False)
            FreeCAD.Console.PrintMessage("Curves appear to cover surface adequately\n")

    def on_clear_curves(self):
        """Clear all curves"""
        self.curve_list.clear()
        self.logic.clear_trimming_curves()

        if self.workflow_stage != 'edges':
            self.cleanup_selection()
            self.start_edge_selection()

    def on_remove_curve(self):
        """Remove selected curve"""
        current_row = self.curve_list.currentRow()
        if current_row >= 0:
            self.logic.remove_trimming_curve(current_row)
            self.curve_list.takeItem(current_row)

    def on_clear_face(self):
        """Clear the selected face"""
        self.logic.set_face_object(None)
        self.face_label.setText(translate('TrimFaceDialog', 'No face selected'))
        self.face_label.setStyleSheet("padding: 4px; background-color: #fafafa; border: 1px solid #ddd; border-radius: 3px;")
        self.extension_group.setVisible(False)

        # Also clear and disable point when face is cleared
        self.logic.set_trim_point(None)
        self.point_label.setText(translate('TrimFaceDialog', 'No point selected'))
        self.point_label.setStyleSheet("padding: 4px; background-color: #fafafa; border: 1px solid #ddd; border-radius: 3px;")
        self.point_group.setEnabled(False)

        self.update_apply_button()

        # Restart face selection if we're past that stage
        if self.workflow_stage in ['point', 'complete']:
            self.cleanup_selection()
            self.start_face_selection()

    def on_clear_point(self):
        """Clear the selected point"""
        self.logic.set_trim_point(None)
        self.point_label.setText(translate('TrimFaceDialog', 'No point selected'))
        self.point_label.setStyleSheet("padding: 4px; background-color: #fafafa; border: 1px solid #ddd; border-radius: 3px;")
        self.update_apply_button()

        # Restart point selection if we're at completion stage
        if self.workflow_stage == 'complete':
            self.cleanup_selection()
            self.start_point_selection()

    def on_apply(self):
        """Apply the trim operation"""
        try:
            # Capture extension settings if custom mode is selected
            if self.extension_custom_radio.isChecked() and self.extension_group.isVisible():
                distance_text = self.extension_distance_edit.text()
                if distance_text:
                    self.logic.set_extension_distance(distance_text)

            # Determine direction based on radio button selection
            if self.direction_normal_radio.isChecked():
                self.logic.set_use_auto_direction(True)
            elif self.direction_view_radio.isChecked():
                self.logic.set_use_auto_direction(False)
                view_dir = FreeCADGui.ActiveDocument.ActiveView.getViewDirection()
                self.logic.set_direction(view_dir)
            elif self.direction_custom_radio.isChecked():
                self.logic.set_use_auto_direction(False)
                try:
                    x_text = self.vector_x_edit.text().strip()
                    y_text = self.vector_y_edit.text().strip()
                    z_text = self.vector_z_edit.text().strip()

                    x = float(x_text) if x_text else 0.0
                    y = float(y_text) if y_text else 0.0
                    z = float(z_text) if z_text else 0.0

                    custom_vector = FreeCAD.Vector(x, y, z)

                    # Smart default: If 0,0,0 entered, use face normal
                    if custom_vector.Length < 1e-6:
                        if self.logic.face_object is not None:
                            face_obj = self.logic.face_object[0]
                            face_subname = self.logic.face_object[1]
                            face_shape = face_obj.Shape.getElement(face_subname)
                            u_mid = (face_shape.ParameterRange[0] + face_shape.ParameterRange[1]) / 2.0
                            v_mid = (face_shape.ParameterRange[2] + face_shape.ParameterRange[3]) / 2.0
                            custom_vector = face_shape.normalAt(u_mid, v_mid)
                            FreeCAD.Console.PrintMessage("Using face normal for zero vector in apply\n")
                        else:
                            raise ValueError("Vector cannot be zero length and no face selected")

                    self.logic.set_direction(custom_vector)
                except ValueError as e:
                    self.status_label.setText(translate('TrimFaceDialog', 'Error: Invalid custom vector'))
                    self.status_label.setStyleSheet("color: #721c24; font-weight: bold; padding: 4px; background-color: #f8d7da; border-radius: 3px;")
                    FreeCAD.Console.PrintError(f"Invalid vector: {str(e)}\n")
                    return

            self.logic.execute_trim()

            # Clean up all visualizations BEFORE closing dialog
            self._cleanup_vector_gizmo()
            self._hide_transparent_preview()
            self._hide_projection_visualizer()
            if self.hover_callback:
                self.hover_callback.remove()
                self.hover_callback = None

            FreeCADGui.Control.closeDialog()
        except Exception as e:
            self.status_label.setText(translate('TrimFaceDialog', 'Error: {0}').format(str(e)))
            self.status_label.setStyleSheet("color: #721c24; font-weight: bold; padding: 4px; background-color: #f8d7da; border-radius: 3px;")
            FreeCAD.Console.PrintError(f"Trim operation failed: {str(e)}\n")

    def on_cancel(self):
        """Cancel and close dialog"""
        # Clean up all visualizations BEFORE closing dialog
        self._cleanup_vector_gizmo()
        self._hide_transparent_preview()
        self._hide_projection_visualizer()
        if self.hover_callback:
            self.hover_callback.remove()
            self.hover_callback = None
        FreeCADGui.Control.closeDialog()

    def accept(self):
        """Called when dialog accepts"""
        try:
            # This is the same logic as on_apply but for task panel accept
            if self.direction_normal_radio.isChecked():
                self.logic.set_use_auto_direction(True)
            elif self.direction_view_radio.isChecked():
                self.logic.set_use_auto_direction(False)
                view_dir = FreeCADGui.ActiveDocument.ActiveView.getViewDirection()
                self.logic.set_direction(view_dir)
            elif self.direction_custom_radio.isChecked():
                self.logic.set_use_auto_direction(False)
                try:
                    x = float(self.vector_x_edit.text())
                    y = float(self.vector_y_edit.text())
                    z = float(self.vector_z_edit.text())
                    custom_vector = FreeCAD.Vector(x, y, z)
                    if custom_vector.Length < 1e-6:
                        raise ValueError("Vector cannot be zero length")
                    self.logic.set_direction(custom_vector)
                except ValueError as e:
                    FreeCAD.Console.PrintError(f"Invalid vector: {str(e)}\n")
                    self.cleanup()  # Clean up before returning
                    return False

            self.logic.execute_trim()

            # Clean up gizmo BEFORE cleanup
            self._cleanup_vector_gizmo()
            self.cleanup()  # Clean up after successful execution
            return True
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error: {str(e)}\n")
            self._cleanup_vector_gizmo()
            self.cleanup()  # Clean up on error
            return False

    def reject(self):
        """Called when dialog rejects"""
        self._cleanup_vector_gizmo()
        self.cleanup()
        return True

    def needsFullSpace(self):
        """
        Return True to hide the default Ok/Cancel buttons at the top.
        We have our own Apply/Cancel buttons, so we don't need the defaults.
        """
        return True

    def getStandardButtons(self):
        """
        Return 0 to hide all standard buttons.
        Combined with needsFullSpace(), this ensures no default buttons appear.
        """
        return 0

    def _show_vector_gizmo(self):
        """
        Show the 3D vector direction gizmo in the viewport.

        Uses the new VectorGizmoUI helper for standardized integration.
        """
        try:
            # Determine gizmo position and size based on face
            arrow_length = 50.0  # Default
            arrow_size = 10.0    # Default
            position = FreeCAD.Vector(0, 0, 0)  # Default

            if self.logic.face_object is not None:
                # Position at face centroid
                face_obj = self.logic.face_object[0]
                face_subname = self.logic.face_object[1]
                face_shape = face_obj.Shape.getElement(face_subname)
                position = face_shape.CenterOfMass

                # Scale arrow based on face size
                bbox = face_shape.BoundBox
                face_diagonal = ((bbox.XLength**2 + bbox.YLength**2 + bbox.ZLength**2)**0.5)
                arrow_length = face_diagonal * 0.3  # 30% of face diagonal
                arrow_size = arrow_length * 0.15     # 15% of arrow length

                FreeCAD.Console.PrintMessage(
                    f"Face diagonal: {face_diagonal:.2f}mm, Arrow length: {arrow_length:.2f}mm\n"
                )
            elif self.logic.trim_point is not None:
                # Position at trim point
                position = self.logic.trim_point

            # Create gizmo if it doesn't exist
            if self.vector_gizmo is None:
                self.vector_gizmo = VectorGizmo(
                    position=position,
                    direction=FreeCAD.Vector(1, 0, 0),  # Default direction
                    arrow_length=arrow_length,
                    arrow_size=arrow_size,
                    color=(0.0, 1.0, 1.0)  # Cyan
                )
                
                # Create UI integration helper
                self.vector_ui = VectorGizmoUI(
                    gizmo=self.vector_gizmo,
                    dialog=self,
                    x_field=self.vector_x_edit,
                    y_field=self.vector_y_edit,
                    z_field=self.vector_z_edit,
                    smart_default_enabled=True,
                    smart_default_callback=self._get_face_normal_for_vector
                )
                
                FreeCAD.Console.PrintMessage("Vector gizmo and UI helper created\n")
            else:
                # Update existing gizmo position and scaling
                self.vector_ui.set_gizmo_position(position)
                self.vector_ui.set_gizmo_scaling(arrow_length, arrow_size)
                self.vector_ui.show_gizmo()
                FreeCAD.Console.PrintMessage("Vector gizmo updated and shown\n")

        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to show vector gizmo: {str(e)}\n")
            import traceback
            traceback.print_exc()

    def _hide_vector_gizmo(self):
        """
        Hide the 3D vector direction gizmo.

        This is called when user switches away from Custom Vector mode.
        The gizmo is hidden but not destroyed, so it can be shown again quickly.
        """
        if self.vector_ui is not None:
            self.vector_ui.hide_gizmo()
            FreeCAD.Console.PrintMessage("Vector gizmo hidden\n")

    def _cleanup_vector_gizmo(self):
        """
        Completely remove and destroy the vector gizmo and UI helper.

        This is called when the dialog is closing (accept/cancel/reject).
        Ensures both the gizmo and UI helper are properly cleaned up.
        """
        if self.vector_ui is not None:
            try:
                self.vector_ui.cleanup()
                self.vector_ui = None
                FreeCAD.Console.PrintMessage("Vector gizmo UI helper cleaned up\n")
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error cleaning up vector UI helper: {str(e)}\n")
        
        if self.vector_gizmo is not None:
            try:
                self.vector_gizmo.cleanup()
                self.vector_gizmo = None
                FreeCAD.Console.PrintMessage("Vector gizmo cleaned up\n")
            except Exception as e:
                FreeCAD.Console.PrintError(f"Error cleaning up vector gizmo: {str(e)}\n")

    def _get_face_normal_for_vector(self):
        """
        Smart default callback for vector gizmo.
        
        Returns the face normal if a face is selected, otherwise Z-axis.
        
        Returns:
            FreeCAD.Vector: Face normal or Z-axis default
        """
        try:
            if self.logic.face_object is not None:
                face_obj = self.logic.face_object[0]
                face_subname = self.logic.face_object[1]
                face_shape = face_obj.Shape.getElement(face_subname)
                u_mid = (face_shape.ParameterRange[0] + face_shape.ParameterRange[1]) / 2.0
                v_mid = (face_shape.ParameterRange[2] + face_shape.ParameterRange[3]) / 2.0
                return face_shape.normalAt(u_mid, v_mid)
            else:
                return FreeCAD.Vector(0, 0, 1)  # Z-axis default
        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Could not get face normal: {str(e)}\n")
            return FreeCAD.Vector(0, 0, 1)

    def _on_vector_field_changed(self):
        """
        Callback when X/Y/Z input fields change.
        
        Updates the projection visualization if it's active when custom vector values change.
        """
        # Update projection visualization if it's active and we're in Custom Vector mode
        if self.direction_custom_radio.isChecked() and self.projection_visualizer_check.isChecked():
            self._hide_projection_visualizer()
            self._show_projection_visualizer()

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

        # Clean up vector gizmo (redundant safety check)
        self._cleanup_vector_gizmo()

        # Clean up projection visualizer
        self._hide_projection_visualizer()

        # Clean up transparent preview completely
        self._hide_transparent_preview()
        if self.transparent_preview is not None:
            try:
                self.transparent_preview.cleanup()
                self.transparent_preview = None
            except Exception as e:
                FreeCAD.Console.PrintWarning(f"Error cleaning up transparent preview: {str(e)}\n")

        # Clean up hover callback
        if self.hover_callback:
            self.hover_callback.remove()
            self.hover_callback = None

        # Clean up visualization from coverage checker
        if hasattr(self, 'logic') and self.logic and hasattr(self.logic, 'coverage_checker'):
            try:
                self.logic.coverage_checker.clear_visualization()
            except:
                pass

    def __del__(self):
        """Destructor"""
        self.cleanup()
