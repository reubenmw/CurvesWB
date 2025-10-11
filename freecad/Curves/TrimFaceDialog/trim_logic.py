# -*- coding: utf-8 -*-

__title__ = 'Trim face dialog - Core logic'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'Core business logic for trim face operations'

import FreeCAD
import Part
from .. import curveExtend
from .coverage_checker import CoverageChecker


class TrimFaceLogic:
    """Core logic for trim face operations"""

    def __init__(self):
        # Object Properties (State Management)
        # Like React state, but stored on 'self' instead of useState()
        self.trimming_curves = []
        self.face_object = None
        self.direction = None
        self.trim_point = None
        self.use_auto_direction = True
        
        # Extension settings - Phase 1: Detection and User Preference Capture
        # These properties store user choices for how to handle short curves
        self.extension_mode = 'boundary'  # 'none', 'boundary', 'custom'
        self.extension_distance = 10.0    # mm for custom mode
        self.needs_extension = False      # Boolean flag set by detection
        
        # Coverage checker - handles the geometry analysis
        self.coverage_checker = CoverageChecker()

    def add_trimming_curve(self, obj, subname):
        self.trimming_curves.append((obj, subname))

    def remove_trimming_curve(self, index):
        if 0 <= index < len(self.trimming_curves):
            del self.trimming_curves[index]

    def clear_trimming_curves(self):
        self.trimming_curves = []

    def set_face_object(self, face_obj):
        self.face_object = face_obj

    def set_direction(self, direction):
        self.direction = direction

    def set_trim_point(self, point):
        self.trim_point = point

    def set_use_auto_direction(self, use_auto):
        self.use_auto_direction = use_auto

    def set_extension_mode(self, mode):
        """
        Set extension mode: 'none', 'boundary', or 'custom'
        
        This is like a state setter in React - it validates input before updating.
        The tuple check ('none', 'boundary', 'custom') is like array.includes() in JS.
        """
        if mode in ('none', 'boundary', 'custom'):
            self.extension_mode = mode
        else:
            FreeCAD.Console.PrintWarning(f"Invalid extension mode: {mode}\n")

    def set_extension_distance(self, distance):
        """
        Set custom extension distance in mm
        
        Validation and Error Handling Pattern:
        Always validate user input before using it. If invalid, provide a fallback.
        This prevents crashes and gives the user a reasonable default.
        """
        try:
            self.extension_distance = float(distance)
        except (ValueError, TypeError):
            FreeCAD.Console.PrintWarning(f"Invalid extension distance: {distance}\n")
            self.extension_distance = 10.0  # Fallback to safe default

    def check_curve_coverage(self, projection_direction=None):
        """
        Check if trimming curves fully cover the face when projected.
        Returns True if extension is needed, False otherwise.

        This is the key detection method for Phase 1 of the Automatic Curve Extension.
        It determines whether the UI should show extension controls to the user.

        How it works (delegated to CoverageChecker):
        1. Get bounding boxes for face and each edge
        2. Calculate diagonal lengths (3D size measurement)
        3. Compare: if edge < 80% of face diagonal, needs extension
        4. Return True to show extension controls, False to hide them

        Args:
            projection_direction: FreeCAD.Vector or None. If None, uses face normal.
        """
        needs_extension = self.coverage_checker.check_curve_coverage(
            self.trimming_curves,
            self.face_object,
            projection_direction
        )
        self.needs_extension = needs_extension
        return needs_extension


    def _extend_edge_to_boundary(self, edge_shape):
        """
        Extend an edge to cover the face boundaries.
        Uses the ExtendCurve algorithm to extend both ends.

        Args:
            edge_shape: Part.Edge to extend

        Returns:
            Extended Part.Edge or original if extension fails
        """
        try:
            # Get the face shape for boundary calculations
            face_obj = self.face_object[0]
            face_subname = self.face_object[1]
            face_shape = face_obj.Shape.getElement(face_subname)
            face_bbox = face_shape.BoundBox

            # Calculate face diagonal as a safe extension distance
            face_diagonal = (
                (face_bbox.XMax - face_bbox.XMin)**2 +
                (face_bbox.YMax - face_bbox.YMin)**2 +
                (face_bbox.ZMax - face_bbox.ZMin)**2
            ) ** 0.5

            # Extension distance: 50% of face diagonal at each end
            # This ensures we cover the surface with some margin
            extension_distance = face_diagonal * 0.5

            # Get trimmed curve from edge
            curve = curveExtend.getTrimmedCurve(edge_shape)

            # Extend both ends with straight extensions (degree=1)
            # You could use degree=2 for G2 continuity if needed
            ext_start = curveExtend.extendCurve(curve, 0, extension_distance, 1)
            ext_end = curveExtend.extendCurve(curve, 1, extension_distance, 1)

            # Join all segments into a single curve
            curve.join(ext_start.toBSpline())
            curve.join(ext_end.toBSpline())

            extended_edge = curve.toShape()

            FreeCAD.Console.PrintMessage(
                f"Extended edge to {extended_edge.Length:.2f}mm "
                f"(original: {edge_shape.Length:.2f}mm)\n"
            )

            return extended_edge

        except Exception as e:
            FreeCAD.Console.PrintWarning(
                f"Failed to extend edge to boundary: {str(e)}\n"
            )
            import traceback
            traceback.print_exc()
            return edge_shape  # Return original on failure

    def _extend_edge_by_distance(self, edge_shape, distance):
        """
        Extend an edge by a specific distance at both ends.

        Args:
            edge_shape: Part.Edge to extend
            distance: Distance in mm to extend at each end

        Returns:
            Extended Part.Edge or original if extension fails
        """
        try:
            # Get trimmed curve from edge
            curve = curveExtend.getTrimmedCurve(edge_shape)

            # Extend both ends with straight extensions
            ext_start = curveExtend.extendCurve(curve, 0, distance, 1)
            ext_end = curveExtend.extendCurve(curve, 1, distance, 1)

            # Join all segments
            curve.join(ext_start.toBSpline())
            curve.join(ext_end.toBSpline())

            extended_edge = curve.toShape()

            FreeCAD.Console.PrintMessage(
                f"Extended edge by {distance}mm at each end "
                f"(new length: {extended_edge.Length:.2f}mm)\n"
            )

            return extended_edge

        except Exception as e:
            FreeCAD.Console.PrintWarning(
                f"Failed to extend edge by distance: {str(e)}\n"
            )
            import traceback
            traceback.print_exc()
            return edge_shape  # Return original on failure

    def get_extended_curves(self, parent_obj=None):
        """
        Get the trimming curves, extended according to the extension mode.

        Args:
            parent_obj: Optional parent object to nest extended edges under

        Returns:
            List of (object, subname) tuples with extended edges if needed,
            or original curves if no extension is required.
        """
        if self.extension_mode == 'none' or not self.needs_extension:
            # No extension needed
            return self.trimming_curves

        extended_curves = []

        for obj_ref, subname in self.trimming_curves:
            try:
                edge_shape = obj_ref.Shape.getElement(subname)

                if self.extension_mode == 'boundary':
                    extended_edge = self._extend_edge_to_boundary(edge_shape)
                elif self.extension_mode == 'custom':
                    extended_edge = self._extend_edge_by_distance(
                        edge_shape,
                        self.extension_distance
                    )
                else:
                    extended_edge = edge_shape

                # Create an extended edge object to replace the original
                # Name it clearly so user knows it's extended
                temp_name = f"{obj_ref.Name}_Extended"
                temp_obj = FreeCAD.ActiveDocument.addObject("Part::Feature", temp_name)
                temp_obj.Shape = extended_edge

                # Style the extended edge (purple/magenta to distinguish)
                if hasattr(temp_obj, 'ViewObject'):
                    temp_obj.ViewObject.LineColor = (0.8, 0.2, 0.8)  # Purple
                    temp_obj.ViewObject.LineWidth = 2.0
                    # Hide by default - user can expand TrimmedFace to see it
                    temp_obj.ViewObject.Visibility = False

                # Create hierarchical structure:
                # TrimmedFace → Extended → Original
                # This preserves the original for reference

                # First, nest original under extended curve
                if not hasattr(temp_obj, 'Group'):
                    temp_obj.addProperty("App::PropertyLinkList", "Group", "Base", "Original curve reference")

                temp_obj.Group = [obj_ref]

                # Hide the original (it's now nested)
                if hasattr(obj_ref, 'ViewObject'):
                    obj_ref.ViewObject.Visibility = False

                # Then nest extended under parent object if provided
                if parent_obj is not None:
                    # Get or create the Group property on parent
                    if not hasattr(parent_obj, 'Group'):
                        parent_obj.addProperty("App::PropertyLinkList", "Group", "Base", "Extended curves used")

                    # Add to parent's group
                    current_group = list(parent_obj.Group) if hasattr(parent_obj, 'Group') else []
                    current_group.append(temp_obj)
                    parent_obj.Group = current_group

                    FreeCAD.Console.PrintMessage(
                        f"Created hierarchy: {parent_obj.Name} → {temp_name} → {obj_ref.Name}\n"
                    )

                extended_curves.append((temp_obj, 'Edge1'))

            except Exception as e:
                FreeCAD.Console.PrintWarning(
                    f"Failed to extend {obj_ref.Name}.{subname}: {str(e)}\n"
                )
                # Fall back to original curve on error
                extended_curves.append((obj_ref, subname))

        return extended_curves

    def execute_trim(self):
        """Execute the trim operation"""
        if not self.trimming_curves:
            raise ValueError("No trimming curves selected")
        if not self.face_object:
            raise ValueError("No face selected")

        try:
            # Create the TrimmedFace object first
            obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "TrimmedFace")

            from ..TrimFace import trimFace, trimFaceVP
            trimFace(obj)
            trimFaceVP(obj.ViewObject)

            obj.Face = (self.face_object[0], [self.face_object[1]])

            # Get curves (extended if needed based on user settings)
            # Pass the parent object so extended edges can be nested
            curves_to_use = self.get_extended_curves(parent_obj=obj)

            FreeCAD.Console.PrintMessage(
                f"Using {len(curves_to_use)} curve(s) for trimming "
                f"(extension mode: {self.extension_mode})\n"
            )

            # Use the (potentially extended) curves for the trim operation
            tool_list = []
            for obj_ref, subname in curves_to_use:
                tool_list.append((obj_ref, [subname]))
            obj.Tool = tool_list

            face_shape = self.face_object[0].Shape.getElement(self.face_object[1])

            if self.use_auto_direction or self.direction is None:
                # IMPORTANT: Use face center normal for consistency with coverage checking
                # Using trim point normal would give different projection direction than coverage check
                try:
                    face_center = face_shape.CenterOfMass
                    uv = face_shape.Surface.parameter(face_center)
                    normal = face_shape.normalAt(uv[0], uv[1])
                    obj.Direction = FreeCAD.Vector(normal)
                    FreeCAD.Console.PrintMessage(f"Using face center normal for projection: {obj.Direction}\n")
                except:
                    obj.Direction = FreeCAD.Vector(0, 0, 1)
                    FreeCAD.Console.PrintWarning("Using default direction\n")
            else:
                obj.Direction = self.direction
                FreeCAD.Console.PrintMessage(f"Using custom direction for projection: {obj.Direction}\n")

            if self.trim_point:
                try:
                    uv = face_shape.Surface.parameter(self.trim_point)
                    obj.PickedPoint = FreeCAD.Vector(uv[0], uv[1], 0)
                except Exception as e:
                    FreeCAD.Console.PrintWarning(f"Could not set picked point: {str(e)}\n")
                    uv = face_shape.Surface.parameter(face_shape.CenterOfMass)
                    obj.PickedPoint = FreeCAD.Vector(uv[0], uv[1], 0)
            else:
                uv = face_shape.Surface.parameter(face_shape.CenterOfMass)
                obj.PickedPoint = FreeCAD.Vector(uv[0], uv[1], 0)

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
