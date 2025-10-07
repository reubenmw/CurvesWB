# -*- coding: utf-8 -*-

__title__ = 'Trim face with dialog'
__author__ = 'Christophe Grellier (Chris_G)'
__license__ = 'LGPL 2.1'
__doc__ = 'Trim a face with a projected curve using a dialog stepper'

import os
import FreeCAD
import FreeCADGui
import Part
from PySide import QtGui
from PySide.QtCore import Qt

try:
    import BOPTools.SplitAPI
    splitAPI = BOPTools.SplitAPI
except ImportError:
    FreeCAD.Console.PrintError("Failed importing BOPTools. Fallback to Part API\n")
    splitAPI = Part.BOPTools.SplitAPI

from freecad.Curves import ICONPATH

TOOL_ICON = os.path.join(ICONPATH, 'trimFace.svg')
DEBUG = False


def debug(string):
    if DEBUG:
        FreeCAD.Console.PrintMessage(string)
        FreeCAD.Console.PrintMessage("\n")


class SelectionGate:
    """Selection gate to control what user can select in 3D view"""
    def __init__(self, mode):
        self.mode = mode  # 'edge' or 'face'

    def allow(self, doc_name, obj_name, subname):
        if self.mode == 'edge':
            return 'Edge' in subname
        elif self.mode == 'face':
            return 'Face' in subname
        return False


class TrimFaceLogic:
    """Core logic for trim face operations - separated from UI"""

    def __init__(self):
        self.trimming_curves = []  # List of (Object, SubElementName) tuples
        self.face_object = None
        self.direction = None
        self.trim_point = None
        self.use_auto_direction = True

    def add_trimming_curve(self, obj, subname):
        """Add a single trimming curve"""
        self.trimming_curves.append((obj, subname))

    def remove_trimming_curve(self, index):
        """Remove trimming curve by index"""
        if 0 <= index < len(self.trimming_curves):
            del self.trimming_curves[index]

    def clear_trimming_curves(self):
        """Clear all trimming curves"""
        self.trimming_curves = []

    def set_face_object(self, face_obj):
        """Set the face to be trimmed"""
        self.face_object = face_obj

    def set_direction(self, direction):
        """Set the projection direction"""
        self.direction = direction

    def set_trim_point(self, point):
        """Set the point to determine which part to keep"""
        self.trim_point = point

    def set_use_auto_direction(self, use_auto):
        """Set whether to use automatic direction calculation"""
        self.use_auto_direction = use_auto

    def execute_trim(self):
        """Execute the actual trim operation using collected data"""
        if not self.trimming_curves:
            raise ValueError("No trimming curves selected")
        if not self.face_object:
            raise ValueError("No face selected")

        try:
            # Create the trimmed face using the original trimFace logic
            obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "TrimmedFace")

            # Import the original trimFace functionality
            from .TrimFace import trimFace, trimFaceVP
            trimFace(obj)
            trimFaceVP(obj.ViewObject)

            # Set the face property
            obj.Face = (self.face_object[0], [self.face_object[1]])

            # Set the tool curves
            tool_list = []
            for obj_ref, subname in self.trimming_curves:
                tool_list.append((obj_ref, [subname]))
            obj.Tool = tool_list

            # Get the face shape for calculations
            face_shape = self.face_object[0].Shape.getElement(self.face_object[1])

            # Set the direction - calculate from face normal if auto is selected
            if self.use_auto_direction or self.direction is None:
                # Calculate the UV parameters for the trim point if available
                ref_point = self.trim_point if self.trim_point else face_shape.CenterOfMass
                try:
                    uv = face_shape.Surface.parameter(ref_point)
                    normal = face_shape.normalAt(uv[0], uv[1])
                    obj.Direction = FreeCAD.Vector(normal)
                except:
                    # Fallback to simple normal calculation
                    obj.Direction = FreeCAD.Vector(0, 0, 1)
                    FreeCAD.Console.PrintWarning("Using default direction\n")
            else:
                obj.Direction = self.direction

            # Set the picked point for which side to keep
            if self.trim_point:
                try:
                    uv = face_shape.Surface.parameter(self.trim_point)
                    obj.PickedPoint = FreeCAD.Vector(uv[0], uv[1], 0)
                except Exception as e:
                    FreeCAD.Console.PrintWarning(f"Could not set picked point: {str(e)}\n")
                    # Use center of face as fallback
                    uv = face_shape.Surface.parameter(face_shape.CenterOfMass)
                    obj.PickedPoint = FreeCAD.Vector(uv[0], uv[1], 0)
            else:
                # Use center of face
                uv = face_shape.Surface.parameter(face_shape.CenterOfMass)
                obj.PickedPoint = FreeCAD.Vector(uv[0], uv[1], 0)

            # Hide the original surface after trim (like the original tool does)
            if hasattr(self.face_object[0], 'ViewObject'):
                self.face_object[0].ViewObject.Visibility = False

            FreeCAD.ActiveDocument.recompute()
            FreeCAD.Console.PrintMessage("Trim operation completed successfully\n")
            return obj

        except ImportError as e:
            FreeCAD.Console.PrintError(f"Failed to import TrimFace: {str(e)}\n")
            raise
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error executing trim: {str(e)}\n")
            import traceback
            traceback.print_exc()
            raise


class TrimFaceDialogTaskPanel:
    """UI class for the trim face dialog - separated from core logic"""

    def __init__(self):
        # Initialize core logic
        self.logic = TrimFaceLogic()

        # Load UI from .ui file
        self.form = FreeCADGui.PySideUic.loadUi(
            os.path.join(os.path.dirname(__file__), "TrimFaceDialog.ui"))

        # UI elements (loaded from UI file)
        self.step_label = self.form.stepLabel
        self.step_description = self.form.stepDescription
        self.info_label = self.form.infoLabel
        self.instructions_label = self.form.instructionsLabel
        self.prev_button = self.form.prevButton
        self.next_button = self.form.nextButton
        self.finish_button = self.form.finishButton
        self.cancel_button = self.form.cancelButton

        # Step-specific widgets
        self.curve_list = self.form.curveListWidget
        self.add_curve_button = self.form.addCurveButton
        self.remove_curve_button = self.form.removeCurveButton
        self.select_button = self.form.selectButton
        self.auto_direction_checkbox = self.form.autoDirectionCheckbox
        self.direction_combo = self.form.directionCombo
        self.direction_frame = self.form.directionFrame
        self.pick_point_button = self.form.pickPointButton
        self.point_label = self.form.pointLabel
        self.preview_frame = self.form.previewFrame

        # Connect signals
        self.add_curve_button.clicked.connect(self.on_add_curve_clicked)
        self.remove_curve_button.clicked.connect(self.on_remove_curve_clicked)
        self.select_button.clicked.connect(self.on_select_face_clicked)
        self.prev_button.clicked.connect(self.prev_step)
        self.next_button.clicked.connect(self.next_step)
        self.finish_button.clicked.connect(self.on_finish)
        self.cancel_button.clicked.connect(self.on_cancel)
        self.auto_direction_checkbox.stateChanged.connect(self.on_direction_mode_changed)
        self.pick_point_button.clicked.connect(self.on_pick_point_clicked)

        # Current step
        self.current_step = 0

        # Selection gate and observer
        self.selection_gate = None
        self.selection_observer = None
        self.adding_curves_mode = False

        # Pre-populate with selected edges if any exist
        self.populate_initial_selection()

        # Setup initial state
        self.update_step(0)

    def populate_initial_selection(self):
        """Pre-populate curve list with any edges selected when tool is activated"""
        selection = FreeCADGui.Selection.getSelectionEx()

        if not selection:
            return

        for sel_obj in selection:
            if sel_obj.HasSubObjects:
                for subname in sel_obj.SubElementNames:
                    if 'Edge' in subname:
                        # Add to logic
                        self.logic.add_trimming_curve(sel_obj.Object, subname)
                        # Add to list widget
                        display_name = f"{sel_obj.Object.Name}.{subname}"
                        self.curve_list.addItem(display_name)

    def update_step(self, step_num):
        """Update UI for the current step"""
        self.current_step = step_num

        # Hide all step-specific widgets first
        self.curve_list.setVisible(False)
        self.add_curve_button.setVisible(False)
        self.remove_curve_button.setVisible(False)
        self.select_button.setVisible(False)
        self.direction_frame.setVisible(False)
        self.preview_frame.setVisible(False)

        if step_num == 0:  # Select curves
            self.step_label.setText("Step 1 of 4: Select Trimming Curve(s)")
            self.step_description.setText("Select one or more edges to be used as trimming tools")

            # Show curve list and add/remove buttons
            self.curve_list.setVisible(True)
            self.add_curve_button.setVisible(True)
            self.remove_curve_button.setVisible(True)

            # Update info based on curve list
            if self.curve_list.count() > 0:
                self.info_label.setText(f"{self.curve_list.count()} curve(s) selected")
                self.info_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.info_label.setText("No curves selected yet")
                self.info_label.setStyleSheet("color: blue; font-style: italic;")

            self.instructions_label.setText("Select edges in the 3D view and click 'Add Curve'")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(self.curve_list.count() > 0)
            self.finish_button.setEnabled(False)

        elif step_num == 1:  # Select face
            self.step_label.setText("Step 2 of 4: Select Face to Trim")
            self.step_description.setText("Select the face that will be trimmed")

            # Show select button for face
            self.select_button.setVisible(True)
            self.select_button.setText("Select Face")

            if self.logic.face_object:
                face_name = f"{self.logic.face_object[0].Name}.{self.logic.face_object[1]}"
                self.info_label.setText(f"Selected: {face_name}")
                self.info_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.info_label.setText("No face selected yet")
                self.info_label.setStyleSheet("color: blue; font-style: italic;")

            self.instructions_label.setText("Click 'Select Face', then select a face in the 3D view")
            self.prev_button.setEnabled(True)
            self.next_button.setEnabled(self.logic.face_object is not None)
            self.finish_button.setEnabled(False)

        elif step_num == 2:  # Set direction
            self.step_label.setText("Step 3 of 4: Projection Direction")
            self.step_description.setText("Set the projection direction for trimming (default: face normal)")
            self.info_label.setText("Direction will be calculated from the face")
            self.info_label.setStyleSheet("color: green; font-weight: bold;")
            self.instructions_label.setText("Choose how the trimming curve will be projected onto the face")

            # Show direction frame
            self.direction_frame.setVisible(True)

            self.prev_button.setEnabled(True)
            self.next_button.setEnabled(True)
            self.finish_button.setEnabled(False)

        elif step_num == 3:  # Select point to keep
            self.step_label.setText("Step 4 of 4: Select Point to Keep")
            self.step_description.setText("Pick a point on the face to specify which part to keep")

            # Show preview frame with pick point button
            self.preview_frame.setVisible(True)

            if self.logic.trim_point:
                pt = self.logic.trim_point
                self.point_label.setText(f"Point: ({pt.x:.2f}, {pt.y:.2f}, {pt.z:.2f})")
                self.point_label.setStyleSheet("color: green; font-weight: bold;")
                self.info_label.setText("Point selected - ready to finish")
                self.info_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.point_label.setText("No point selected")
                self.point_label.setStyleSheet("color: blue; font-style: italic;")
                self.info_label.setText("Click 'Pick Point on Face' button")
                self.info_label.setStyleSheet("color: blue; font-style: italic;")

            self.instructions_label.setText("Click the button below, then click on the face to select which area to keep after trimming")
            self.prev_button.setEnabled(True)
            self.next_button.setVisible(False)
            self.finish_button.setEnabled(self.logic.trim_point is not None)

    def on_add_curve_clicked(self):
        """Toggle add curve mode - automatically add edges when selected"""
        if self.adding_curves_mode:
            # Stop adding mode
            self.stop_adding_curves()
        else:
            # Start adding mode
            self.start_adding_curves()

    def start_adding_curves(self):
        """Start the curve adding mode with selection observer"""
        self.adding_curves_mode = True
        self.add_curve_button.setText("Done Adding")
        self.info_label.setText("Click on edges in the 3D view to add them")
        self.info_label.setStyleSheet("color: blue; font-style: italic;")

        # Set up selection gate for edges only
        FreeCADGui.Selection.removeSelectionGate()
        self.selection_gate = SelectionGate('edge')
        FreeCADGui.Selection.addSelectionGate(self.selection_gate)

        # Add selection observer to auto-add edges
        class CurveSelectionObserver:
            def __init__(self, parent):
                self.parent = parent

            def addSelection(self, doc_name, obj_name, sub_name, pos):
                if 'Edge' in sub_name:
                    obj = FreeCAD.ActiveDocument.getObject(obj_name)
                    # Add to logic
                    self.parent.logic.add_trimming_curve(obj, sub_name)
                    # Add to list widget
                    display_name = f"{obj_name}.{sub_name}"
                    self.parent.curve_list.addItem(display_name)
                    self.parent.next_button.setEnabled(True)
                    self.parent.info_label.setText(f"{self.parent.curve_list.count()} curve(s) selected")
                    self.parent.info_label.setStyleSheet("color: green; font-weight: bold;")

        self.selection_observer = CurveSelectionObserver(self)
        FreeCADGui.Selection.addObserver(self.selection_observer)

    def stop_adding_curves(self):
        """Stop the curve adding mode"""
        self.adding_curves_mode = False
        self.add_curve_button.setText("Add Curve")

        # Remove selection gate and observer
        if self.selection_gate:
            FreeCADGui.Selection.removeSelectionGate()
            self.selection_gate = None

        if self.selection_observer:
            FreeCADGui.Selection.removeObserver(self.selection_observer)
            self.selection_observer = None

        if self.curve_list.count() > 0:
            self.info_label.setText(f"{self.curve_list.count()} curve(s) selected")
            self.info_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.info_label.setText("No curves selected yet")
            self.info_label.setStyleSheet("color: blue; font-style: italic;")

    def on_remove_curve_clicked(self):
        """Remove selected item from curve list"""
        current_row = self.curve_list.currentRow()

        if current_row >= 0:
            # Remove from logic
            self.logic.remove_trimming_curve(current_row)
            # Remove from list widget
            self.curve_list.takeItem(current_row)

            if self.curve_list.count() > 0:
                self.info_label.setText(f"Curve removed - {self.curve_list.count()} remaining")
                self.info_label.setStyleSheet("color: green; font-weight: bold;")
                self.next_button.setEnabled(True)
            else:
                self.info_label.setText("All curves removed")
                self.info_label.setStyleSheet("color: blue; font-style: italic;")
                self.next_button.setEnabled(False)
        else:
            self.info_label.setText("Select a curve from the list to remove")
            self.info_label.setStyleSheet("color: orange; font-weight: bold;")

    def on_select_face_clicked(self):
        """Toggle face selection mode with instant confirmation"""
        if hasattr(self, 'selecting_face') and self.selecting_face:
            # Stop selection mode
            self.stop_face_selection()
        else:
            # Start selection mode
            self.start_face_selection()

    def start_face_selection(self):
        """Start face selection mode with auto-confirm"""
        self.selecting_face = True
        self.select_button.setText("Cancel Selection")
        self.info_label.setText("Click on a face in the 3D view")
        self.info_label.setStyleSheet("color: blue; font-style: italic;")

        # Set up selection gate for faces
        FreeCADGui.Selection.removeSelectionGate()
        self.selection_gate = SelectionGate('face')
        FreeCADGui.Selection.addSelectionGate(self.selection_gate)

        # Add selection observer to auto-confirm face
        class FaceSelectionObserver:
            def __init__(self, parent):
                self.parent = parent

            def addSelection(self, doc_name, obj_name, sub_name, pos):
                if 'Face' in sub_name:
                    obj = FreeCAD.ActiveDocument.getObject(obj_name)
                    # Store as (Object, SubElementName) tuple
                    self.parent.logic.set_face_object((obj, sub_name))

                    face_name = f"{obj_name}.{sub_name}"
                    self.parent.info_label.setText(f"Selected: {face_name}")
                    self.parent.info_label.setStyleSheet("color: green; font-weight: bold;")
                    self.parent.next_button.setEnabled(True)

                    # Auto-stop selection mode after getting face
                    self.parent.stop_face_selection()

        self.selection_observer = FaceSelectionObserver(self)
        FreeCADGui.Selection.addObserver(self.selection_observer)

    def stop_face_selection(self):
        """Stop face selection mode"""
        self.selecting_face = False
        self.select_button.setText("Select Face")

        # Remove selection gate and observer
        if self.selection_gate:
            FreeCADGui.Selection.removeSelectionGate()
            self.selection_gate = None

        if self.selection_observer:
            FreeCADGui.Selection.removeObserver(self.selection_observer)
            self.selection_observer = None

    def on_direction_mode_changed(self, state):
        """Handle auto direction checkbox state change"""
        is_auto = bool(state)
        self.logic.set_use_auto_direction(is_auto)
        self.direction_combo.setEnabled(not is_auto)

    def on_pick_point_clicked(self):
        """Toggle point picking mode with observer"""
        if hasattr(self, 'picking_point') and self.picking_point:
            # Stop picking mode
            self.stop_point_picking()
        else:
            # Start picking mode
            self.start_point_picking()

    def start_point_picking(self):
        """Start point picking mode with selection observer for auto-confirm"""
        self.picking_point = True
        self.pick_point_button.setText("Cancel Picking")
        self.point_label.setText("Click on the face in the 3D view to pick a point")
        self.point_label.setStyleSheet("color: blue; font-style: italic;")

        # Clear previous selection
        FreeCADGui.Selection.clearSelection()

        # Add selection observer to auto-detect picked points
        class PointSelectionObserver:
            def __init__(self, parent):
                self.parent = parent

            def addSelection(self, doc_name, obj_name, sub_name, pos):
                # Use a timer to give FreeCAD time to populate PickedPoints
                from PySide import QtCore
                QtCore.QTimer.singleShot(100, lambda: self.parent.check_picked_point())

        self.selection_observer = PointSelectionObserver(self)
        FreeCADGui.Selection.addObserver(self.selection_observer)

    def check_picked_point(self):
        """Check if a picked point is available and process it"""
        if not hasattr(self, 'picking_point') or not self.picking_point:
            return

        selection = FreeCADGui.Selection.getSelectionEx()

        if selection and len(selection) > 0:
            sel = selection[0]
            # Check if there are picked points
            if hasattr(sel, 'PickedPoints') and len(sel.PickedPoints) > 0:
                picked_3d = sel.PickedPoints[0]

                # Convert to parametric space if we have a face
                if self.logic.face_object:
                    try:
                        # Get the face shape
                        face_obj = self.logic.face_object[0]
                        face_subname = self.logic.face_object[1]
                        face_shape = face_obj.Shape.getElement(face_subname)

                        # Convert the 3D point to UV parametric coordinates
                        u, v = face_shape.Surface.parameter(picked_3d)

                        # Store the point
                        self.logic.set_trim_point(picked_3d)

                        self.point_label.setText(f"Point: ({picked_3d.x:.2f}, {picked_3d.y:.2f}, {picked_3d.z:.2f})")
                        self.point_label.setStyleSheet("color: green; font-weight: bold;")
                        self.finish_button.setEnabled(True)
                        self.info_label.setText("Point selected - ready to finish")
                        self.info_label.setStyleSheet("color: green; font-weight: bold;")

                        # Auto-stop picking after success
                        self.stop_point_picking()
                    except Exception as e:
                        self.point_label.setText(f"Error: {str(e)}")
                        self.point_label.setStyleSheet("color: red; font-style: italic;")

    def stop_point_picking(self):
        """Stop point picking mode"""
        self.picking_point = False
        self.pick_point_button.setText("Pick Point on Face")

        # Remove selection observer
        if self.selection_observer:
            FreeCADGui.Selection.removeObserver(self.selection_observer)
            self.selection_observer = None

    def next_step(self):
        """Move to next step"""
        if self.current_step < 3:
            self.update_step(self.current_step + 1)

    def prev_step(self):
        """Move to previous step"""
        if self.current_step > 0:
            self.update_step(self.current_step - 1)

    def on_finish(self):
        """Execute the trim operation and close dialog"""
        try:
            self.logic.set_use_auto_direction(self.auto_direction_checkbox.isChecked())
            self.logic.execute_trim()
            FreeCADGui.Control.closeDialog()
        except Exception as e:
            self.info_label.setText(f"Error: {str(e)}")
            self.info_label.setStyleSheet("color: red; font-weight: bold;")
            FreeCAD.Console.PrintError(f"Trim operation failed: {str(e)}\n")

    def on_cancel(self):
        """Close the dialog without performing the operation"""
        FreeCADGui.Control.closeDialog()

    def accept(self):
        """Called when user clicks Finish button"""
        try:
            self.logic.set_use_auto_direction(self.auto_direction_checkbox.isChecked())
            self.logic.execute_trim()
            return True
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error in trim operation: {str(e)}\n")
            return False

    def reject(self):
        """Called when user clicks Cancel button"""
        self.cleanup()
        return True

    def cleanup(self):
        """Clean up resources when closing dialog"""
        try:
            FreeCADGui.Selection.removeSelectionGate()
            self.selection_gate = None
        except:
            pass

    def __del__(self):
        """Destructor - ensure cleanup"""
        self.cleanup()


class TrimFaceDialogCommand:
    def Activated(self):
        # Show version banner
        FreeCAD.Console.PrintMessage("=" * 60 + "\n")
        FreeCAD.Console.PrintMessage("🔧 TRIM FACE DIALOG - UPDATED VERSION v2.0\n")
        FreeCAD.Console.PrintMessage("✅ Loading from: Curves Fork addon\n")
        FreeCAD.Console.PrintMessage("📅 October 2025 - Fixed by Claude\n")
        FreeCAD.Console.PrintMessage("=" * 60 + "\n")

        panel = TrimFaceDialogTaskPanel()
        FreeCADGui.Control.showDialog(panel)

    def GetResources(self):
        return {
            'Pixmap': TOOL_ICON,
            'MenuText': '🔧 Trim Face Dialog [UPDATED v2.0]',
            'ToolTip': '✅ NEW FIXED VERSION - Trim a face with a 4-step wizard dialog (October 2025)'
        }


# Register the command
FreeCADGui.addCommand('TrimDialog', TrimFaceDialogCommand())
