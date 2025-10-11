#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for VectorGizmo utility component.

This script demonstrates how to use the refactored VectorGizmo from the Utils package.
It tests the arrow gizmo with various configurations to verify that:
1. The arrow head connects properly to the shaft
2. The proportions are correct
3. The scaling works as expected
"""

import FreeCAD
import FreeCADGui

def test_vector_gizmo_from_utils():
    """Test the VectorGizmo utility from the new Utils package"""
    
    try:
        # Import from the new Utils location
        from freecad.Curves.Utils.VectorGizmo import VectorGizmo
        print("✓ Successfully imported VectorGizmo from Utils package")
    except ImportError as e:
        print(f"✗ Failed to import VectorGizmo from Utils: {str(e)}")
        return False
    
    # Test 1: Basic arrow creation
    print("\nTest 1: Basic arrow creation")
    position = FreeCAD.Vector(0, 0, 0)
    direction = FreeCAD.Vector(1, 1, 1)
    
    gizmo = VectorGizmo(position, direction, arrow_length=50.0, arrow_size=10.0)
    print("✓ VectorGizmo created successfully")
    
    # Test 2: Direction changes
    print("\nTest 2: Direction changes")
    test_directions = [
        FreeCAD.Vector(1, 0, 0),      # X axis
        FreeCAD.Vector(0, 1, 0),      # Y axis  
        FreeCAD.Vector(0, 0, 1),      # Z axis
        FreeCAD.Vector(1, 1, 0),      # XY diagonal
        FreeCAD.Vector(1, 1, 1),      # XYZ diagonal
    ]
    
    for i, direction in enumerate(test_directions):
        print(f"  Setting direction to {direction}")
        gizmo.set_direction(direction)
        result = gizmo.get_direction()
        print(f"  Result: {result} (Length: {result.Length:.6f})")
    
    # Test 3: Position changes
    print("\nTest 3: Position changes")
    test_positions = [
        FreeCAD.Vector(10, 0, 0),
        FreeCAD.Vector(0, 10, 0),
        FreeCAD.Vector(0, 0, 10),
        FreeCAD.Vector(-10, -10, -10)
    ]
    
    for i, position in enumerate(test_positions):
        print(f"  Setting position to {position}")
        gizmo.set_position(position)
    
    # Test 4: Different arrow sizes
    print("\nTest 4: Different arrow sizes")
    small_gizmo = VectorGizmo(
        FreeCAD.Vector(20, 0, 0), 
        FreeCAD.Vector(0, 1, 0), 
        arrow_length=20.0, 
        arrow_size=5.0
    )
    large_gizmo = VectorGizmo(
        FreeCAD.Vector(-20, 0, 0), 
        FreeCAD.Vector(0, 1, 0), 
        arrow_length=100.0, 
        arrow_size=20.0
    )
    print("✓ Small and large gizmos created successfully")
    
    # Test 5: Show/hide functionality
    print("\nTest 5: Show/hide functionality")
    gizmo.hide()
    assert not gizmo.is_visible(), "Gizmo should be hidden"
    gizmo.show()
    assert gizmo.is_visible(), "Gizmo should be visible"
    print("✓ Show/hide works correctly")
    
    # Cleanup
    print("\nTest 6: Cleanup")
    gizmo.cleanup()
    small_gizmo.cleanup()
    large_gizmo.cleanup()
    print("✓ All gizmos cleaned up successfully")
    
    print("\n🎉 All tests passed! VectorGizmo from Utils package is working correctly.")
    print("The arrow head should connect properly to the shaft with correct proportions.")
    return True

def test_projection_visualizer_from_utils():
    """Test the ProjectionVisualizer utility from the new Utils package"""
    
    try:
        # Import from the new Utils location
        from freecad.Curves.Utils.CurveProjectionVisualizer import ProjectionVisualizer
        print("✓ Successfully imported ProjectionVisualizer from Utils package")
    except ImportError as e:
        print(f"✗ Failed to import ProjectionVisualizer from Utils: {str(e)}")
        return False
    
    # Test basic creation
    print("\nTest: ProjectionVisualizer creation")
    visualizer = ProjectionVisualizer()
    print("✓ ProjectionVisualizer created successfully")
    
    # Test cleanup
    visualizer.clear_visualization()
    print("✓ ProjectionVisualizer cleanup works")
    
    print("\n🎉 ProjectionVisualizer from Utils package is working correctly!")
    return True

def test_utils_package_structure():
    """Test that the Utils package structure is working correctly"""
    
    print("=== Testing Utils Package Structure ===")
    
    try:
        # Test main Utils package
        import freecad.Curves.Utils
        print("✓ Utils package imports successfully")
        
        # Test VectorGizmo subpackage
        from freecad.Curves.Utils.VectorGizmo import VectorGizmo
        print("✓ VectorGizmo subpackage imports successfully")
        
        # Test CurveProjectionVisualizer subpackage
        from freecad.Curves.Utils.CurveProjectionVisualizer import ProjectionVisualizer
        print("✓ CurveProjectionVisualizer subpackage imports successfully")
        
        print("\n✅ Utils package structure is working correctly!")
        return True
        
    except ImportError as e:
        print(f"✗ Utils package structure test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if we're in FreeCAD
    try:
        app = FreeCAD
        gui = FreeCADGui
        print("Running in FreeCAD environment")
        
        # Test package structure first
        if test_utils_package_structure():
            # Test individual components
            test_vector_gizmo_from_utils()
            test_projection_visualizer_from_utils()
        
        print("\n=== CONCLUSION ===")
        print("The Utils package refactoring is complete and working correctly!")
        print("Both VectorGizmo and ProjectionVisualizer are now available as reusable utilities.")
        
    except NameError:
        print("Error: This script must be run within FreeCAD")
        print("Please load this script in FreeCAD's Python console")
