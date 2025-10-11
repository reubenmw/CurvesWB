# -*- coding: utf-8 -*-

__title__ = 'Trim face dialog - Transparent preview overlay'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'Real-time transparent preview system for trim face operations'

import FreeCAD
import FreeCADGui
import Part
import time
from pivy import coin
from .. import CoinNodes


class TrimPreviewOverlay:
    """
    Real-time visual preview showing trim areas in transparent colors.
    
    This class manages Coin3D scene graph overlays to provide immediate
    visual feedback showing what will be kept (green) and what will be
    removed (red) from the target face before applying the operation.
    """
    
    def __init__(self):
        # Scene graph components
        self.root_separator = None
        self.keep_material = None
        self.remove_material = None
        self.keep_coordinates = None
        self.remove_coordinates = None
        self.keep_faces = None
        self.remove_faces = None
        
        # Performance caching
        self._last_calculation_time = 0.0
        self._last_face_hash = None
        self._last_curves_hash = None
        self._cached_keep_mesh = None
        self._cached_remove_mesh = None
        
        # Preview state
        self.is_active = False
        self.scene_graph_added = False
        
        # Preview colors with transparency
        self.keep_color = (0.0, 0.8, 0.0)  # Green
        self.remove_color = (0.8, 0.0, 0.0)  # Red
        self.transparency = 0.7  # 70% transparent
        
        # Performance requirements
        self.max_response_time = 0.1  # 100ms max response time
        
    def show_preview(self, face_object, trimming_curves, projection_direction=None):
        """
        Show the transparent preview overlay.
        
        Args:
            face_object: Tuple of (obj, subname) for the target face
            trimming_curves: List of (obj, subname) tuples for trimming curves
            projection_direction: FreeCAD.Vector or None for auto direction
        """
        try:
            start_time = time.time()
            
            # Check if we can use cached results
            if self._can_use_cache(face_object, trimming_curves, projection_direction):
                self._show_cached_preview()
                return
            
            # Calculate preview mesh
            keep_mesh, remove_mesh = self._calculate_trim_preview(
                face_object, trimming_curves, projection_direction
            )
            
            if not keep_mesh and not remove_mesh:
                FreeCAD.Console.PrintWarning("No preview geometry generated\n")
                return
            
            # Create or update scene graph
            self._ensure_scene_graph()
            self._update_preview_mesh(keep_mesh, remove_mesh)
            
            # Add to scene if not already added
            if not self.scene_graph_added:
                self._add_to_scene()
            
            self.is_active = True
            
            # Cache the results
            self._cache_results(face_object, trimming_curves, projection_direction, 
                              keep_mesh, remove_mesh)
            
            calc_time = time.time() - start_time
            FreeCAD.Console.PrintMessage(f"Preview updated in {calc_time*1000:.1f}ms\n")
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to show preview: {str(e)}\n")
            self.hide_preview()
    
    def hide_preview(self):
        """Hide the transparent preview overlay."""
        if self.scene_graph_added:
            self._remove_from_scene()
        
        self.is_active = False
        FreeCAD.Console.PrintMessage("Preview hidden\n")
    
    def cleanup(self):
        """Clean up all resources and remove from scene."""
        self.hide_preview()
        self._clear_scene_graph()
        self._clear_cache()
    
    def _calculate_trim_preview(self, face_object, trimming_curves, projection_direction):
        """
        Non-destructive calculation of trim preview areas.
        
        This method performs the actual geometry analysis to determine
        which parts of the face will be kept and which will be removed.
        
        Args:
            face_object: Tuple of (obj, subname) for the target face
            trimming_curves: List of (obj, subname) tuples for trimming curves
            projection_direction: FreeCAD.Vector or None for auto direction
            
        Returns:
            Tuple of (keep_mesh, remove_mesh) where each is a list of points
        """
        try:
            # Get face shape
            face_obj, face_subname = face_object
            face_shape = face_obj.Shape.getElement(face_subname)
            
            if not isinstance(face_shape, Part.Face):
                return [], []
            
            # Determine projection direction
            if projection_direction is None:
                # Use face normal at center
                center = face_shape.CenterOfMass
                uv = face_shape.Surface.parameter(center)
                projection_direction = face_shape.normalAt(uv[0], uv[1])
            
            # Ensure direction is normalized
            if projection_direction.Length > 1e-6:
                projection_direction.normalize()
            else:
                projection_direction = FreeCAD.Vector(0, 0, 1)
            
            # Project trimming curves onto face
            projected_curves = self._project_curves_onto_face(
                trimming_curves, face_shape, projection_direction
            )
            
            if not projected_curves:
                return [], []
            
            # Create trim regions using boolean operations
            keep_region, remove_region = self._create_trim_regions(
                face_shape, projected_curves
            )
            
            # Generate mesh points for visualization
            keep_mesh = self._mesh_face_region(keep_region) if keep_region else []
            remove_mesh = self._mesh_face_region(remove_region) if remove_region else []
            
            return keep_mesh, remove_mesh
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"Preview calculation failed: {str(e)}\n")
            return [], []
    
    def _project_curves_onto_face(self, trimming_curves, face_shape, projection_direction):
        """
        Project trimming curves onto the target face.
        
        Args:
            trimming_curves: List of (obj, subname) tuples
            face_shape: Part.Face to project onto
            projection_direction: FreeCAD.Vector for projection direction
            
        Returns:
            List of Part.Wire objects representing projected curves
        """
        projected_wires = []
        
        try:
            for curve_obj, curve_subname in trimming_curves:
                # Get edge shape
                edge_shape = curve_obj.Shape.getElement(curve_subname)
                if not isinstance(edge_shape, Part.Edge):
                    continue
                
                # Project edge onto face
                projection_result = face_shape.project([edge_shape], projection_direction)
                
                if projection_result and len(projection_result) > 0:
                    # Get the projected edges and create wires
                    projected_edges = []
                    for proj_shape in projection_result:
                        if hasattr(proj_shape, 'Edges'):
                            projected_edges.extend(proj_shape.Edges)
                    
                    if projected_edges:
                        # Try to create a wire from projected edges
                        try:
                            wire = Part.Wire(projected_edges)
                            projected_wires.append(wire)
                        except:
                            # If wire creation fails, add edges individually
                            for edge in projected_edges:
                                try:
                                    wire = Part.Wire([edge])
                                    projected_wires.append(wire)
                                except:
                                    continue
            
            return projected_wires
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"Curve projection failed: {str(e)}\n")
            return []
    
    def _create_trim_regions(self, face_shape, projected_curves):
        """
        Create keep and remove regions using boolean operations.
        
        Args:
            face_shape: Part.Face to trim
            projected_curves: List of Part.Wire objects
            
        Returns:
            Tuple of (keep_face, remove_face) Part.Face objects
        """
        try:
            if not projected_curves:
                return face_shape, None
            
            # Create a compound face from all projected curves
            # This represents the area that will be removed
            trim_faces = []
            for wire in projected_curves:
                try:
                    # Create a face from the wire if it's closed
                    if wire.isClosed():
                        face = Part.Face(wire)
                        if face.isValid():
                            trim_faces.append(face)
                except:
                    continue
            
            if not trim_faces:
                return face_shape, None
            
            # Combine all trim faces
            if len(trim_faces) == 1:
                trim_region = trim_faces[0]
            else:
                # Fuse all trim faces together
                trim_region = trim_faces[0].fuse(*trim_faces[1:])
            
            # Perform boolean operation to determine keep/remove regions
            # The intersection of face and trim_region is what gets removed
            try:
                # Find the intersection (area to remove)
                intersection = face_shape.common(trim_region)
                
                # Find the difference (area to keep)
                difference = face_shape.cut(trim_region)
                
                return difference, intersection
                
            except Exception as e:
                FreeCAD.Console.PrintWarning(f"Boolean operation failed: {str(e)}\n")
                return face_shape, None
                
        except Exception as e:
            FreeCAD.Console.PrintError(f"Region creation failed: {str(e)}\n")
            return face_shape, None
    
    def _mesh_face_region(self, face_region):
        """
        Generate mesh points from a face region for visualization.
        
        Args:
            face_region: Part.Face object or None
            
        Returns:
            List of 3D points as tuples
        """
        if not face_region or not hasattr(face_region, ' tessellate'):
            return []
        
        try:
            # Use tessellation to generate mesh
            mesh_points = []
            
            # Get tessellated points
            tessellation = face_region.tessellate(0.1)  # 0.1mm tolerance
            
            if tessellation and len(tessellation) >= 2:
                points, triangles = tessellation
                
                # Convert FreeCAD vectors to tuples
                for point in points:
                    mesh_points.append((point.x, point.y, point.z))
            
            return mesh_points
            
        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Mesh generation failed: {str(e)}\n")
            return []
    
    def _ensure_scene_graph(self):
        """Ensure the scene graph structure exists."""
        if self.root_separator is None:
            # Create root separator
            self.root_separator = coin.SoSeparator()
            
            # Create materials for keep/remove regions
            self.keep_material = coin.SoMaterial()
            self.keep_material.diffuseColor.setValue(coin.SbColor(*self.keep_color))
            self.keep_material.transparency.setValue(self.transparency)
            
            self.remove_material = coin.SoMaterial()
            self.remove_material.diffuseColor.setValue(coin.SbColor(*self.remove_color))
            self.remove_material.transparency.setValue(self.transparency)
            
            # Create coordinate nodes
            self.keep_coordinates = coin.SoCoordinate3()
            self.remove_coordinates = coin.SoCoordinate3()
            
            # Create face set nodes
            self.keep_faces = coin.SoFaceSet()
            self.remove_faces = coin.SoFaceSet()
            
            # Build scene graph structure
            # Keep region (green)
            keep_separator = coin.SoSeparator()
            keep_separator.addChild(self.keep_material)
            keep_separator.addChild(self.keep_coordinates)
            keep_separator.addChild(self.keep_faces)
            
            # Remove region (red)
            remove_separator = coin.SoSeparator()
            remove_separator.addChild(self.remove_material)
            remove_separator.addChild(self.remove_coordinates)
            remove_separator.addChild(self.remove_faces)
            
            # Add both to root
            self.root_separator.addChild(keep_separator)
            self.root_separator.addChild(remove_separator)
    
    def _update_preview_mesh(self, keep_mesh, remove_mesh):
        """Update the preview mesh in the scene graph."""
        if self.keep_coordinates and keep_mesh:
            # Convert points to coin format
            coin_points = [coin.SbVec3f(*point) for point in keep_mesh]
            self.keep_coordinates.point.setValues(0, len(coin_points), coin_points)
            
            # Set face indices (simple triangulation)
            if len(coin_points) >= 3:
                indices = list(range(len(coin_points)))
                indices.append(-1)  # End of face
                self.keep_faces.coordIndex.setValues(0, len(indices), indices)
        
        if self.remove_coordinates and remove_mesh:
            # Convert points to coin format
            coin_points = [coin.SbVec3f(*point) for point in remove_mesh]
            self.remove_coordinates.point.setValues(0, len(coin_points), coin_points)
            
            # Set face indices
            if len(coin_points) >= 3:
                indices = list(range(len(coin_points)))
                indices.append(-1)  # End of face
                self.remove_faces.coordIndex.setValues(0, len(indices), indices)
    
    def _add_to_scene(self):
        """Add the preview overlay to the FreeCAD scene graph."""
        try:
            if self.root_separator and not self.scene_graph_added:
                # Get the active document's view
                active_view = FreeCADGui.ActiveDocument.ActiveView
                if active_view:
                    # Get the scene graph
                    scene_graph = active_view.getSceneGraph()
                    if scene_graph:
                        # Add our preview overlay
                        scene_graph.addChild(self.root_separator)
                        self.scene_graph_added = True
                        FreeCAD.Console.PrintMessage("Preview overlay added to scene\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to add preview to scene: {str(e)}\n")
    
    def _remove_from_scene(self):
        """Remove the preview overlay from the FreeCAD scene graph."""
        try:
            if self.root_separator and self.scene_graph_added:
                # Get the active document's view
                active_view = FreeCADGui.ActiveDocument.ActiveView
                if active_view:
                    # Get the scene graph
                    scene_graph = active_view.getSceneGraph()
                    if scene_graph:
                        # Remove our preview overlay
                        scene_graph.removeChild(self.root_separator)
                        self.scene_graph_added = False
                        FreeCAD.Console.PrintMessage("Preview overlay removed from scene\n")
        except Exception as e:
            FreeCAD.Console.PrintError(f"Failed to remove preview from scene: {str(e)}\n")
    
    def _clear_scene_graph(self):
        """Clear all scene graph components."""
        self.root_separator = None
        self.keep_material = None
        self.remove_material = None
        self.keep_coordinates = None
        self.remove_coordinates = None
        self.keep_faces = None
        self.remove_faces = None
    
    def _can_use_cache(self, face_object, trimming_curves, projection_direction):
        """Check if cached results can be used."""
        if not self._cached_keep_mesh and not self._cached_remove_mesh:
            return False
        
        # Calculate hashes for comparison
        current_face_hash = self._hash_face_object(face_object)
        current_curves_hash = self._hash_curves_list(trimming_curves)
        
        # Check if anything changed
        if (current_face_hash != self._last_face_hash or 
            current_curves_hash != self._last_curves_hash):
            return False
        
        # Check cache age (max 5 seconds)
        if time.time() - self._last_calculation_time > 5.0:
            return False
        
        return True
    
    def _cache_results(self, face_object, trimming_curves, projection_direction,
                      keep_mesh, remove_mesh):
        """Cache calculation results for performance."""
        self._last_calculation_time = time.time()
        self._last_face_hash = self._hash_face_object(face_object)
        self._last_curves_hash = self._hash_curves_list(trimming_curves)
        self._cached_keep_mesh = keep_mesh
        self._cached_remove_mesh = remove_mesh
    
    def _show_cached_preview(self):
        """Show the cached preview results."""
        if self._cached_keep_mesh or self._cached_remove_mesh:
            self._ensure_scene_graph()
            self._update_preview_mesh(self._cached_keep_mesh, self._cached_remove_mesh)
            
            if not self.scene_graph_added:
                self._add_to_scene()
            
            self.is_active = True
            FreeCAD.Console.PrintMessage("Using cached preview\n")
    
    def _clear_cache(self):
        """Clear cached results."""
        self._last_calculation_time = 0.0
        self._last_face_hash = None
        self._last_curves_hash = None
        self._cached_keep_mesh = None
        self._cached_remove_mesh = None
    
    def _hash_face_object(self, face_object):
        """Create a hash for the face object."""
        if not face_object:
            return None
        
        try:
            obj, subname = face_object
            # Use object name, subname, and shape hash
            shape_hash = hash(str(obj.Shape.getElement(subname).hashCode()))
            return hash((obj.Name, subname, shape_hash))
        except:
            return None
    
    def _hash_curves_list(self, trimming_curves):
        """Create a hash for the trimming curves list."""
        if not trimming_curves:
            return None
        
        try:
            curve_hashes = []
            for obj, subname in trimming_curves:
                shape_hash = hash(str(obj.Shape.getElement(subname).hashCode()))
                curve_hashes.append((obj.Name, subname, shape_hash))
            return hash(tuple(curve_hashes))
        except:
            return None
