# -*- coding: utf-8 -*-

"""
Vector Gizmo - Reusable 3D Arrow Direction Indicator

This module provides a reusable 3D arrow gizmo for visualizing and manipulating
vector directions in FreeCAD. It's designed to be easily integrated into any
tool that needs vector direction input with visual feedback.

Classes:
    VectorGizmo: Main 3D arrow gizmo class
    VectorGizmoUI: Standardized UI integration helper

Usage:
    from freecad.Curves.Utils.VectorGizmo import VectorGizmo, VectorGizmoUI
    
    # Create gizmo
    gizmo = VectorGizmo(position, direction)
    
    # Integrate with UI
    ui_helper = VectorGizmoUI(gizmo, dialog, x_field, y_field, z_field)
"""

from .vector_gizmo import VectorGizmo
from .ui_integration import VectorGizmoUI

__all__ = ['VectorGizmo', 'VectorGizmoUI']
