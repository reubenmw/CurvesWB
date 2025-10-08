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
    PointSelectionObserver
)


class TrimFaceDialogTaskPanel:
    """Fluid NX-style dialog for trim face"""

    def __init__(self):
        self.logic = TrimFaceLogic()

        self.form = FreeCADGui.PySideUic.loadUi(
            os.path.join(os.path.dirname(__file__), "TrimFaceDialog.ui"))

        self.status_label = self.form.statusLabel
        self.curve_list = self.form.curveListWidget
        self.clear_curves_button = self.form.clearCurvesButton
        self.remove_curve_button = self.form.removeCurveButton
        # Extension controls
        self.extension_group = self.form.extensionGroup
        self.extension_none_radio = self.form.extensionNoneRadio
        self.extension_boundary_radio = self.form.extensionBoundaryRadio
        self.extension_custom_radio = self.form.extensionCustomRadio
        self.extension_distance_edit = self.form.extensionDistanceEdit
        # Other controls
        self.face_label = self.form.faceLabel
        self.point_label = self.form.pointLabel
        self.direction_normal_radio = self.form.directionNormalRadio
        self.direction_view_radio = self.form.directionViewRadio
        self.direction_custom_radio = self.form.directionCustomRadio
        self.vector_x_edit = self.form.vectorXEdit
        self.vector_y_edit = self.form.vectorYEdit
        self.vector_z_edit = self.form.vectorZEdit
        self.apply_button = self.form.applyButton
        self.cancel_button = self.form.cancelButton

        self.clear_curves_button.clicked.connect(self.on_clear_curves)
        self.remove_curve_button.clicked.connect(self.on_remove_curve)
        self.apply_button.clicked.connect(self.on_apply)
        self.cancel_button.clicked.connect(self.on_cancel)
        self.direction_custom_radio.toggled.connect(self.on_direction_changed)
        # Extension radio button connections
        self.extension_none_radio.toggled.connect(self.on_extension_changed)
        self.extension_boundary_radio.toggled.connect(self.on_extension_changed)
        self.extension_custom_radio.toggled.connect(self.on_extension_changed)

        self.workflow_stage = 'edges'
        self.selection_gate = None
        self.selection_observer = None

        # Disable Apply button initially
        self.apply_button.setEnabled(False)

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
        self.update_status("Select trimming edges (Ctrl/Shift for multiple)")

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
        self.update_status(f"{self.curve_list.count()} edge(s) selected")

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
        self.update_status("Click on the face to trim")
        self.update_apply_button()

        FreeCADGui.Selection.clearSelection()
        self.selection_gate = SelectionGate('face')
        FreeCADGui.Selection.addSelectionGate(self.selection_gate)

        self.selection_observer = FaceSelectionObserver(self)
        FreeCADGui.Selection.addObserver(self.selection_observer)

    def on_face_selected(self, obj, subname):
        """Handle face selection"""
        self.logic.set_face_object((obj, subname))
        face_name = f"{obj.Name}.{subname}"
        self.face_label.setText(face_name)
        self.face_label.setStyleSheet("padding: 4px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 3px; color: #155724;")

        # Check if curve extension is needed
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
        self.update_status("Click on the face to select the area to keep")
        self.update_apply_button()

        FreeCADGui.Selection.clearSelection()

        self.selection_observer = PointSelectionObserver(self)
        FreeCADGui.Selection.addObserver(self.selection_observer)

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

                        self.point_label.setText(f"Point: ({picked_3d.x:.2f}, {picked_3d.y:.2f}, {picked_3d.z:.2f})")
                        self.point_label.setStyleSheet("padding: 4px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 3px; color: #155724;")

                        QtCore.QTimer.singleShot(100, self.complete_workflow)
                    except Exception as e:
                        self.point_label.setText(f"Error: {str(e)}")
                        self.point_label.setStyleSheet("padding: 4px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 3px; color: #721c24;")

    def complete_workflow(self):
        """Complete the workflow"""
        self.stop_point_selection()
        self.workflow_stage = 'complete'
        self.update_status("Ready to apply trim operation")
        self.status_label.setStyleSheet("color: #155724; font-weight: bold; padding: 4px; background-color: #d4edda; border-radius: 3px;")
        self.update_apply_button()

    def stop_point_selection(self):
        """Stop point selection mode"""
        if self.selection_observer:
            FreeCADGui.Selection.removeObserver(self.selection_observer)
            self.selection_observer = None

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

    def on_extension_changed(self):
        """Handle extension radio button changes"""
        if self.extension_none_radio.isChecked():
            self.logic.set_extension_mode('none')
            self.extension_distance_edit.setEnabled(False)
        elif self.extension_boundary_radio.isChecked():
            self.logic.set_extension_mode('boundary')
            self.extension_distance_edit.setEnabled(False)
        elif self.extension_custom_radio.isChecked():
            self.logic.set_extension_mode('custom')
            self.extension_distance_edit.setEnabled(True)

    def check_and_show_extension_controls(self):
        """
        Check if curves need extension and show/hide extension controls accordingly.
        This is called after face selection.
        """
        needs_extension = self.logic.check_curve_coverage()

        if needs_extension:
            # Show the extension group
            self.extension_group.setVisible(True)
            FreeCAD.Console.PrintMessage("Extension controls shown - curve may be shorter than surface\n")
        else:
            # Hide the extension group
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
                    x = float(self.vector_x_edit.text())
                    y = float(self.vector_y_edit.text())
                    z = float(self.vector_z_edit.text())
                    custom_vector = FreeCAD.Vector(x, y, z)
                    if custom_vector.Length < 1e-6:
                        raise ValueError("Vector cannot be zero length")
                    self.logic.set_direction(custom_vector)
                except ValueError as e:
                    self.status_label.setText("Error: Invalid custom vector")
                    self.status_label.setStyleSheet("color: #721c24; font-weight: bold; padding: 4px; background-color: #f8d7da; border-radius: 3px;")
                    FreeCAD.Console.PrintError(f"Invalid vector: {str(e)}\n")
                    return

            self.logic.execute_trim()
            FreeCADGui.Control.closeDialog()
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: #721c24; font-weight: bold; padding: 4px; background-color: #f8d7da; border-radius: 3px;")
            FreeCAD.Console.PrintError(f"Trim operation failed: {str(e)}\n")

    def on_cancel(self):
        """Cancel and close dialog"""
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
                    return False

            self.logic.execute_trim()
            return True
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error: {str(e)}\n")
            return False

    def reject(self):
        """Called when dialog rejects"""
        self.cleanup()
        return True

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

    def __del__(self):
        """Destructor"""
        self.cleanup()
