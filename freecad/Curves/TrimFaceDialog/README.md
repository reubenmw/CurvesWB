# Trim Face Dialog - Developer Overview

This document explains the files in the TrimFaceDialog tool root directory and their main functions for developers.

## Root Files Overview

```
TrimFaceDialog/
├── __init__.py                    # Module initialization and exports
├── command.py                     # FreeCAD command registration
├── coverage_checker.py            # Curve coverage detection algorithms
├── dialog_panel.py                # Main UI dialog and workflow management
├── selection_handlers.py          # User input and selection handling
├── trim_logic.py                  # Core trim operation logic
├── TrimFaceDialog.py              # Legacy entry point
├── TrimFaceDialog.ui              # Qt UI definition file
├── USER_GUIDE.md                  # Complete user documentation
├── README.md                      # This developer overview
├── Dev/                           # Development planning documents
└── Tests/                         # Testing documentation
```

## Core Files

### `__init__.py`
**Purpose**: Module initialization and exports
- Imports and exports main classes
- Provides clean public API
- Handles module-level setup

### `command.py`
**Purpose**: FreeCAD command registration and execution
- Registers the "Trim Face Dialog" command in FreeCAD GUI
- Creates and manages the dialog task panel
- Handles command lifecycle

### `trim_logic.py`
**Purpose**: Core business logic for trim operations
**Main Classes**:
- `TrimFaceLogic`: Central logic coordinator
**Key Functions**:
- Curve coverage detection
- Automatic curve extension
- Trim execution
- Extended curve creation and hierarchy management

### `dialog_panel.py`
**Purpose**: Main UI dialog and workflow management
**Main Classes**:
- `TrimFaceDialogTaskPanel`: NX-style dialog interface
**Key Functions**:
- Multi-stage workflow (edges → face → point → complete)
- Extension control visibility
- User interaction handling
- Settings management

### `coverage_checker.py`
**Purpose**: Advanced projection-based curve coverage detection
**Main Classes**:
- `CoverageChecker`: Detection algorithm implementation
**Key Functions**:
- Newton-Raphson projection solving
- UV parameter space calculations
- Projection mathematics
- Debug visualization overlay

### `selection_handlers.py`
**Purpose**: User input and selection handling
**Main Classes**:
- `EdgeSelectionObserver`: Edge selection events
- `FaceSelectionObserver`: Face selection events
**Key Functions**:
- Multi-selection support (Ctrl/Shift)
- Selection validation
- Workflow state transitions

### `vector_gizmo.py` (MOVED TO UTILS PACKAGE)
**Purpose**: Interactive 3D arrow gizmo for custom vector input (now available as reusable utility)
**Location**: `freecad.Curves.Utils.VectorGizmo.VectorGizmo`
**Key Functions**:
- Interactive 3D arrow visualization
- Mouse interaction and drag functionality
- Bidirectional sync with UI input fields
- State management (normal/hover/dragging)
**Usage**: Import from Utils package: `from freecad.Curves.Utils.VectorGizmo import VectorGizmo, VectorGizmoUI`

### `projection_visualizer.py` (MOVED TO UTILS PACKAGE)
**Purpose**: Debug visualization tools (now available as reusable utility)
**Location**: `freecad.Curves.Utils.CurveProjectionVisualizer.ProjectionVisualizer`
**Key Functions**:
- Coin3D overlay creation
- Projection direction visualization
- UV space debugging
- Visual feedback for algorithms
**Usage**: Import from Utils package: `from freecad.Curves.Utils.CurveProjectionVisualizer import ProjectionVisualizer`

### `TrimFaceDialog.py`
**Purpose**: Legacy entry point
- Maintains backward compatibility
- Delegates to new architecture

### `TrimFaceDialog.ui`
**Purpose**: Qt UI definition file
- Dialog layout and widgets
- UI element properties
- Form structure for Qt Designer

## Supporting Files

### `USER_GUIDE.md`
Complete user documentation including quick start, features, and troubleshooting.

### `Dev/`
Development planning documents including feature roadmap, implementation guides, and algorithm fixes.

### `Tests/`
Testing documentation and comprehensive test suites covering all functionality.

## Architecture Flow

1. **Entry Point**: `command.py` registers command and creates dialog
2. **UI Layer**: `dialog_panel.py` manages user interface and workflow
3. **Selection**: `selection_handlers.py` captures user inputs
4. **Detection**: `coverage_checker.py` analyzes curve coverage
5. **Logic**: `trim_logic.py` executes core operations
6. **Visualization**: `freecad.Curves.Utils.CurveProjectionVisualizer` provides debug feedback (reusable utility)

## Key Dependencies

- `freecad.Curves.TrimFace`: Core trim functionality
- `freecad.Curves.curveExtend`: Curve extension algorithms
- `freecad.Curves.Utils.VectorGizmo`: Reusable 3D arrow gizmo component
- `freecad.Curves.Utils.CurveProjectionVisualizer`: Reusable projection visualization component
- FreeCAD API: Object creation, geometry operations, UI integration
- Qt5: Dialog interface and widget management

## Utils Package Integration

The TrimFaceDialog now leverages reusable components from the `freecad.Curves.Utils` package:

### VectorGizmo
- **Import**: `from freecad.Curves.Utils.VectorGizmo import VectorGizmo, VectorGizmoUI`
- **Purpose**: Interactive 3D arrow for custom vector direction input
- **Features**: Bidirectional UI sync, smart defaults, proper cleanup

### CurveProjectionVisualizer
- **Import**: `from freecad.Curves.Utils.CurveProjectionVisualizer import ProjectionVisualizer`
- **Purpose**: Debug visualization of curve projection onto surfaces
- **Features**: Colored points, projection rays, UV direction indicators
- **UI Integration**: Toggle control in dialog for debugging workflows

These utilities can be reused by other tools in the Curves workbench, promoting code consistency and reducing duplication.
