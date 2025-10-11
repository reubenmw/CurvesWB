# Vector Gizmo - Reusable 3D Arrow Direction Indicator

A reusable, well-documented 3D arrow gizmo for FreeCAD that provides visual feedback for vector direction input. Designed to be easily integrated into any FreeCAD tool that needs vector direction specification.

## Overview

The Vector Gizmo creates a 3D arrow in the FreeCAD viewport that:
- Shows vector direction visually in real-time
- Synchronizes bidirectionally with X/Y/Z input fields
- Provides callbacks for direction changes
- Supports customizable colors and scaling
- Includes framework for future 3D manipulation
- Follows FreeCAD coding conventions and best practices

## Quick Start

### Basic Usage

```python
from freecad.Curves.Utils.VectorGizmo import VectorGizmo

# Create a gizmo at origin pointing in +X direction
gizmo = VectorGizmo(
    position=FreeCAD.Vector(0, 0, 0),
    direction=FreeCAD.Vector(1, 0, 0),
    arrow_length=50.0,
    arrow_size=10.0,
    color=(0.0, 1.0, 1.0)  # Cyan
)

# Set up callback for direction changes
def on_direction_changed(new_direction):
    print(f"Direction changed to: {new_direction}")

gizmo.on_direction_changed.append(on_direction_changed)

# Update direction programmatically
gizmo.set_direction(FreeCAD.Vector(0, 1, 0))

# Clean up when done
gizmo.cleanup()
```

### UI Integration

```python
from freecad.Curves.Utils.VectorGizmo import VectorGizmo, VectorGizmoUI

# In your dialog class:
def __init__(self):
    # Create gizmo
    self.vector_gizmo = VectorGizmo(
        position=FreeCAD.Vector(0, 0, 0),
        direction=FreeCAD.Vector(1, 0, 0)
    )
    
    # Create UI integration helper
    self.vector_ui = VectorGizmoUI(
        gizmo=self.vector_gizmo,
        dialog=self,
        x_field=self.form.vectorXEdit,
        y_field=self.form.vectorYEdit,
        z_field=self.form.vectorZEdit,
        smart_default_enabled=True
    )

def cleanup(self):
    # Clean up both gizmo and UI helper
    if hasattr(self, 'vector_ui'):
        self.vector_ui.cleanup()
```

## Architecture

### Core Components

1. **VectorGizmo** - Main 3D arrow implementation
   - Coin3D scene graph management
   - Arrow rendering and positioning
   - Direction normalization and updates
   - Mouse interaction framework

2. **VectorGizmoUI** - UI integration helper
   - Bidirectional field synchronization
   - Smart default handling
   - Signal management and cleanup
   - Common UI patterns

### Scene Graph Structure

```
root (SoSeparator)
├─ switch (SoSwitch) - show/hide control
│   ├─ material (SoMaterial) - arrow color
│   ├─ base_transform (SoTransform) - position + rotation
│   ├─ shaft_separator (SoSeparator)
│   │   ├─ shaft_scale (SoScale) - shaft scaling
│   │   └─ shaft_cylinder (SoCylinder) - arrow shaft
│   └─ cone_separator (SoSeparator)
│       ├─ cone_transform (SoTransform) - cone positioning
│       ├─ cone_scale (SoScale) - cone scaling
│       ├─ cone_origin (SoTranslation) - cone origin offset
│       └─ cone (SoCone) - arrow head
└─ pick_separator (SoSeparator) - interaction elements
```

## API Reference

### VectorGizmo Class

#### Constructor

```python
VectorGizmo(position, direction, arrow_length=50.0, arrow_size=10.0, color=(0.0, 1.0, 1.0))
```

**Parameters:**
- `position` (FreeCAD.Vector): Base position of the arrow
- `direction` (FreeCAD.Vector): Initial direction (will be normalized)
- `arrow_length` (float): Length of arrow shaft in mm (default: 50.0)
- `arrow_size` (float): Size of arrow cone head in mm (default: 10.0)
- `color` (tuple): RGB color tuple (default: cyan)

#### Direction Methods

- `set_direction(direction)` - Set arrow direction (normalizes input)
- `get_direction()` - Get current direction as unit vector
- `get_tip_position()` - Get position of arrow tip

#### Position Methods

- `set_position(position)` - Set arrow base position
- `get_position()` - Get current base position

#### Scaling Methods

- `set_arrow_length(length)` - Set shaft length in mm
- `set_arrow_size(size)` - Set overall arrow size in mm

#### Color Methods

- `set_color(color)` - Set custom RGB color
- `set_color_normal()` - Set to normal color
- `set_color_hover()` - Set to hover color (yellow)
- `set_color_dragging()` - Set to dragging color (green)
- `set_color_invalid()` - Set to invalid color (red)

#### Visibility Methods

- `show()` - Show the arrow
- `hide()` - Hide the arrow
- `is_visible()` - Check if visible
- `toggle_visibility()` - Toggle visibility

#### Callbacks

- `on_direction_changed` - List of callback functions for direction changes

#### Cleanup

- `cleanup()` - Remove from scene and clean up resources

### VectorGizmoUI Class

#### Constructor

```python
VectorGizmoUI(gizmo, dialog, x_field, y_field, z_field, 
               smart_default_enabled=True, smart_default_callback=None)
```

**Parameters:**
- `gizmo` (VectorGizmo): The gizmo instance to integrate
- `dialog`: Parent dialog object
- `x_field`: Qt input field for X component
- `y_field`: Qt input field for Y component
- `z_field`: Qt input field for Z component
- `smart_default_enabled` (bool): Enable smart defaults
- `smart_default_callback` (callable): Custom default function

#### Vector Methods

- `get_vector()` - Get current vector from fields
- `set_vector(vector)` - Set both fields and gizmo
- `validate_fields()` - Validate field inputs

#### UI Control Methods

- `set_fields_enabled(enabled)` - Enable/disable input fields
- `clear_fields()` - Clear all field values
- `show_gizmo()` / `hide_gizmo()` - Control gizmo visibility
- `set_gizmo_position(position)` - Set gizmo position
- `set_gizmo_scaling()` - Set gizmo size parameters

#### Color Methods

- `set_gizmo_color(color)` - Set custom color
- `set_gizmo_normal/hover/dragging/invalid()` - Set color states

#### Cleanup

- `cleanup()` - Disconnect signals and clean up gizmo

## Standard UI Integration

### Required UI Elements

Your dialog should have input fields following this naming convention:
- `vectorXEdit` - X component input field
- `vectorYEdit` - Y component input field  
- `vectorZEdit` - Z component input field

### Integration Pattern

```python
class YourDialog:
    def __init__(self):
        # Create gizmo using utility function
        self.vector_gizmo, self.vector_ui = create_standard_vector_ui(
            self,
            gizmo_name="vector",
            smart_default_enabled=True,
            smart_default_callback=self._get_face_normal
        )
        
        # Initial setup
        if self.should_show_gizmo():
            self._setup_vector_gizmo()
    
    def _setup_vector_gizmo(self):
        """Configure gizmo for current context"""
        if self.some_condition:
            position = self._get_gizmo_position()
            self.vector_ui.set_gizmo_position(position)
            
            # Scale based on context
            arrow_length = self._calculate_arrow_length()
            arrow_size = arrow_length * 0.15
            self.vector_ui.set_gizmo_scaling(arrow_length, arrow_size)
            
            self.vector_ui.show_gizmo()
        else:
            self.vector_ui.hide_gizmo()
    
    def _get_face_normal(self):
        """Smart default callback"""
        if hasattr(self, 'logic') and self.logic.face_object:
            # Return face normal
            face_obj = self.logic.face_object[0]
            face_subname = self.logic.face_object[1]
            face_shape = face_obj.Shape.getElement(face_subname)
            u_mid = (face_shape.ParameterRange[0] + face_shape.ParameterRange[1]) / 2.0
            v_mid = (face_shape.ParameterRange[2] + face_shape.ParameterRange[3]) / 2.0
            return face_shape.normalAt(u_mid, v_mid)
        return FreeCAD.Vector(0, 0, 1)  # Default
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'vector_ui'):
            self.vector_ui.cleanup()
```

## Smart Default System

The gizmo includes intelligent handling of zero vectors (0, 0, 0):

1. **Automatic Detection**: When user enters (0, 0, 0) or leaves fields empty
2. **Context-Aware Defaults**: Uses face normal if available, falls back to Z-axis
3. **User Feedback**: Console messages indicate when smart defaults are applied
4. **Bidirectional Sync**: Fields are updated with the applied default

## Customization

### Colors

```python
# Set custom color
gizmo.set_color((1.0, 0.5, 0.0))  # Orange

# Use predefined color states
gizmo.set_color_normal()  # Default color
gizmo.set_color_hover()    # Yellow
gizmo.set_color_dragging() # Green
gizmo.set_color_invalid()  # Red
```

### Scaling

```python
# Size based on context
bbox = some_shape.BoundBox
face_diagonal = ((bbox.XLength**2 + bbox.YLength**2 + bbox.ZLength**2)**0.5)
arrow_length = face_diagonal * 0.3  # 30% of face size
arrow_size = arrow_length * 0.15     # 15% of length

gizmo.set_arrow_length(arrow_length)
gizmo.set_arrow_size(arrow_size)
```

### Positioning

```python
# Position at face centroid
position = face_shape.CenterOfMass
gizmo.set_position(position)

# Position at specific point
position = FreeCAD.Vector(x, y, z)
gizmo.set_position(position)
```

## Future Extensions

The gizmo includes framework for future enhancements:

### 3D Manipulation

```python
# Future: Enable 3D dragging
gizmo.enable_3d_manipulation()

# Future: Enable axis snapping
gizmo.set_snap_to_axis(enabled=True)
```

### Advanced Interaction

The mouse interaction framework is already in place for:
- Hover detection and highlighting
- 3D ray casting for drag operations
- Spherical projection for direction changes
- Visual feedback during manipulation

## Best Practices

### Performance

- Create gizmo once, reuse when possible
- Use `show()`/`hide()` instead of creating/destroying
- Always call `cleanup()` when done
- Scale gizmo appropriately for context

### Integration

- Use `VectorGizmoUI` for standard field integration
- Implement smart defaults for better UX
- Handle cleanup in dialog `cleanup()` method
- Validate inputs before processing

### Error Handling

- Always check vector length before setting
- Handle zero vectors with smart defaults
- Validate field inputs with `validate_fields()`
- Use try-catch blocks around gizmo operations

## Troubleshooting

### Common Issues

1. **Gizmo not visible**: Check that it's added to scene graph and not hidden
2. **Fields not updating**: Verify signal connections are properly set up
3. **Direction not changing**: Ensure vector is not zero-length
4. **Memory leaks**: Always call `cleanup()` when done

### Debug Tips

```python
# Check gizmo state
print(f"Visible: {gizmo.is_visible()}")
print(f"Direction: {gizmo.get_direction()}")
print(f"Position: {gizmo.get_position()}")

# Validate fields
is_valid, message = ui_helper.validate_fields()
print(f"Valid: {is_valid}, Message: {message}")

# Check current vector
current_vector = ui_helper.get_vector()
print(f"Current vector: {current_vector}")
```

## Examples

### Simple Direction Indicator

```python
# Create a simple direction indicator
indicator = VectorGizmo(
    position=FreeCAD.Vector(0, 0, 0),
    direction=FreeCAD.Vector(1, 0, 0),
    arrow_length=30.0,
    arrow_size=5.0,
    color=(1.0, 0.0, 0.0)  # Red
)

# Update based on some calculation
new_direction = calculate_direction()
indicator.set_direction(new_direction)

# Clean up later
indicator.cleanup()
```

### Context-Aware Gizmo

```python
class AdvancedTool:
    def __init__(self):
        # Create gizmo
        self.direction_gizmo = VectorGizmo(
            position=FreeCAD.Vector(0, 0, 0),
            direction=FreeCAD.Vector(0, 0, 1)
        )
        
        # Set up callback
        self.direction_gizmo.on_direction_changed.append(self.on_direction_change)
    
    def update_context(self, selected_object):
        """Update gizmo based on selected object"""
        if selected_object:
            # Position at object center
            bbox = selected_object.Shape.BoundBox
            center = FreeCAD.Vector(
                bbox.XMin + bbox.XLength/2,
                bbox.YMin + bbox.YLength/2,
                bbox.ZMin + bbox.ZLength/2
            )
            self.direction_gizmo.set_position(center)
            
            # Scale based on object size
            diagonal = ((bbox.XLength**2 + bbox.YLength**2 + bbox.ZLength**2)**0.5)
            self.direction_gizmo.set_arrow_length(diagonal * 0.2)
            
            self.direction_gizmo.show()
        else:
            self.direction_gizmo.hide()
    
    def on_direction_change(self, direction):
        """Handle direction changes"""
        # Update tool state
        self.current_direction = direction
        self.update_preview()
    
    def cleanup(self):
        """Clean up resources"""
        self.direction_gizmo.cleanup()
```

## License

LGPL 2.1 - See LICENSE file for details.

## Contributing

When contributing to the Vector Gizmo:
1. Follow FreeCAD coding conventions
2. Add comprehensive documentation
3. Include examples for new features
4. Test with multiple FreeCAD versions
5. Maintain backward compatibility

## Changelog

### v1.0.0
- Initial release
- Core 3D arrow functionality
- UI integration helper
- Smart default system
- Comprehensive documentation
- Framework for future 3D manipulation
