# Trim Face Dialog - Documentation Index

## 📚 **START HERE**

**👉 [AUTOMATIC_EXTENSION_COMPLETE.md](AUTOMATIC_EXTENSION_COMPLETE.md)** - Complete feature guide

**👉 [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)** - 28 test cases (includes multiple curves tests)

---

## 🎯 Key Features

- **✨ Automatic Curve Extension** - Detects short curves, extends automatically
- **🔢 Multiple Curves** - Select any number of edges (Ctrl/Shift)
- **📐 Projection-Based Detection** - Respects direction (no false positives)
- **🌳 Clean Hierarchy** - TrimmedFace → Extended → Original (all hidden by default)
- **🎨 Three Extension Modes** - None, Boundary (default), Custom distance
- **📍 Three Projection Modes** - Face Normal, View Direction, Custom Vector

## Usage

1. **Select Edges** (optional): Pre-select trimming curves before opening tool
2. **Open Tool**: Curves → Trim Face Dialog
3. **Add Curves**: Click edges (Ctrl/Shift for multiple)
4. **Select Face**: Click face to trim
5. **Pick Point**: Click point on face indicating which side to keep
6. **Apply**: Verify settings and click Apply

## Projection Direction Options

### Face Normal (Default)
Projects curve perpendicular to the surface at each point. Best for:
- Uniform surfaces
- Standard trimming operations
- When surface orientation is well-defined

### View Direction
Projects along current camera view angle. Best for:
- Visual-based trimming
- Matching what you see in viewport
- Artistic/presentation work

### Custom Vector
Projects along user-defined X, Y, Z vector. Best for:
- Engineering requirements (specific direction)
- Batch operations with consistent direction
- Advanced geometric constraints

## 🧪 Multiple Curves Testing

**YES - Multiple curves are fully tested!** See [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) Section 2:
- ✅ Test 2.1: Two short curves
- ✅ Test 2.2: Mixed lengths (one short, one long)
- ✅ Test 2.3: Three+ curves

**Quick verification:** Select 2+ edges with Ctrl+Click, all will be extended and nested properly.

---

## 📁 Files

### Core Code
- `trim_logic.py` - Extension algorithms, detection (~400 lines)
- `dialog_panel.py` - UI workflow, event handlers
- `selection_handlers.py` - Mouse/selection observers
- `command.py` - FreeCAD command registration
- `TrimFaceDialog.ui` - Qt Designer UI with extension controls
- `__init__.py` - Module exports

### Documentation
- **[AUTOMATIC_EXTENSION_COMPLETE.md](AUTOMATIC_EXTENSION_COMPLETE.md)** - Complete guide ⭐
- **[TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)** - 28 test cases
- **[UX_DESIGN.md](UX_DESIGN.md)** - Tree hierarchy design
- `README.md` - This file

## Technical Details

### Selection System
Uses FreeCAD's selection observers with custom gates for edge/face filtering. Modifier key detection enables fluid multi-select vs auto-advance behavior.

### Point Picking
Leverages `PickedPoints` system with 100ms QTimer delay for stable selection. Converts 3D picks to parametric UV coordinates via `Surface.parameter()`.

### Workflow States
- `edges`: Initial state, collecting trimming curves
- `face`: Selecting face to trim
- `point`: Picking trim side indicator point
- `complete`: Ready to apply operation

## Deployment

Run `deploy_to_freecad.ps1` to copy files to FreeCAD Mod directory. Requires FreeCAD restart to load changes.

## See Also

- Original implementation: `TrimFace.py`
- Future features: `FUTURE_FEATURES.md`
