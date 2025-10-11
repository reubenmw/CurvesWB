# -*- coding: utf-8 -*-

__title__ = 'Projection Visualizer - Debug Tool'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'Standalone tool to visualize how curves project onto surfaces'

import FreeCAD
import FreeCADGui
import Part
from pivy import coin


class ProjectionVisualizer:
    """
    Debug tool to visualize curve projection onto a surface.

    Shows:
    - Red points: Original curve sample points
    - Green points: Projected points on the surface
    - Blue lines: Projection rays
    - Yellow: Surface UV bounds visualization
    """

    def __init__(self):
        self.vis_root = None

    def clear_visualization(self):
        """Clear any existing visualization"""
        if self.vis_root:
            try:
                sg = FreeCADGui.ActiveDocument.ActiveView.getSceneGraph()
                sg.removeChild(self.vis_root)
            except:
                pass
            self.vis_root = None

    def visualize_projection(self, curve_obj, curve_subname, face_obj, face_subname, direction=None):
        """
        Visualize how a curve projects onto a face.

        Args:
            curve_obj: FreeCAD object containing the curve
            curve_subname: Subname of the edge (e.g., "Edge1")
            face_obj: FreeCAD object containing the face
            face_subname: Subname of the face (e.g., "Face1")
            direction: FreeCAD.Vector - projection direction (if None, uses face normal)
        """
        self.clear_visualization()

        try:
            # Get the shapes
            edge_shape = curve_obj.Shape.getElement(curve_subname)
            face_shape = face_obj.Shape.getElement(face_subname)

            # Determine projection direction
            if direction is None:
                try:
                    face_center = face_shape.CenterOfMass
                    uv = face_shape.Surface.parameter(face_center)
                    direction = face_shape.normalAt(uv[0], uv[1])
                    FreeCAD.Console.PrintMessage(f"Using face normal as projection direction: {direction}\n")
                except:
                    direction = FreeCAD.Vector(0, 0, 1)
                    FreeCAD.Console.PrintWarning("Using default direction (0, 0, 1)\n")

            direction.normalize()

            # Sample points along the curve
            sample_points = []

            # Add vertices
            for vertex in edge_shape.Vertexes:
                sample_points.append(vertex.Point)

            # Sample along the curve
            for i in range(50):
                t = edge_shape.FirstParameter + (edge_shape.LastParameter - edge_shape.FirstParameter) * i / 49.0
                sample_points.append(edge_shape.valueAt(t))

            FreeCAD.Console.PrintMessage(f"Projecting {len(sample_points)} curve points onto surface...\n")

            # Project each point and collect visualization data
            curve_viz_points = []
            proj_viz_points = []
            line_viz_points = []

            surf = face_shape.Surface
            line_length = 1000.0

            min_u = float('inf')
            max_u = float('-inf')
            min_v = float('inf')
            max_v = float('-inf')

            # Get face UV bounds for Newton-Raphson initial guess
            face_u_min, face_u_max, face_v_min, face_v_max = face_shape.ParameterRange

            for point in sample_points:
                try:
                    # Use Newton-Raphson to find true line-surface intersection
                    best_uv = None
                    best_intersection = None

                    try:
                        # Initial guess
                        u_guess = (face_u_min + face_u_max) / 2.0
                        v_guess = (face_v_min + face_v_max) / 2.0

                        try:
                            u_guess, v_guess = surf.parameter(point)
                        except:
                            pass

                        # Iterate to find UV where surf.value(u,v) lies on projection line
                        for iteration in range(20):
                            surf_point = surf.value(u_guess, v_guess)

                            diff = surf_point - point
                            t = diff.dot(direction)
                            closest_on_line = point + direction * t
                            dist = surf_point.distanceToPoint(closest_on_line)

                            if dist < 0.01:
                                best_uv = (u_guess, v_guess)
                                best_intersection = surf_point
                                break

                            # Compute gradient
                            du = (face_u_max - face_u_min) * 0.001
                            dv = (face_v_max - face_v_min) * 0.001

                            try:
                                surf_u_plus = surf.value(u_guess + du, v_guess)
                                surf_v_plus = surf.value(u_guess, v_guess + dv)

                                grad_u = (surf_u_plus - surf_point).normalize()
                                grad_v = (surf_v_plus - surf_point).normalize()

                                to_line = closest_on_line - surf_point

                                step_u = to_line.dot(grad_u) * du / du
                                step_v = to_line.dot(grad_v) * dv / dv

                                damping = 0.5
                                u_guess += step_u * damping
                                v_guess += step_v * damping

                            except:
                                if dist < 50.0:
                                    best_uv = (u_guess, v_guess)
                                    best_intersection = surf_point
                                break

                        if best_uv is None and iteration > 0:
                            surf_point = surf.value(u_guess, v_guess)
                            diff = surf_point - point
                            t = diff.dot(direction)
                            closest_on_line = point + direction * t
                            dist = surf_point.distanceToPoint(closest_on_line)

                            if dist < 50.0:
                                best_uv = (u_guess, v_guess)
                                best_intersection = surf_point

                    except:
                        # Fallback to sampling
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

                    if best_uv and best_intersection:
                        u, v = best_uv
                        min_u = min(min_u, u)
                        max_u = max(max_u, u)
                        min_v = min(min_v, v)
                        max_v = max(max_v, v)

                        curve_viz_points.append((point.x, point.y, point.z))
                        proj_viz_points.append((best_intersection.x, best_intersection.y, best_intersection.z))
                        line_viz_points.append((point.x, point.y, point.z))
                        line_viz_points.append((best_intersection.x, best_intersection.y, best_intersection.z))

                except Exception as e:
                    continue

            # Print results
            FreeCAD.Console.PrintMessage("\n=== PROJECTION RESULTS ===\n")
            FreeCAD.Console.PrintMessage(f"Projection direction: {direction}\n")
            FreeCAD.Console.PrintMessage(f"Face UV range: U=[{face_u_min:.4f}, {face_u_max:.4f}], V=[{face_v_min:.4f}, {face_v_max:.4f}]\n")
            FreeCAD.Console.PrintMessage(f"Projected curve UV bounds: U=[{min_u:.4f}, {max_u:.4f}], V=[{min_v:.4f}, {max_v:.4f}]\n")

            u_covered = min_u <= face_u_min and max_u >= face_u_max
            v_covered = min_v <= face_v_min and max_v >= face_v_max

            FreeCAD.Console.PrintMessage(f"U direction covered: {u_covered} (extends {min_u - face_u_min:.4f} before, {max_u - face_u_max:.4f} after)\n")
            FreeCAD.Console.PrintMessage(f"V direction covered: {v_covered} (extends {min_v - face_v_min:.4f} before, {max_v - face_v_max:.4f} after)\n")
            FreeCAD.Console.PrintMessage(f"Successfully projected {len(curve_viz_points)} points\n")
            FreeCAD.Console.PrintMessage("==========================\n\n")

            # Create visualization
            if len(curve_viz_points) == 0:
                FreeCAD.Console.PrintWarning("No points were successfully projected!\n")
                return

            self.vis_root = coin.SoSeparator()
            sg = FreeCADGui.ActiveDocument.ActiveView.getSceneGraph()
            sg.addChild(self.vis_root)

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

            # Add UV direction arrows to show which way U and V go on the surface
            try:
                # Get face center
                face_center = face_shape.CenterOfMass
                u_center = (face_u_min + face_u_max) / 2.0
                v_center = (face_v_min + face_v_max) / 2.0

                # Sample points to show U and V directions
                u_range = face_u_max - face_u_min
                v_range = face_v_max - face_v_min

                # U direction arrow (at center V, varying U)
                u_start = surf.value(u_center, v_center)
                u_end = surf.value(u_center + u_range * 0.2, v_center)  # 20% of U range

                # V direction arrow (at center U, varying V)
                v_start = surf.value(u_center, v_center)
                v_end = surf.value(u_center, v_center + v_range * 0.2)  # 20% of V range

                # Yellow arrow for U direction
                u_arrow_sep = coin.SoSeparator()
                u_arrow_mat = coin.SoMaterial()
                u_arrow_mat.diffuseColor = (1, 1, 0)  # Yellow
                u_arrow_sep.addChild(u_arrow_mat)

                u_arrow_style = coin.SoDrawStyle()
                u_arrow_style.lineWidth = 5
                u_arrow_sep.addChild(u_arrow_style)

                u_arrow_coords = coin.SoCoordinate3()
                u_arrow_coords.point.setValues(0, 2, [(u_start.x, u_start.y, u_start.z), (u_end.x, u_end.y, u_end.z)])
                u_arrow_sep.addChild(u_arrow_coords)
                u_arrow_sep.addChild(coin.SoLineSet())
                self.vis_root.addChild(u_arrow_sep)

                # Magenta arrow for V direction
                v_arrow_sep = coin.SoSeparator()
                v_arrow_mat = coin.SoMaterial()
                v_arrow_mat.diffuseColor = (1, 0, 1)  # Magenta
                v_arrow_sep.addChild(v_arrow_mat)

                v_arrow_style = coin.SoDrawStyle()
                v_arrow_style.lineWidth = 5
                v_arrow_sep.addChild(v_arrow_style)

                v_arrow_coords = coin.SoCoordinate3()
                v_arrow_coords.point.setValues(0, 2, [(v_start.x, v_start.y, v_start.z), (v_end.x, v_end.y, v_end.z)])
                v_arrow_sep.addChild(v_arrow_coords)
                v_arrow_sep.addChild(coin.SoLineSet())
                self.vis_root.addChild(v_arrow_sep)

                FreeCAD.Console.PrintMessage("UV direction indicators:\n")
                FreeCAD.Console.PrintMessage("  - Yellow arrow: U direction (increasing U)\n")
                FreeCAD.Console.PrintMessage("  - Magenta arrow: V direction (increasing V)\n")
            except Exception as arrow_error:
                FreeCAD.Console.PrintWarning(f"Could not create UV arrows: {arrow_error}\n")

            FreeCAD.Console.PrintMessage("Visualization created:\n")
            FreeCAD.Console.PrintMessage("  - Red points: Curve sample points\n")
            FreeCAD.Console.PrintMessage("  - Green points: Projected points on surface\n")
            FreeCAD.Console.PrintMessage("  - Blue lines: Projection rays\n")
            FreeCAD.Console.PrintMessage("  - Yellow arrow: U direction\n")
            FreeCAD.Console.PrintMessage("  - Magenta arrow: V direction\n")

            FreeCADGui.activeDocument().activeView().viewAxonometric()
            FreeCADGui.SendMsgToActiveView("ViewFit")

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error visualizing projection: {str(e)}\n")
            import traceback
            traceback.print_exc()


def visualize_selection(direction=None):
    """
    Visualize projection for the current selection.

    Usage:
        1. Select one edge (curve)
        2. Select one face
        3. Run this function

    Optional: Provide a direction vector, otherwise uses face normal
    """
    sel = FreeCADGui.Selection.getSelectionEx()

    if len(sel) < 2:
        FreeCAD.Console.PrintError("Please select a curve (edge) and a face\n")
        return

    # Find the edge and face from selection
    edge_obj = None
    edge_sub = None
    face_obj = None
    face_sub = None

    for sel_obj in sel:
        for sub in sel_obj.SubElementNames:
            if sub.startswith("Edge") and edge_obj is None:
                edge_obj = sel_obj.Object
                edge_sub = sub
            elif sub.startswith("Face") and face_obj is None:
                face_obj = sel_obj.Object
                face_sub = sub

    if not edge_obj or not face_obj:
        FreeCAD.Console.PrintError("Please select one edge and one face\n")
        return

    FreeCAD.Console.PrintMessage(f"Visualizing projection of {edge_obj.Name}.{edge_sub} onto {face_obj.Name}.{face_sub}\n")

    visualizer = ProjectionVisualizer()
    visualizer.visualize_projection(edge_obj, edge_sub, face_obj, face_sub, direction)


# Convenience function for the console
def run():
    """Quick run function - select an edge and face, then call this"""
    visualize_selection()
