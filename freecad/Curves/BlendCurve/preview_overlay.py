"""Real-time 3D preview overlay for blend curve operations.

This module provides live visual feedback during blend curve creation by
rendering a semi-transparent preview curve in the 3D viewport. The preview
updates dynamically as parameters change, using FreeCAD's Coin3D scene graph.

The preview system:
- Renders blend curves as transparent ghost lines before final creation
- Updates in real-time as scale, position, or continuity parameters change
- Uses Coin3D for efficient GPU-accelerated rendering
- Automatically cleans up when dialog closes
"""

import FreeCAD
import FreeCADGui
import Part
from pivy import coin


class BlendCurvePreview:
    """Real-time visual preview of blend curves in the 3D viewport.

    Renders a semi-transparent curve overlay that updates dynamically as
    parameters change. Uses Coin3D scene graph for efficient rendering.

    The preview is displayed as a light blue, partially transparent line
    that gives immediate visual feedback without creating actual geometry.

    Attributes:
        root_separator (coin.SoSeparator): Root node of the scene graph
        preview_material (coin.SoMaterial): Material defining color/transparency
        preview_coordinates (coin.SoCoordinate3): 3D point coordinates
        preview_lineset (coin.SoLineSet): Line segments connecting points
        is_active (bool): Whether preview is currently displaying
        scene_graph_added (bool): Whether scene graph is attached to viewport
        preview_color (tuple): RGB color (0.0-1.0 range)
        line_width (float): Width of preview line in pixels
        transparency (float): 0.0 = opaque, 1.0 = fully transparent
    """

    def __init__(self):
        """Initialize the blend curve preview system.

        Sets up scene graph components and default styling. The actual
        Coin3D scene graph is created lazily on first preview update.
        """
        # Scene graph components (initialized on first use)
        self.root_separator = None
        self.preview_material = None
        self.preview_coordinates = None
        self.preview_lineset = None

        # Preview state
        self.is_active = False
        self.scene_graph_added = False

        # Preview styling (customizable)
        self.preview_color = (0.0, 0.5, 1.0)  # Light blue
        self.line_width = 3.0  # Pixel width
        self.transparency = 0.3  # 30% transparent (70% opaque for visibility)

        # Cached blend curve shape
        self._cached_blend_shape = None

    def initialize_scene_graph(self):
        """Create and attach the Coin3D scene graph to the viewport.

        Builds a scene graph hierarchy with material, draw style, coordinates,
        and line set nodes. Attaches the graph to the active 3D view.

        The scene graph structure:
            SoSeparator (root)
            ├── SoMaterial (color and transparency)
            ├── SoDrawStyle (line width)
            ├── SoCoordinate3 (3D points)
            └── SoLineSet (line segments)
        """
        if self.scene_graph_added:
            return

        # Create root separator
        self.root_separator = coin.SoSeparator()

        # Set up material (color and transparency)
        self.preview_material = coin.SoMaterial()
        self.preview_material.diffuseColor.setValue(self.preview_color)
        self.preview_material.transparency.setValue(self.transparency)

        # Set up draw style (line width)
        draw_style = coin.SoDrawStyle()
        draw_style.lineWidth.setValue(self.line_width)

        # Create coordinate holder
        self.preview_coordinates = coin.SoCoordinate3()

        # Create line set to draw the curve
        self.preview_lineset = coin.SoLineSet()

        # Build scene graph hierarchy
        self.root_separator.addChild(self.preview_material)
        self.root_separator.addChild(draw_style)
        self.root_separator.addChild(self.preview_coordinates)
        self.root_separator.addChild(self.preview_lineset)

        # Add to active view
        view = FreeCADGui.ActiveDocument.ActiveView
        scene = view.getSceneGraph()
        scene.addChild(self.root_separator)

        self.scene_graph_added = True
        self.is_active = True

    def update_preview(self, blend_curve_shape):
        """
        Update the preview with a new blend curve shape.

        Args:
            blend_curve_shape: Part.Shape of the blend curve to preview
        """
        if not blend_curve_shape:
            self.clear_preview()
            return

        try:
            # Initialize scene graph if needed
            if not self.scene_graph_added:
                self.initialize_scene_graph()

            # Discretize the curve into points for visualization
            points = self._discretize_curve(blend_curve_shape)

            # Update coordinates
            self.preview_coordinates.point.setNum(len(points))
            for i, pt in enumerate(points):
                self.preview_coordinates.point.set1Value(i, pt.x, pt.y, pt.z)

            # Set line segments (connect all points in sequence)
            self.preview_lineset.numVertices.setValue(len(points))

            # Cache the shape
            self._cached_blend_shape = blend_curve_shape

        except Exception as e:
            FreeCAD.Console.PrintError(f"Preview update failed: {str(e)}\n")

    def _discretize_curve(self, shape, num_points=50):
        """
        Convert curve shape into discrete points for visualization.

        Args:
            shape: Part.Shape containing the curve
            num_points: Number of points to sample

        Returns:
            List of FreeCAD.Vector points
        """
        if not shape or not shape.Edges:
            return []

        edge = shape.Edges[0]  # Get first edge
        points = []

        # Sample points along the curve parameter space
        param_range = edge.LastParameter - edge.FirstParameter
        for i in range(num_points):
            param = edge.FirstParameter + (i / (num_points - 1)) * param_range
            point = edge.valueAt(param)
            points.append(point)

        return points

    def clear_preview(self):
        """Clear the preview without removing scene graph.

        Empties the coordinate and line data, hiding the preview while
        keeping the scene graph structure intact for future updates.
        This is more efficient than removing and recreating the scene graph.
        """
        if not self.scene_graph_added:
            return

        try:
            # Clear coordinates
            if self.preview_coordinates:
                self.preview_coordinates.point.setNum(0)

            # Clear line segments
            if self.preview_lineset:
                self.preview_lineset.numVertices.setValue(0)

            self._cached_blend_shape = None

        except Exception as e:
            FreeCAD.Console.PrintError(f"Preview clear failed: {str(e)}\n")

    def remove_from_scene(self):
        """Completely remove preview from scene graph.

        Detaches the scene graph from the viewport and cleans up all resources.
        Called automatically on dialog close or object destruction.
        After calling this, the preview must be reinitialized to display again.
        """
        if not self.scene_graph_added:
            return

        try:
            view = FreeCADGui.ActiveDocument.ActiveView
            scene = view.getSceneGraph()
            scene.removeChild(self.root_separator)

            self.scene_graph_added = False
            self.is_active = False
            self._cached_blend_shape = None

        except Exception as e:
            FreeCAD.Console.PrintError(f"Scene removal failed: {str(e)}\n")

    def set_color(self, r, g, b):
        """Change the preview line color.

        Args:
            r (float): Red component (0.0-1.0)
            g (float): Green component (0.0-1.0)
            b (float): Blue component (0.0-1.0)
        """
        self.preview_color = (r, g, b)
        if self.preview_material:
            self.preview_material.diffuseColor.setValue(r, g, b)

    def set_transparency(self, value):
        """Change preview transparency.

        Args:
            value (float): Transparency level (0.0 = opaque, 1.0 = fully transparent)
        """
        self.transparency = value
        if self.preview_material:
            self.preview_material.transparency.setValue(value)

    def __del__(self):
        """Destructor - ensures preview is cleaned up.

        Automatically removes the scene graph when the preview object
        is garbage collected, preventing memory leaks and scene graph pollution.
        """
        self.remove_from_scene()
