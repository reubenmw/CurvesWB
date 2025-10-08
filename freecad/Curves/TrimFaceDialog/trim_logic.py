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
        self.trimming_curves = []
        self.face_object = None
        self.direction = None
        self.trim_point = None
        self.use_auto_direction = True
        # Extension settings
        self.extension_mode = 'boundary'  # 'none', 'boundary', 'custom'
        self.extension_distance = 10.0  # mm for custom mode
        self.needs_extension = False
        # Coverage checker
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
        """Set extension mode: 'none', 'boundary', or 'custom'"""
        if mode in ('none', 'boundary', 'custom'):
            self.extension_mode = mode
        else:
            FreeCAD.Console.PrintWarning(f"Invalid extension mode: {mode}\n")

    def set_extension_distance(self, distance):
        """Set custom extension distance in mm"""
        try:
            self.extension_distance = float(distance)
        except (ValueError, TypeError):
            FreeCAD.Console.PrintWarning(f"Invalid extension distance: {distance}\n")
            self.extension_distance = 10.0

    def check_curve_coverage(self, projection_direction=None):
        """
        Check if trimming curves fully cover the face when projected.
        Returns True if extension is needed, False otherwise.

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

    def _project_curve_to_face_uv(self, edge_shape, face_shape, direction):
        """
        Project a curve onto a face along a direction and return the UV bounds on the face.

        Args:
            edge_shape: Part.Edge - the curve to project
            face_shape: Part.Face - the face to project onto
            direction: FreeCAD.Vector - projection direction

        Returns:
            dict: {'min_u': float, 'max_u': float, 'min_v': float, 'max_v': float}
                  or None if projection fails
        """
        try:
            # Sample points along the curve
            sample_points = []

            # Add vertices
            for vertex in edge_shape.Vertexes:
                sample_points.append(vertex.Point)

            # Sample along the curve
            for i in range(50):
                t = edge_shape.FirstParameter + (edge_shape.LastParameter - edge_shape.FirstParameter) * i / 49.0
                sample_points.append(edge_shape.valueAt(t))

            # Use discretize for additional points
            try:
                discretized = edge_shape.discretize(Number=100)
                sample_points.extend(discretized)
            except:
                pass

            # Project each point onto the face and get UV coordinates
            min_u = float('inf')
            max_u = float('-inf')
            min_v = float('inf')
            max_v = float('-inf')

            successful_projections = 0
            failed_projections = 0

            FreeCAD.Console.PrintMessage(f"  Projecting {len(sample_points)} curve points onto face...\n")

            for point in sample_points:
                try:
                    # Project the curve point onto the face along the projection direction
                    # Create a line from the point in both directions along the projection vector
                    # and find intersections with the face

                    # Make a long line segment in the projection direction
                    line_length = 1000.0  # mm, should be long enough
                    p1 = point - direction * line_length
                    p2 = point + direction * line_length

                    # Create a line edge for intersection
                    import Part
                    projection_line = Part.LineSegment(p1, p2).toShape()

                    # Instead of using common() which only finds intersections within face bounds,
                    # project directly onto the underlying surface (which is infinite/extended)

                    # Find the point on the infinite surface along the projection line
                    # Sample along the line and find the closest point on surface
                    min_dist = float('inf')
                    best_uv = None
                    best_intersection = None

                    for i in range(50):
                        test_point = p1 + (p2 - p1) * i / 49.0
                        try:
                            test_u, test_v = face_shape.Surface.parameter(test_point)
                            surf_point = face_shape.Surface.value(test_u, test_v)

                            # Calculate distance from surface point to projection line
                            diff = surf_point - point
                            t = diff.dot(direction)
                            closest_on_line = point + direction * t
                            dist = surf_point.distanceToPoint(closest_on_line)

                            if dist < min_dist:
                                min_dist = dist
                                best_uv = (test_u, test_v)
                                best_intersection = surf_point
                        except:
                            continue

                    # Use the best projection found
                    if best_uv and min_dist < 50.0:  # 50mm tolerance
                        u, v = best_uv
                        min_u = min(min_u, u)
                        max_u = max(max_u, u)
                        min_v = min(min_v, v)
                        max_v = max(max_v, v)
                        successful_projections += 1
                    else:
                        # Projection failed - point too far from surface
                        failed_projections += 1

                except Exception as e:
                    # Point might not project onto face, skip it
                    failed_projections += 1
                    continue

            FreeCAD.Console.PrintMessage(
                f"  Projection results: {successful_projections} successful, {failed_projections} failed\n"
            )

            if successful_projections < 2:
                # Not enough points projected successfully
                FreeCAD.Console.PrintWarning(
                    f"  Only {successful_projections} points projected successfully - too few for coverage check\n"
                )
                return None

            return {'min_u': min_u, 'max_u': max_u, 'min_v': min_v, 'max_v': max_v}

        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Error in _project_curve_to_face_uv: {str(e)}\n")
            return None

    def _get_bounds_in_plane(self, shape, direction):
        """
        Get the 2D bounding box of a shape when projected onto a plane perpendicular to direction.

        Args:
            shape: Part.Shape (Face or Edge)
            direction: FreeCAD.Vector projection direction (normalized)

        Returns:
            dict: {'min_u': float, 'max_u': float, 'min_v': float, 'max_v': float}
                  u and v are orthogonal axes in the projection plane
        """
        # Create two orthogonal vectors perpendicular to direction
        direction = direction.normalize()

        # Find a vector not parallel to direction
        if abs(direction.x) < 0.9:
            temp = FreeCAD.Vector(1, 0, 0)
        else:
            temp = FreeCAD.Vector(0, 1, 0)

        # Create orthonormal basis for the projection plane
        u_axis = direction.cross(temp).normalize()
        v_axis = direction.cross(u_axis).normalize()

        # Get points to project
        points = []
        if hasattr(shape, 'Edges'):  # Face
            for edge in shape.Edges:
                # Add vertices first to ensure we get actual endpoints
                for vertex in edge.Vertexes:
                    points.append(vertex.Point)
                # Sample multiple points along each edge for better accuracy
                for i in range(10):
                    t = edge.FirstParameter + (edge.LastParameter - edge.FirstParameter) * i / 9.0
                    points.append(edge.valueAt(t))
        else:  # Edge
            # Add vertices first to ensure we get actual endpoints
            for vertex in shape.Vertexes:
                points.append(vertex.Point)
            # Sample many points along the edge for accuracy
            for i in range(50):
                t = shape.FirstParameter + (shape.LastParameter - shape.FirstParameter) * i / 49.0
                points.append(shape.valueAt(t))
            # Also use discretize for more accurate representation
            try:
                discretized = shape.discretize(Number=100)
                points.extend(discretized)
            except:
                pass

        if not points:
            return {'min_u': 0, 'max_u': 0, 'min_v': 0, 'max_v': 0}

        # Project all points onto the plane and find bounds
        min_u = float('inf')
        max_u = float('-inf')
        min_v = float('inf')
        max_v = float('-inf')

        for point in points:
            # Project point onto u and v axes
            u_coord = point.dot(u_axis)
            v_coord = point.dot(v_axis)

            min_u = min(min_u, u_coord)
            max_u = max(max_u, u_coord)
            min_v = min(min_v, v_coord)
            max_v = max(max_v, v_coord)

        return {'min_u': min_u, 'max_u': max_u, 'min_v': min_v, 'max_v': max_v}

    def _bounds_contain(self, curve_bounds, face_bounds, tolerance=0.9):
        """
        Check if curve bounds contain (or nearly contain) face bounds.

        Args:
            curve_bounds: dict with min_u, max_u, min_v, max_v for curve
            face_bounds: dict with min_u, max_u, min_v, max_v for face
            tolerance: float, fraction of face extent that curve must cover (0.9 = 90%)

        Returns:
            bool: True if curve adequately covers face
        """
        # Calculate required coverage in each direction
        face_u_extent = face_bounds['max_u'] - face_bounds['min_u']
        face_v_extent = face_bounds['max_v'] - face_bounds['min_v']

        # Calculate margins needed (e.g., if tolerance=0.9, we allow 5% margin on each side)
        u_margin = face_u_extent * (1 - tolerance) / 2.0
        v_margin = face_v_extent * (1 - tolerance) / 2.0

        # Check if curve covers face with tolerance
        u_covered = (curve_bounds['min_u'] <= face_bounds['min_u'] + u_margin and
                     curve_bounds['max_u'] >= face_bounds['max_u'] - u_margin)
        v_covered = (curve_bounds['min_v'] <= face_bounds['min_v'] + v_margin and
                     curve_bounds['max_v'] >= face_bounds['max_v'] - v_margin)

        return u_covered and v_covered

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
                ref_point = self.trim_point if self.trim_point else face_shape.CenterOfMass
                try:
                    uv = face_shape.Surface.parameter(ref_point)
                    normal = face_shape.normalAt(uv[0], uv[1])
                    obj.Direction = FreeCAD.Vector(normal)
                except:
                    obj.Direction = FreeCAD.Vector(0, 0, 1)
                    FreeCAD.Console.PrintWarning("Using default direction\n")
            else:
                obj.Direction = self.direction

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
