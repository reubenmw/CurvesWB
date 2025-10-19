# -*- coding: utf-8 -*-

__title__ = 'Blend Curve Logic'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'Core logic for blend curve creation and trimming'

import FreeCAD
import Part

# Import from existing blend_curve module
from freecad.Curves.blend_curve import BlendCurve, PointOnEdge


class BlendCurveLogic:
    """Logic layer for blend curve creation"""

    def __init__(self):
        self.edge1 = None
        self.edge2 = None
        self.point1 = None  # PointOnEdge
        self.point2 = None  # PointOnEdge
        self.blend_curve = None  # BlendCurve
        self.scale_mode = 'auto'  # 'auto', 'manual', 'optimize'
        self.trim_mode = 'auto'  # 'auto', 'manual', 'none'
        self.continuity1 = 1  # G1 by default
        self.continuity2 = 1

    def set_edge1(self, obj, subname, parameter):
        """Set first edge and blend point"""
        edge = obj.Shape.getElement(subname)
        self.edge1 = (obj, subname, edge)
        self.point1 = PointOnEdge(edge, parameter, self.continuity1)

    def set_edge2(self, obj, subname, parameter):
        """Set second edge and blend point"""
        edge = obj.Shape.getElement(subname)
        self.edge2 = (obj, subname, edge)
        self.point2 = PointOnEdge(edge, parameter, self.continuity2)

    def set_continuity(self, edge_num, continuity):
        """Set G0, G1, G2, or G3 continuity (0-3)"""
        if edge_num == 1:
            self.continuity1 = continuity
            if self.point1:
                self.point1.continuity = continuity
        else:
            self.continuity2 = continuity
            if self.point2:
                self.point2.continuity = continuity

    def set_scale_mode(self, mode):
        """Set scale mode: 'auto', 'manual', or 'optimize'"""
        self.scale_mode = mode

    def set_trim_mode(self, mode):
        """Set trim mode: 'auto', 'manual', or 'none'"""
        self.trim_mode = mode

    def compute_blend(self):
        """Generate blend curve using current settings"""
        if not self.point1 or not self.point2:
            raise ValueError("Both edges must be selected")

        self.blend_curve = BlendCurve(self.point1, self.point2)

        if self.scale_mode == 'auto':
            self.blend_curve.auto_scale()
        elif self.scale_mode == 'optimize':
            self.blend_curve.minimize_curvature()
        # Manual scale handled separately via set_manual_scales()

        self.blend_curve.perform()
        return self.blend_curve

    def set_manual_scales(self, scale1, scale2):
        """Set manual scale values"""
        if self.blend_curve:
            self.blend_curve.scale1 = scale1
            self.blend_curve.scale2 = scale2
            self.blend_curve.perform()

    def execute_blend(self, params):
        """Create final FreeCAD blend curve object from UI parameters"""
        try:
            # Extract parameters from dialog
            curve1_obj = params["curve1_obj"]
            curve1_subname = params["curve1_subname"]
            curve1_position = params["curve1_position"]
            curve1_scale = params["curve1_scale"]
            curve1_continuity = params["curve1_continuity"]

            curve2_obj = params["curve2_obj"]
            curve2_subname = params["curve2_subname"]
            curve2_position = params["curve2_position"]
            curve2_scale = params["curve2_scale"]
            curve2_continuity = params["curve2_continuity"]

            FreeCAD.Console.PrintMessage("Getting edges...\n")

            # Get the edges
            edge1 = curve1_obj.Shape.getElement(curve1_subname)
            edge2 = curve2_obj.Shape.getElement(curve2_subname)

            FreeCAD.Console.PrintMessage(f"Edge1 length: {edge1.Length}\n")
            FreeCAD.Console.PrintMessage(f"Edge2 length: {edge2.Length}\n")

            # Convert position (mm) to parameter
            # For now, use position as a ratio of curve length
            if edge1.Length > 0:
                param1 = edge1.FirstParameter + (curve1_position / edge1.Length) * (edge1.LastParameter - edge1.FirstParameter)
            else:
                param1 = edge1.FirstParameter

            if edge2.Length > 0:
                param2 = edge2.FirstParameter + (curve2_position / edge2.Length) * (edge2.LastParameter - edge2.FirstParameter)
            else:
                param2 = edge2.FirstParameter

            FreeCAD.Console.PrintMessage(f"Param1: {param1}, Param2: {param2}\n")
            FreeCAD.Console.PrintMessage(f"Creating PointOnEdge objects...\n")

            # Create PointOnEdge objects with proper continuity
            # Note: Don't set size here - it will be set via BlendCurve.scale1/scale2 properties
            self.point1 = PointOnEdge(edge1, param1, curve1_continuity)
            self.point2 = PointOnEdge(edge2, param2, curve2_continuity)

            FreeCAD.Console.PrintMessage(f"Point1: {self.point1}\n")
            FreeCAD.Console.PrintMessage(f"Point2: {self.point2}\n")
            FreeCAD.Console.PrintMessage(f"Creating BlendCurve...\n")

            # Create blend curve
            self.blend_curve = BlendCurve(self.point1, self.point2)

            FreeCAD.Console.PrintMessage(f"Setting scales: {curve1_scale}, {curve2_scale}\n")
            # Note: Negative scales flip the tangent direction
            self.blend_curve.scale1 = curve1_scale
            self.blend_curve.scale2 = curve2_scale

            FreeCAD.Console.PrintMessage("Performing blend...\n")
            self.blend_curve.perform()

            FreeCAD.Console.PrintMessage("Creating FreeCAD object...\n")

            # Create a FeaturePython object with custom ViewProvider for double-click editing
            doc = FreeCAD.ActiveDocument
            obj = doc.addObject("Part::FeaturePython", "BlendCurve")

            # Store blend parameters as properties for re-editing
            # Curve 1 properties
            obj.addProperty("App::PropertyLink", "Curve1Object", "Curve 1", "First curve object")
            obj.addProperty("App::PropertyString", "Curve1SubName", "Curve 1", "First curve sub-element name (e.g., Edge1)")
            obj.addProperty("App::PropertyFloat", "Curve1Scale", "Curve 1", "First curve scale factor")
            obj.addProperty("App::PropertyFloat", "Curve1Position", "Curve 1", "Position along first curve (mm)")
            obj.addProperty("App::PropertyInteger", "Curve1Continuity", "Curve 1", "Continuity at first curve (0=G0, 1=G1, 2=G2, 3=G3)")

            # Curve 2 properties
            obj.addProperty("App::PropertyLink", "Curve2Object", "Curve 2", "Second curve object")
            obj.addProperty("App::PropertyString", "Curve2SubName", "Curve 2", "Second curve sub-element name (e.g., Edge1)")
            obj.addProperty("App::PropertyFloat", "Curve2Scale", "Curve 2", "Second curve scale factor")
            obj.addProperty("App::PropertyFloat", "Curve2Position", "Curve 2", "Position along second curve (mm)")
            obj.addProperty("App::PropertyInteger", "Curve2Continuity", "Curve 2", "Continuity at second curve (0=G0, 1=G1, 2=G2, 3=G3)")

            # Set the property values from parameters
            obj.Curve1Object = curve1_obj
            obj.Curve1SubName = curve1_subname
            obj.Curve1Scale = curve1_scale
            obj.Curve1Position = curve1_position
            obj.Curve1Continuity = curve1_continuity

            obj.Curve2Object = curve2_obj
            obj.Curve2SubName = curve2_subname
            obj.Curve2Scale = curve2_scale
            obj.Curve2Position = curve2_position
            obj.Curve2Continuity = curve2_continuity

            # Assign the shape
            obj.Shape = self.blend_curve.shape

            # Attach our custom ViewProvider for double-click editing support
            from .blend_curve_vp import BlendCurveViewProvider
            BlendCurveViewProvider(obj.ViewObject)

            # Make sure it's visible with default appearance
            if obj.ViewObject:
                obj.ViewObject.Visibility = True
                obj.ViewObject.LineWidth = 2.0
                # Use default line color (no explicit color set)

            doc.recompute()

            FreeCAD.Console.PrintMessage("Blend curve created successfully!\n")
            return obj

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error in execute_blend: {str(e)}\n")
            import traceback
            FreeCAD.Console.PrintError(traceback.format_exc())
            raise
