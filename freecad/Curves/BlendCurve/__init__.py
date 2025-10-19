"""BlendCurve module for FreeCAD Curves Workbench.

This module provides an interactive tool for creating smooth blend curves
between two edges with full control over continuity, scale, position, and
trimming behavior.

Main Components:
    - BlendCurveCommand: FreeCAD command registration
    - BlendCurveTaskPanel: Interactive Qt dialog
    - BlendCurveLogic: Core blend curve computation
    - BlendCurveViewProvider: Double-click editing support
    - SelectionGate/Observers: Interactive selection handling
    - BlendCurvePreview: Real-time 3D preview overlay

Features:
    - G0-G3 continuity control at each endpoint
    - Adjustable scale and position along curves
    - Real-time preview with parameter changes
    - Automatic trimming of source curves
    - Double-click to re-edit existing blend curves
    - Theme-aware edge highlighting
    - Comprehensive validation and error handling
"""

import FreeCAD

# Module constants
DEBUG = False  # Set to True to enable debug console output


def debug(string):
    """Print debug message to FreeCAD console if DEBUG is enabled.

    Args:
        string (str): Message to print
    """
    if DEBUG:
        FreeCAD.Console.PrintMessage(string)
        FreeCAD.Console.PrintMessage("\n")


# Import main components for easy access
# Import command first - this registers the FreeCAD command
try:
    from .command import BlendCurveCommand
except ImportError as e:
    FreeCAD.Console.PrintError(f"BlendCurve command registration failed: {e}\n")

# Import other components
try:
    from .selection_handlers import (
        SelectionGate,
        EdgeSelectionObserver,
        BlendPointSelectionObserver,
    )
    from .blend_logic import BlendCurveLogic
    from .dialog_panel import BlendCurveTaskPanel
except ImportError as e:
    # During initial setup, these files may not exist yet
    FreeCAD.Console.PrintWarning(
        f"BlendCurve module components not fully loaded: {e}\n"
    )

# Public API - components available for import
__all__ = [
    "SelectionGate",
    "EdgeSelectionObserver",
    "BlendPointSelectionObserver",
    "BlendCurveLogic",
    "BlendCurveTaskPanel",
    "BlendCurveCommand",
    "DEBUG",
    "debug",
]
