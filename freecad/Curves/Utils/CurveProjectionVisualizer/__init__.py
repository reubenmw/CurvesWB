# -*- coding: utf-8 -*-

"""
Curve Projection Visualizer - Reusable Debug Tool

This module provides a reusable debug tool for visualizing how curves project
onto surfaces in FreeCAD. It's designed to be easily integrated into any
tool that needs to debug curve projection behavior.

Classes:
    ProjectionVisualizer: Main visualization class for curve projection debugging

Usage:
    from freecad.Curves.Utils.CurveProjectionVisualizer import ProjectionVisualizer
    
    # Create visualizer
    visualizer = ProjectionVisualizer()
    
    # Visualize projection
    visualizer.visualize_projection(curve_obj, curve_subname, face_obj, face_subname)
"""

from .projection_visualizer import ProjectionVisualizer

__all__ = ['ProjectionVisualizer']
