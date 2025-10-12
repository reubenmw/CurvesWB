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

try:
    import BOPTools.SplitAPI
    splitAPI = BOPTools.SplitAPI
except ImportError:
    FreeCAD.Console.PrintError("Failed importing BOPTools. Fallback to Part API\n")
    splitAPI = Part.BOPTools.SplitAPI


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
        self._cached_split_faces = None  # Cache split faces for hover detection
        self._last_face_shape = None  # Cache face shape for UV calculations

        # Preview state
        self.is_active = False
        self.scene_graph_added = False
        self.hover_mode = True  # New: show preview only on hover

        # Preview colors with transparency
        self.keep_color = (0.0, 0.8, 0.0)  # Green (not used in hover mode)
        self.remove_color = (0.8, 0.0, 0.0)  # Red
        self.transparency = 0.7  # 70% transparent

        # Performance requirements
        self.max_response_time = 0.1  # 100ms max response time

        # Hover state
        self.current_hover_point = None
        self.face_object_ref = None
        self.trimming_curves_ref = None
        self.projection_direction_ref = None
        
    def show_preview(self, face_object, trimming_curves, projection_direction=None, trim_point=None):
        """
        Show the transparent preview overlay.

        Args:
            face_object: Tuple of (obj, subname) for the target face
            trimming_curves: List of (obj, subname) tuples for trimming curves
            projection_direction: FreeCAD.Vector or None for auto direction
            trim_point: FreeCAD.Vector point to determine which region to delete (new UX)
        """
        try:
            start_time = time.time()
            
            # Check if we can use cached results
            # NOTE: Don't use cache during hover mode - trim_point changes constantly
            # if self._can_use_cache(face_object, trimming_curves, projection_direction):
            #     self._show_cached_preview()
            #     return
            
            # Calculate preview mesh (pass trim_point for intelligent region selection)
            keep_mesh, remove_mesh = self._calculate_trim_preview(
                face_object, trimming_curves, projection_direction, trim_point
            )
            
            if not keep_mesh and not remove_mesh:
                FreeCAD.Console.PrintWarning("No preview geometry generated\n")
                # Hide preview if no geometry
                if self.scene_graph_added:
                    self._remove_from_scene()
                return

            # Force clean rebuild to avoid mesh artifacts
            # Remove old scene graph if it exists
            if self.scene_graph_added:
                self._remove_from_scene()

            # Clear scene graph and recreate
            self._clear_scene_graph()
            self._ensure_scene_graph()
            self._update_preview_mesh(keep_mesh, remove_mesh)

            # Add fresh scene graph to scene
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
    
    def _calculate_trim_preview(self, face_object, trimming_curves, projection_direction, trim_point=None):
        """
        Calculate trim preview showing only the delete (red) region.

        NEW UX: Only show red overlay on the region that will be DELETED.
        The region to delete is determined by the trim_point - the region containing
        the point will be deleted.

        Args:
            face_object: Tuple of (obj, subname) for the target face
            trimming_curves: List of (obj, subname) tuples for trimming curves
            projection_direction: FreeCAD.Vector or None for auto direction
            trim_point: FreeCAD.Vector to determine which region to delete

        Returns:
            Tuple of (keep_mesh, remove_mesh) where keep_mesh is None (new UX)
        """
        try:
            # Get face shape
            face_obj, face_subname = face_object
            face_shape = face_obj.Shape.getElement(face_subname)

            if not isinstance(face_shape, Part.Face):
                return [], []

            # If no trimming curves, show whole face as "keep"
            if not trimming_curves:
                keep_mesh = self._mesh_face_region(face_shape)
                return keep_mesh, []

            # Determine projection direction if not provided
            if projection_direction is None:
                try:
                    u_mid = (face_shape.ParameterRange[0] + face_shape.ParameterRange[1]) / 2.0
                    v_mid = (face_shape.ParameterRange[2] + face_shape.ParameterRange[3]) / 2.0
                    projection_direction = face_shape.normalAt(u_mid, v_mid)
                except:
                    projection_direction = FreeCAD.Vector(0, 0, 1)

            # Get original edges (not projected) - same as TrimFace
            original_edges = []
            for curve_obj, curve_subname in trimming_curves:
                edge_shape = curve_obj.Shape.getElement(curve_subname)
                if isinstance(edge_shape, Part.Edge):
                    original_edges.append(edge_shape)

            if not original_edges:
                FreeCAD.Console.PrintWarning("No valid edges found\n")
                keep_mesh = self._mesh_face_region(face_shape)
                return keep_mesh, []

            # Create wires from sorted edges (same as TrimFace)
            wires = [Part.Wire(el) for el in Part.sortEdges(original_edges)]

            # Try to split the face using original wires (not projected)
            keep_face, remove_face = self._create_trim_regions(
                face_shape, wires, projection_direction, trim_point
            )

            # Generate meshes for visualization
            # IMPORTANT: Always regenerate meshes, don't use cached mesh when face changes
            keep_mesh = self._mesh_face_region(keep_face) if keep_face else []
            remove_mesh = self._mesh_face_region(remove_face) if remove_face else []

            return keep_mesh, remove_mesh

        except Exception as e:
            FreeCAD.Console.PrintError(f"Preview calculation failed: {str(e)}\n")
            import traceback
            traceback.print_exc()
            # Fallback: show original face as "keep"
            try:
                face_obj, face_subname = face_object
                face_shape = face_obj.Shape.getElement(face_subname)
                keep_mesh = self._mesh_face_region(face_shape)
                return keep_mesh, []
            except:
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
                projection_result = face_shape.project([edge_shape])
                
                # Handle both single shape and list results
                if projection_result:
                    # Ensure we have a list to work with
                    if isinstance(projection_result, Part.Shape):
                        projection_result = [projection_result]
                    
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
    
    def _create_trim_regions(self, face_shape, wires, projection_direction, trim_point=None):
        """
        Create keep and remove regions by splitting the face with wires.

        Uses EXACTLY the same algorithm as TrimFace: takes original wires,
        translates and extrudes them to create cutting tools, then slices the face.

        NEW UX: Uses trim_point to determine which region to DELETE (show in red).
        The face containing the trim_point will be marked as the delete region.

        Args:
            face_shape: Part.Face to trim
            wires: List of Part.Wire objects (original, not projected)
            projection_direction: FreeCAD.Vector for projection/extrusion direction
            trim_point: FreeCAD.Vector to determine which region to delete

        Returns:
            Tuple of (keep_face, remove_face) where keep_face is None (new UX)
        """
        try:
            if not wires:
                return face_shape, None

            # Normalize projection direction
            v = projection_direction.normalize()

            # Calculate extrusion distance - EXACTLY as TrimFace does
            union = Part.Compound(wires + [face_shape])
            d = 2 * union.BoundBox.DiagonalLength

            # Create cutting tools - EXACTLY as TrimFace does
            cuttool = []
            for i, w in enumerate(wires):
                try:
                    # Translate and extrude - EXACTLY as TrimFace
                    w.translate(v * d)
                    tool = w.extrude(-v * d * 2)
                    cuttool.append(tool)
                except Exception as e:
                    FreeCAD.Console.PrintWarning(f"Failed to create cutting tool {i}: {str(e)}\n")

            if not cuttool:
                FreeCAD.Console.PrintWarning("No valid cutting tools created\n")
                return face_shape, None

            # Slice the face - EXACTLY as TrimFace does
            try:
                # Check if we can use cached split faces
                use_cached = (self._cached_split_faces is not None and
                             self._last_face_shape is face_shape)

                if use_cached:
                    bf = self._cached_split_faces
                else:
                    bf = splitAPI.slice(face_shape, cuttool, "Split", 1e-6)
                    # Cache the split result for next hover
                    self._cached_split_faces = bf
                    self._last_face_shape = face_shape

                if bf and hasattr(bf, 'Faces') and len(bf.Faces) > 1:
                    # Successfully split!

                    # NEW UX: No green overlay, only show red for area to be deleted
                    # Use trim_point to determine which face to delete (same logic as TrimFace)
                    remove_face = None

                    if trim_point:
                        try:
                            # Convert 3D point to UV parameters on face
                            u, v = face_shape.Surface.parameter(trim_point)

                            # Find which face contains this point - that's the one to DELETE
                            found_face = False
                            for i, f in enumerate(bf.Faces):
                                if f.isPartOfDomain(u, v):
                                    remove_face = f
                                    found_face = True
                                    break

                            # If no face contains the point, don't show anything
                            if not found_face:
                                return None, None

                        except Exception as e:
                            FreeCAD.Console.PrintWarning(f"Could not determine face from trim point: {e}\n")
                            return None, None
                    else:
                        # No trim point - show first face as delete region
                        remove_face = bf.Faces[0]

                    # Don't show green overlay
                    keep_face = None

                    return keep_face, remove_face
                else:
                    FreeCAD.Console.PrintWarning(f"Face splitting produced no split (only {len(bf.Faces)} face(s))\n")
                    return None, None

            except Exception as split_error:
                FreeCAD.Console.PrintWarning(f"BOPTools split failed: {str(split_error)}\n")
                import traceback
                traceback.print_exc()
                return face_shape, None

        except Exception as e:
            FreeCAD.Console.PrintError(f"Region creation failed: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return face_shape, None
    
    def _mesh_face_region(self, face_region):
        """
        Generate mesh points and triangles from a face region for visualization.

        Uses FreeCAD's tessellation to create a triangulated mesh representation
        of the face suitable for rendering with Coin3D.

        Args:
            face_region: Part.Face object or None

        Returns:
            Tuple of (points, triangles) where:
            - points is a list of 3D coordinate tuples
            - triangles is a list of triangle index tuples
        """
        if not face_region:
            return []

        # Handle both single faces and compounds of faces
        faces_to_mesh = []
        if hasattr(face_region, 'Faces'):
            faces_to_mesh = face_region.Faces
        elif hasattr(face_region, 'tessellate'):
            faces_to_mesh = [face_region]
        else:
            return []

        try:
            all_points = []
            all_triangles = []
            point_offset = 0

            for face in faces_to_mesh:
                if not hasattr(face, 'tessellate'):
                    continue

                # Get tessellated mesh data
                # Returns (vertices, triangles) where:
                # - vertices is a list of FreeCAD.Vector
                # - triangles is a list of (i1, i2, i3) index tuples
                tessellation = face.tessellate(0.5)  # 0.5mm tolerance for performance

                if tessellation and len(tessellation) >= 2:
                    points, triangles = tessellation

                    # Convert FreeCAD vectors to tuples
                    for point in points:
                        all_points.append((point.x, point.y, point.z))

                    # Adjust triangle indices for offset and add to list
                    for tri in triangles:
                        adjusted_tri = (
                            tri[0] + point_offset,
                            tri[1] + point_offset,
                            tri[2] + point_offset
                        )
                        all_triangles.append(adjusted_tri)

                    point_offset += len(points)

            return (all_points, all_triangles)

        except Exception as e:
            FreeCAD.Console.PrintWarning(f"Mesh generation failed: {str(e)}\n")
            import traceback
            traceback.print_exc()
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
            
            # Create indexed face set nodes (for triangle rendering)
            self.keep_faces = coin.SoIndexedFaceSet()
            self.remove_faces = coin.SoIndexedFaceSet()
            
            # Build scene graph structure
            # Keep region (green)
            keep_separator = coin.SoSeparator()

            # Add draw style for proper rendering
            keep_draw_style = coin.SoDrawStyle()
            keep_draw_style.style = coin.SoDrawStyle.FILLED

            # Disable back-face culling to see faces from both sides
            keep_shape_hints = coin.SoShapeHints()
            keep_shape_hints.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
            keep_shape_hints.shapeType = coin.SoShapeHints.UNKNOWN_SHAPE_TYPE

            # Add polygon offset to render on top of existing geometry
            # Very strong offset values to prevent z-fighting/clipping during hover
            keep_polygon_offset = coin.SoPolygonOffset()
            keep_polygon_offset.factor.setValue(-50.0)
            keep_polygon_offset.units.setValue(-50.0)

            # Alternative approach: use complexity to force rendering on top
            keep_complexity = coin.SoComplexity()
            keep_complexity.value.setValue(0.8)

            keep_separator.addChild(keep_draw_style)
            keep_separator.addChild(keep_shape_hints)
            keep_separator.addChild(keep_polygon_offset)
            keep_separator.addChild(keep_complexity)
            keep_separator.addChild(self.keep_material)
            keep_separator.addChild(self.keep_coordinates)
            keep_separator.addChild(self.keep_faces)

            # Remove region (red)
            remove_separator = coin.SoSeparator()

            # Add draw style for proper rendering
            remove_draw_style = coin.SoDrawStyle()
            remove_draw_style.style = coin.SoDrawStyle.FILLED

            # Disable back-face culling to see faces from both sides
            remove_shape_hints = coin.SoShapeHints()
            remove_shape_hints.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
            remove_shape_hints.shapeType = coin.SoShapeHints.UNKNOWN_SHAPE_TYPE

            # Add polygon offset to render on top of existing geometry
            # Very strong offset values to prevent z-fighting/clipping during hover
            remove_polygon_offset = coin.SoPolygonOffset()
            remove_polygon_offset.factor.setValue(-50.0)
            remove_polygon_offset.units.setValue(-50.0)

            # Alternative approach: use complexity to force rendering on top
            remove_complexity = coin.SoComplexity()
            remove_complexity.value.setValue(0.8)

            remove_separator.addChild(remove_draw_style)
            remove_separator.addChild(remove_shape_hints)
            remove_separator.addChild(remove_polygon_offset)
            remove_separator.addChild(remove_complexity)
            remove_separator.addChild(self.remove_material)
            remove_separator.addChild(self.remove_coordinates)
            remove_separator.addChild(self.remove_faces)

            # Add both to root
            self.root_separator.addChild(keep_separator)
            self.root_separator.addChild(remove_separator)
    
    def _update_preview_mesh(self, keep_mesh, remove_mesh):
        """
        Update the preview mesh in the scene graph.

        This method takes the tessellated mesh data and converts it to Coin3D
        scene graph nodes for rendering.

        Args:
            keep_mesh: Tuple of (points, triangles) for the keep region
            remove_mesh: Tuple of (points, triangles) for the remove region
        """
        # Update keep region (green) - clear if no mesh
        if self.keep_coordinates:
            if keep_mesh and isinstance(keep_mesh, tuple) and len(keep_mesh) == 2:
                points, triangles = keep_mesh

                if points and triangles:
                    # Convert points to Coin3D format
                    coin_points = [coin.SbVec3f(*point) for point in points]
                    self.keep_coordinates.point.setValues(0, len(coin_points), coin_points)

                    # Convert triangles to coordIndex format
                    # Coin3D expects: i1, i2, i3, -1, i4, i5, i6, -1, ...
                    indices = []
                    for tri in triangles:
                        indices.extend([tri[0], tri[1], tri[2], -1])

                    self.keep_faces.coordIndex.setValues(0, len(indices), indices)

                    pass  # Mesh updated successfully
                else:
                    # Clear mesh - use deleteValues to properly remove
                    self.keep_coordinates.point.deleteValues(0)
                    self.keep_faces.coordIndex.deleteValues(0)
            else:
                # Clear mesh - use deleteValues to properly remove
                self.keep_coordinates.point.deleteValues(0)
                self.keep_faces.coordIndex.deleteValues(0)

        # Update remove region (red) - clear if no mesh
        if self.remove_coordinates:
            if remove_mesh and isinstance(remove_mesh, tuple) and len(remove_mesh) == 2:
                points, triangles = remove_mesh

                if points and triangles:
                    # Convert points to Coin3D format
                    coin_points = [coin.SbVec3f(*point) for point in points]
                    self.remove_coordinates.point.setValues(0, len(coin_points), coin_points)

                    # Convert triangles to coordIndex format
                    indices = []
                    for tri in triangles:
                        indices.extend([tri[0], tri[1], tri[2], -1])

                    self.remove_faces.coordIndex.setValues(0, len(indices), indices)

                    pass  # Mesh updated successfully
                else:
                    # Clear mesh - use deleteValues to properly remove
                    self.remove_coordinates.point.deleteValues(0)
                    self.remove_faces.coordIndex.deleteValues(0)
            else:
                # Clear mesh - use deleteValues to properly remove
                self.remove_coordinates.point.deleteValues(0)
                self.remove_faces.coordIndex.deleteValues(0)
    
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
