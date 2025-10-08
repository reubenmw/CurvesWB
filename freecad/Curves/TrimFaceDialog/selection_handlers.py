# -*- coding: utf-8 -*-

__title__ = 'Trim face dialog - Selection handlers'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'Selection gates and observers for trim face dialog'


class SelectionGate:
    """Selection gate to control what user can select in 3D view"""
    def __init__(self, mode):
        self.mode = mode

    def allow(self, doc_name, obj_name, subname):
        if self.mode == 'edge':
            return 'Edge' in subname
        elif self.mode == 'face':
            return 'Face' in subname
        return False


class EdgeSelectionObserver:
    """Observer for edge selection events"""
    def __init__(self, parent):
        self.parent = parent

    def addSelection(self, doc_name, obj_name, sub_name, pos):
        import FreeCAD
        if 'Edge' in sub_name:
            obj = FreeCAD.ActiveDocument.getObject(obj_name)
            self.parent.on_edge_selected(obj, sub_name)


class FaceSelectionObserver:
    """Observer for face selection events"""
    def __init__(self, parent):
        self.parent = parent

    def addSelection(self, doc_name, obj_name, sub_name, pos):
        import FreeCAD
        if 'Face' in sub_name:
            obj = FreeCAD.ActiveDocument.getObject(obj_name)
            self.parent.on_face_selected(obj, sub_name)


class PointSelectionObserver:
    """Observer for point selection events"""
    def __init__(self, parent):
        self.parent = parent

    def addSelection(self, doc_name, obj_name, sub_name, pos):
        from PySide import QtCore
        QtCore.QTimer.singleShot(100, lambda: self.parent.check_picked_point())
