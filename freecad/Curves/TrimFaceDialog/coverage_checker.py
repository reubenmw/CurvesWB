# -*- coding: utf-8 -*-

__title__ = 'Trim face dialog - Coverage checker'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'Check if trimming curves adequately cover the face when projected'

import FreeCAD
import FreeCADGui
import Part
from pivy import coin


class CoverageChecker:
    """Check if trimming curves cover a face when projected along a direction"""

    def __init__(self):
        self.debug = True  # Enable detailed debug output
        self.visualize = True  # Enable Coin3D visualization
        self.vis_root = None  # Root node for visualization

    def clear_visualization(self):
        """Clear any existing visualization"""
        if self.vis_root:
            try:
                # Check if we still have a valid view before trying to clean up
                if FreeCADGui.ActiveDocument and FreeCADGui.ActiveDocument.ActiveView:
                    sg = FreeCADGui.ActiveDocument.ActiveView.getSceneGraph()
                    if sg:
                        sg.removeChild(self.vis_root)
            except Exception as e:
                # Silently ignore cleanup errors - visualization is already being destroyed
                pass
            finally:
                # Always clear the reference to prevent access violations
                self.vis_root = None

    def check_curve_coverage(self, trimming_curves, face_object, projection_direction=None):
        """
        Check if trimming curves fully cover the face when projected.

        Args:
            trimming_curves: List of (obj, subname) tuples for edges
            face_object: Tuple of (obj, subname) for the face
            projection_direction: FreeCAD.Vector or None. If None, uses face normal.

        Returns:
            bool: True if extension is needed, False if curves adequately cover
        """
        if not trimming_curves or not face_object:
            return False

        # Clear previous visualization
        self.clear_visualization()

        # Create visualization root if enabled
        if self.visualize:
            try:
                self.vis_root = coin.SoSeparator()
                sg = FreeCADGui.ActiveDocument.ActiveView.getSceneGraph()
                sg.addChild(self.vis_root)
                FreeCAD.Console.PrintMessage("Visualization enabled - Red=curve points, Green=projected points, Blue=projection lines\n")
            except Exception as e:
                FreeCAD.Console.PrintWarning(f"Could not create visualization: {e}\n")
                self.visualize = False

        try:
            face_obj = face_object[0]
            face_subname = face_object[1]
            face_shape = face_obj.Shape.getElement(face_subname)

            # Determine projection direction for coverage check
            if projection_direction is not None:
                proj_direction = projection_direction.normalize()
                FreeCAD.Console.PrintMessage(f"Checking coverage using provided direction: {proj_direction}\n")
            else:
                # Fallback to face normal
                try:
                    face_center = face_shape.CenterOfMass
                    uv = face_shape.Surface.parameter(face_center)
                    proj_direction = face_shape.normalAt(uv[0], uv[1])
                    FreeCAD.Console.PrintMessage(f"Checking coverage using face normal: {proj_direction}\n")
                except:
                    proj_direction = FreeCAD.Vector(0, 0, 1)
                    FreeCAD.Console.PrintWarning("Using default direction for detection\n")

            # Normalize the direction
            proj_direction.normalize()

            # Get the face's parameter space bounds (u,v coordinates on surface)
            u_min, u_max, v_min, v_max = face_shape.ParameterRange

            if self.debug:
                FreeCAD.Console.PrintMessage(f"Face UV range: U=[{u_min:.2f}, {u_max:.2f}], V=[{v_min:.2f}, {v_max:.2f}]\n")

            # Check each curve
            for obj_ref, subname in trimming_curves:
                edge_shape = obj_ref.Shape.getElement(subname)

                # Project the curve onto the face to get its UV bounds
                try:
                    projected_uv_bounds = self._project_curve_to_face_uv(
                        edge_shape, face_shape, proj_direction
                    )

                    if projected_uv_bounds is None:
                        FreeCAD.Console.PrintWarning(
                            f"Could not project curve {obj_ref.Name}.{subname} onto face - skipping coverage check\n"
                        )
                        continue

                    # Check if projected curve is adequate for trimming
                    # A curve is adequate if it enters and exits the face (crosses through it)
                    # Simple rule: Both endpoints outside + curve passes through interior = valid cut

                    # Get UV coordinates
                    start_u = projected_uv_bounds['start_u']
                    start_v = projected_uv_bounds['start_v']
                    end_u = projected_uv_bounds['end_u']
                    end_v = projected_uv_bounds['end_v']

                    # Also get overall bounds
                    curve_min_u = projected_uv_bounds['min_u']
                    curve_max_u = projected_uv_bounds['max_u']
                    curve_min_v = projected_uv_bounds['min_v']
                    curve_max_v = projected_uv_bounds['max_v']

                    # Check if endpoints are outside the face boundaries
                    start_outside = (start_u < u_min or start_u > u_max or
                                    start_v < v_min or start_v > v_max)
                    end_outside = (end_u < u_min or end_u > u_max or
                                  end_v < v_min or end_v > v_max)

                    # Check if curve has points inside the face
                    # (overlaps with face interior in both U and V)
                    has_interior = (curve_min_u < u_max and curve_max_u > u_min and
                                   curve_min_v < v_max and curve_max_v > v_min)

                    # A curve creates a valid cut if:
                    # - Both endpoints are outside the face boundaries, AND
                    # - The curve passes through the interior of the face
                    # This handles: straight cuts, diagonal cuts, U-shaped cuts, same-edge entry/exit
                    is_adequate = start_outside and end_outside and has_interior

                    needs_extension = not is_adequate

                    # Calculate coverage for debug output
                    face_u_range = u_max - u_min
                    face_v_range = v_max - v_min
                    u_coverage = min(curve_max_u, u_max) - max(curve_min_u, u_min)
                    v_coverage = min(curve_max_v, v_max) - max(curve_min_v, v_min)
                    u_coverage_percent = u_coverage / face_u_range if face_u_range > 0 else 0
                    v_coverage_percent = v_coverage / face_v_range if face_v_range > 0 else 0

                    if needs_extension:
                        FreeCAD.Console.PrintMessage(
                            f"Curve {obj_ref.Name}.{subname} does not fully cover face - extension recommended\n"
                            f"  Projection direction: {proj_direction}\n"
                            f"  Face UV range: U=[{u_min:.2f}, {u_max:.2f}], V=[{v_min:.2f}, {v_max:.2f}]\n"
                            f"  Curve START: U={start_u:.4f}, V={start_v:.4f} (outside={start_outside})\n"
                            f"  Curve END: U={end_u:.4f}, V={end_v:.4f} (outside={end_outside})\n"
                            f"  Has interior points: {has_interior}\n"
                            f"  Coverage: U={u_coverage_percent*100:.1f}%, V={v_coverage_percent*100:.1f}%\n"
                        )
                        return True
                    else:
                        FreeCAD.Console.PrintMessage(
                            f"Curve {obj_ref.Name}.{subname} adequately covers face\n"
                            f"  Projection direction: {proj_direction}\n"
                            f"  Face UV range: U=[{u_min:.2f}, {u_max:.2f}], V=[{v_min:.2f}, {v_max:.2f}]\n"
                            f"  Curve START: U={start_u:.4f}, V={start_v:.4f} (outside={start_outside})\n"
                            f"  Curve END: U={end_u:.4f}, V={end_v:.4f} (outside={end_outside})\n"
                            f"  Has interior points: {has_interior}\n"
                            f"  Coverage: U={u_coverage_percent*100:.1f}%, V={v_coverage_percent*100:.1f}%\n"
                        )
                except Exception as e:
                    FreeCAD.Console.PrintWarning(
                        f"Error checking coverage for {obj_ref.Name}.{subname}: {str(e)}\n"
                    )
                    import traceback
                    traceback.print_exc()

            FreeCAD.Console.PrintMessage("All curves adequately cover the face\n")
            return False

        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Error checking curve coverage: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return False

    def _project_curve_to_face_uv(self, edge_shape, face_shape, direction):
        """
        Project a curve onto a face along a direction and return the UV bounds on the face.

        Args:
            edge_shape: Part.Edge - the curve to project
            face_shape: Part.Face - the face to project onto
            direction: FreeCAD.Vector - projection direction

        Returns:
            dict: {'start_u', 'start_v', 'end_u', 'end_v', 'min_u', 'max_u', 'min_v', 'max_v'}
                  or None if projection fails
        """
        try:
            # Get curve endpoints - these are the most important for coverage check
            start_point = edge_shape.valueAt(edge_shape.FirstParameter)
            end_point = edge_shape.valueAt(edge_shape.LastParameter)

            # Sample points along the curve for visualization and fallback checks
            sample_points = [start_point, end_point]

            # Sample along the curve (fewer samples since we prioritize endpoints)
            for i in range(20):
                t = edge_shape.FirstParameter + (edge_shape.LastParameter - edge_shape.FirstParameter) * i / 19.0
                sample_points.append(edge_shape.valueAt(t))

            # Use discretize for additional points
            try:
                discretized = edge_shape.discretize(Number=50)
                sample_points.extend(discretized)
            except:
                pass

            # Project each point onto the face and get UV coordinates
            min_u = float('inf')
            max_u = float('-inf')
            min_v = float('inf')
            max_v = float('-inf')

            start_u = None
            start_v = None
            end_u = None
            end_v = None

            successful_projections = 0
            failed_projections = 0

            if self.debug:
                FreeCAD.Console.PrintMessage(f"  Projecting {len(sample_points)} curve points onto face...\n")

            # Visualization setup
            curve_viz_points = []
            proj_viz_points = []
            line_viz_points = []

            for point in sample_points:
                try:
                    # Project the curve point onto the face along the projection direction
                    # Create a line from the point in both directions along the projection vector
                    # and find intersections with the face

                    # Project point onto the infinite surface along the projection direction
                    # Key: Find true line-surface intersection without UV clamping

                    surf = face_shape.Surface
                    best_uv = None
                    best_intersection = None

                    # Method: Iteratively refine UV coordinates to find where surf.value(u,v)
                    # lies on the projection line: point + t*direction

                    # Start with an initial guess - project point onto surface
                    try:
                        # Get initial UV estimate from the face's parametric range
                        u_min, u_max, v_min, v_max = face_shape.ParameterRange

                        # CRITICAL FIX: Don't use surf.parameter(point) as initial guess
                        # because it clamps UV to face bounds!
                        # Instead, sample along the projection line to find a good starting point

                        line_length = 1000.0
                        p1 = point - direction * line_length
                        p2 = point + direction * line_length

                        # Sample a few points along the line and pick the one closest to surface
                        best_guess_dist = float('inf')
                        u_guess = (u_min + u_max) / 2.0
                        v_guess = (v_min + v_max) / 2.0

                        for i in range(5):  # Just 5 samples for initial guess
                            test_pt = p1 + (p2 - p1) * i / 4.0
                            try:
                                # Get UV (may be clamped, but that's ok for initial guess)
                                test_u, test_v = surf.parameter(test_pt)
                                surf_pt = surf.value(test_u, test_v)

                                # Check distance to projection line
                                diff = surf_pt - point
                                t = diff.dot(direction)
                                closest = point + direction * t
                                dist = surf_pt.distanceToPoint(closest)

                                if dist < best_guess_dist:
                                    best_guess_dist = dist
                                    u_guess = test_u
                                    v_guess = test_v
                            except:
                                continue

                        # Newton-Raphson iteration to find (u,v) where surf.value(u,v)
                        # lies on the line: point + t*direction
                        # Key: Use proper UV step sizes based on surface derivatives
                        # The iteration will escape the clamped initial guess

                        max_iterations = 50  # Increased for better convergence
                        tolerance = 0.01  # 0.01mm

                        for iteration in range(max_iterations):
                            # Evaluate surface at current UV
                            surf_point = surf.value(u_guess, v_guess)

                            # Find closest point on projection line
                            diff = surf_point - point
                            t = diff.dot(direction)
                            closest_on_line = point + direction * t
                            dist = surf_point.distanceToPoint(closest_on_line)

                            # If close enough, we're done
                            if dist < tolerance:
                                best_uv = (u_guess, v_guess)
                                best_intersection = surf_point
                                break

                            # Vector we need to move in 3D space
                            target_vector = closest_on_line - surf_point

                            # Compute surface partial derivatives (tangent vectors)
                            du = abs(u_max - u_min) * 0.01  # 1% of range for finite difference
                            dv = abs(v_max - v_min) * 0.01

                            try:
                                # Get surface tangent vectors at current point
                                surf_u_plus = surf.value(u_guess + du, v_guess)
                                surf_u_minus = surf.value(u_guess - du, v_guess)
                                surf_v_plus = surf.value(u_guess, v_guess + dv)
                                surf_v_minus = surf.value(u_guess, v_guess - dv)

                                # Partial derivatives dS/du and dS/dv (in 3D space)
                                dS_du = (surf_u_plus - surf_u_minus) / (2.0 * du)
                                dS_dv = (surf_v_plus - surf_v_minus) / (2.0 * dv)

                                # Solve for delta_u and delta_v:
                                # target_vector ≈ dS_du * delta_u + dS_dv * delta_v
                                # This is a least-squares problem

                                # Build 3x2 Jacobian matrix: J = [dS_du | dS_dv]
                                # Solve: J^T * J * [delta_u, delta_v]^T = J^T * target_vector

                                # J^T * J (2x2 matrix)
                                a11 = dS_du.dot(dS_du)
                                a12 = dS_du.dot(dS_dv)
                                a22 = dS_dv.dot(dS_dv)

                                # J^T * target_vector (2x1 vector)
                                b1 = dS_du.dot(target_vector)
                                b2 = dS_dv.dot(target_vector)

                                # Solve 2x2 system
                                det = a11 * a22 - a12 * a12
                                if abs(det) > 1e-10:
                                    delta_u = (a22 * b1 - a12 * b2) / det
                                    delta_v = (a11 * b2 - a12 * b1) / det

                                    # Apply with damping
                                    damping = 0.7
                                    u_guess += delta_u * damping
                                    v_guess += delta_v * damping
                                else:
                                    # Singular matrix, can't continue
                                    if dist < 50.0:
                                        best_uv = (u_guess, v_guess)
                                        best_intersection = surf_point
                                    break

                            except Exception as inner_e:
                                # If gradient computation fails, stop
                                if dist < 50.0:
                                    best_uv = (u_guess, v_guess)
                                    best_intersection = surf_point
                                break

                        # If we exited the loop without finding solution, use last iteration if reasonable
                        if best_uv is None and iteration > 0:
                            surf_point = surf.value(u_guess, v_guess)
                            diff = surf_point - point
                            t = diff.dot(direction)
                            closest_on_line = point + direction * t
                            dist = surf_point.distanceToPoint(closest_on_line)

                            if dist < 50.0:
                                best_uv = (u_guess, v_guess)
                                best_intersection = surf_point

                    except Exception as e:
                        # Fallback: use simple sampling if Newton-Raphson fails
                        if self.debug:
                            FreeCAD.Console.PrintWarning(f"Iterative projection failed, using sampling: {e}\n")

                        line_length = 1000.0
                        p1 = point - direction * line_length
                        p2 = point + direction * line_length
                        min_dist = float('inf')

                        for i in range(15):
                            test_point = p1 + (p2 - p1) * i / 14.0
                            try:
                                u, v = surf.parameter(test_point)
                                surf_point = surf.value(u, v)

                                diff = surf_point - point
                                t = diff.dot(direction)
                                closest_on_line = point + direction * t
                                dist = surf_point.distanceToPoint(closest_on_line)

                                if dist < min_dist:
                                    min_dist = dist
                                    best_uv = (u, v)
                                    best_intersection = surf_point
                            except:
                                continue

                    # Use the projection result
                    if best_uv and best_intersection:
                        u, v = best_uv

                        # Capture endpoint UV coordinates (first two points are start and end)
                        if successful_projections == 0:
                            start_u = u
                            start_v = v
                        elif successful_projections == 1:
                            end_u = u
                            end_v = v

                        # Debug: Print first few UV coordinates to see if they extend beyond bounds
                        if self.debug and successful_projections < 5:
                            point_type = "START" if successful_projections == 0 else ("END" if successful_projections == 1 else "sample")
                            FreeCAD.Console.PrintMessage(f"    {point_type} UV: ({u:.4f}, {v:.4f}) from point ({point.x:.2f}, {point.y:.2f}, {point.z:.2f})\n")

                        min_u = min(min_u, u)
                        max_u = max(max_u, u)
                        min_v = min(min_v, v)
                        max_v = max(max_v, v)
                        successful_projections += 1

                        # Add to visualization
                        if self.visualize and best_intersection:
                            curve_viz_points.append((point.x, point.y, point.z))
                            proj_viz_points.append((best_intersection.x, best_intersection.y, best_intersection.z))
                            line_viz_points.append((point.x, point.y, point.z))
                            line_viz_points.append((best_intersection.x, best_intersection.y, best_intersection.z))
                    else:
                        # Projection failed - point too far from surface
                        failed_projections += 1

                except Exception as e:
                    # Point might not project onto face, skip it
                    failed_projections += 1
                    continue

            # Create visualization
            if self.visualize and len(curve_viz_points) > 0:
                # Red curve points
                curve_sep = coin.SoSeparator()
                curve_mat = coin.SoMaterial()
                curve_mat.diffuseColor = (1, 0, 0)  # Red
                curve_sep.addChild(curve_mat)

                curve_style = coin.SoDrawStyle()
                curve_style.pointSize = 10
                curve_sep.addChild(curve_style)

                curve_coords = coin.SoCoordinate3()
                curve_coords.point.setValues(0, len(curve_viz_points), curve_viz_points)
                curve_sep.addChild(curve_coords)
                curve_sep.addChild(coin.SoPointSet())
                self.vis_root.addChild(curve_sep)

                # Green projected points
                proj_sep = coin.SoSeparator()
                proj_mat = coin.SoMaterial()
                proj_mat.diffuseColor = (0, 1, 0)  # Green
                proj_sep.addChild(proj_mat)
                proj_sep.addChild(curve_style)

                proj_coords = coin.SoCoordinate3()
                proj_coords.point.setValues(0, len(proj_viz_points), proj_viz_points)
                proj_sep.addChild(proj_coords)
                proj_sep.addChild(coin.SoPointSet())
                self.vis_root.addChild(proj_sep)

                # Blue projection lines
                line_sep = coin.SoSeparator()
                line_mat = coin.SoMaterial()
                line_mat.diffuseColor = (0, 0, 1)  # Blue
                line_sep.addChild(line_mat)

                line_style = coin.SoDrawStyle()
                line_style.lineWidth = 2
                line_sep.addChild(line_style)

                line_coords = coin.SoCoordinate3()
                line_coords.point.setValues(0, len(line_viz_points), line_viz_points)
                line_sep.addChild(line_coords)

                line_set = coin.SoLineSet()
                line_set.numVertices.setValues(0, len(curve_viz_points), [2] * len(curve_viz_points))
                line_sep.addChild(line_set)
                self.vis_root.addChild(line_sep)

            if self.debug:
                FreeCAD.Console.PrintMessage(
                    f"  Projection results: {successful_projections} successful, {failed_projections} failed\n"
                )

            if successful_projections < 2:
                # Not enough points projected successfully
                FreeCAD.Console.PrintWarning(
                    f"  Only {successful_projections} points projected successfully - too few for coverage check\n"
                )
                return None

            # Check if we got valid endpoint projections
            if start_u is None or end_u is None:
                FreeCAD.Console.PrintWarning("  Failed to project curve endpoints\n")
                return None

            return {
                'start_u': start_u, 'start_v': start_v,
                'end_u': end_u, 'end_v': end_v,
                'min_u': min_u, 'max_u': max_u,
                'min_v': min_v, 'max_v': max_v
            }

        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Error in _project_curve_to_face_uv: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return None
