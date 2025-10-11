# Clean Hierarchy System - User Tests

## Test Overview
This document provides manual testing instructions for the Clean Hierarchy System feature in the TrimFaceDialog.

## Test Setup

### Prerequisites
1. FreeCAD with CurvesWB addon installed
2. A test document with:
   - A face to trim (e.g., a rectangular face)
   - One or more curves that can be used for trimming
   - Curves that are shorter than the face (to trigger extension)

### Test Cases

### Test Case 1: Basic Hierarchy Creation (No Extension)
**Objective**: Verify simple hierarchy when no extension is needed

**Steps**:
1. Create a rectangular face (e.g., 100x50mm)
2. Create a curve that spans the full width of the face
3. Open TrimFaceDialog
4. Select the face and curve
5. Set extension mode to 'none'
6. Execute the trim operation

**Expected Results**:
- TrimmedFace object is created and visible
- Original curve is nested under TrimmedFace (2-level hierarchy)
- Original curve is hidden by default
- Can expand TrimmedFace in tree view to see the original curve
- Original curve can be made visible by toggling visibility

### Test Case 2: Extended Curve Hierarchy Creation
**Objective**: Verify three-level hierarchy when extension is used

**Steps**:
1. Create a rectangular face (e.g., 100x50mm)
2. Create a short curve (e.g., 30mm) that needs extension
3. Open TrimFaceDialog
4. Select the face and curve
5. Set extension mode to 'boundary'
6. Execute the trim operation

**Expected Results**:
- TrimmedFace object is created and visible (level 1)
- Extended curve object is created and nested under TrimmedFace (level 2)
- Extended curve has purple color (0.8, 0.2, 0.8) and LineWidth=2.0
- Extended curve is hidden by default
- Original curve is nested under extended curve (level 3)
- Original curve is hidden by default
- Three-level hierarchy: TrimmedFace → Extended → Original

### Test Case 3: Multiple Curves Hierarchy
**Objective**: Verify hierarchy with multiple trimming curves

**Steps**:
1. Create a rectangular face (e.g., 100x50mm)
2. Create 2-3 short curves that need extension
3. Open TrimFaceDialog
4. Select the face and all curves
5. Set extension mode to 'boundary'
6. Execute the trim operation

**Expected Results**:
- TrimmedFace object is created and visible
- Multiple extended curve objects are nested under TrimmedFace
- Each extended curve has its corresponding original curve nested
- All extended curves have purple styling
- All curves are hidden by default
- Can expand/collapse hierarchy levels independently

### Test Case 4: Custom Extension Distance
**Objective**: Verify hierarchy with custom extension distance

**Steps**:
1. Create a rectangular face (e.g., 100x50mm)
2. Create a short curve
3. Open TrimFaceDialog
4. Select the face and curve
5. Set extension mode to 'custom'
6. Set custom distance (e.g., 20mm)
7. Execute the trim operation

**Expected Results**:
- Same hierarchy structure as Test Case 2
- Extended curve length reflects custom distance
- Purple styling applied to extended curve
- Proper nesting maintained

### Test Case 5: Visibility Management
**Objective**: Test visibility toggling through hierarchy

**Steps**:
1. Create a trim operation with extension (as in Test Case 2)
2. In the tree view, expand the TrimmedFace object
3. Toggle visibility of the extended curve
4. Expand the extended curve
5. Toggle visibility of the original curve
6. Toggle visibility of the TrimmedFace

**Expected Results**:
- Can independently control visibility of each hierarchy level
- Toggling parent visibility affects all children
- Toggling child visibility doesn't affect parent
- Visibility changes persist in the tree view

### Test Case 6: Delete Cascade
**Objective**: Test proper cleanup when deleting objects

**Steps**:
1. Create a trim operation with extension
2. Delete the TrimmedFace object
3. Verify cleanup
4. Repeat test, but delete an extended curve instead
5. Verify cleanup

**Expected Results**:
- Deleting TrimmedFace removes entire hierarchy
- No orphaned objects remain
- Deleting extended curve removes its nested original
- Document remains clean without broken references

### Test Case 7: Error Handling
**Objective**: Test behavior with invalid inputs

**Steps**:
1. Try to trim with invalid curve selection
2. Try to trim with no face selected
3. Try to trim with curve that cannot be extended
4. Verify error messages and fallback behavior

**Expected Results**:
- Clear error messages for invalid inputs
- Graceful fallback to original curves when extension fails
- No orphaned objects created during error conditions
- Document remains stable

## Success Criteria

### Functional Requirements
- [ ] TrimmedFace object is visible by default (level 1)
- [ ] Extended curves are hidden by default (level 2)
- [ ] Original curves are hidden by default (level 3)
- [ ] Hierarchy structure is logical and intuitive
- [ ] Objects can be made visible for inspection
- [ ] Delete cascade works properly
- [ ] Extended curves have distinct visual styling

### Visual Design
- [ ] Extended curves have purple color (0.8, 0.2, 0.8)
- [ ] Extended curves have LineWidth=2.0
- [ ] Original curves maintain their original styling
- [ ] TrimmedFace uses standard FreeCAD styling

### User Experience
- [ ] Clean default view (only TrimmedFace visible)
- [ ] Progressive disclosure (expand to see details)
- [ ] Intuitive tree view navigation
- [ ] Clear object naming (e.g., "Curve_Extended")
- [ ] Proper error messages and feedback

## Test Results

### Test Case 1: Basic Hierarchy Creation
- Status: [ ] Pass / [ ] Fail
- Notes: _________________________________

### Test Case 2: Extended Curve Hierarchy Creation
- Status: [ ] Pass / [ ] Fail
- Notes: _________________________________

### Test Case 3: Multiple Curves Hierarchy
- Status: [ ] Pass / [ ] Fail
- Notes: _________________________________

### Test Case 4: Custom Extension Distance
- Status: [ ] Pass / [ ] Fail
- Notes: _________________________________

### Test Case 5: Visibility Management
- Status: [ ] Pass / [ ] Fail
- Notes: _________________________________

### Test Case 6: Delete Cascade
- Status: [ ] Pass / [ ] Fail
- Notes: _________________________________

### Test Case 7: Error Handling
- Status: [ ] Pass / [ ] Fail
- Notes: _________________________________

## Overall Assessment
- Feature Status: [ ] Complete / [ ] Needs Work / [ ] Failed
- Critical Issues: _________________________________
- Minor Issues: _________________________________
- Recommendations: _________________________________
