# -*- coding: utf-8 -*-

__title__ = "Trim Face Object"
__license__ = "LGPL 2.1"
__doc__ = "FeaturePython object for trimmed faces"

import FreeCAD
import Part

try:
    import BOPTools.SplitAPI

    splitAPI = BOPTools.SplitAPI
except ImportError:
    FreeCAD.Console.PrintError("Failed importing BOPTools. Fallback to Part API\n")
    splitAPI = Part.BOPTools.SplitAPI

from . import debug


class TrimFaceObject:
    """FeaturePython proxy class for trimmed face objects"""

    def __init__(self, obj):
        """Add the properties"""
        debug("\nTrimFaceObject init")
        obj.addProperty("App::PropertyLinkSub", "Face", "TrimFace", "Input face")
        obj.addProperty(
            "App::PropertyVector",
            "PickedPoint",
            "TrimFace",
            "Picked point in parametric space of the face (u,v,0)",
        )
        obj.addProperty(
            "App::PropertyLinkSubList", "Tool", "TrimFace", "Trimming curve"
        )
        obj.addProperty("App::PropertyLink", "DirVector", "TrimFace", "Trimming Vector")
        obj.addProperty(
            "App::PropertyVector", "Direction", "TrimFace", "Trimming direction"
        )
        obj.Proxy = self

    def getFace(self, link):
        o = link[0]
        shapelist = link[1]
        for s in shapelist:
            if "Face" in s:
                n = eval(s.lstrip("Face"))
                debug("Face {}".format(n))
                return o.Shape.Faces[n - 1]
        return None

    def getEdges(self, sublinks):
        res = []
        for link in sublinks:
            o = link[0]
            shapelist = link[1]
            for s in shapelist:
                if "Edge" in s:
                    n = eval(s.lstrip("Edge"))
                    debug("Edge {}".format(n))
                    res.append(o.Shape.Edges[n - 1])
        return res

    def getVector(self, obj):
        if hasattr(obj, "DirVector"):
            if obj.DirVector:
                v = FreeCAD.Vector(obj.DirVector.Direction)
                debug("choosing DirVector : {}".format(str(v)))
                if v.Length > 1e-6:
                    return v
        if hasattr(obj, "Direction"):
            if obj.Direction:
                v = FreeCAD.Vector(obj.Direction)
                debug("choosing Direction : {}".format(str(v)))
                if v.Length > 1e-6:
                    return v
        debug("choosing (0,0,-1)")
        return FreeCAD.Vector(0, 0, -1)

    def execute(self, obj):
        debug("* trimFace execute *")
        if not obj.Tool:
            debug("No tool")
            return
        if not obj.PickedPoint:
            debug("No PickedPoint")
            return
        if not obj.Face:
            debug("No Face")
            return
        if not (obj.DirVector or obj.Direction):
            debug("No Direction")
            return

        face = self.getFace(obj.Face)
        v = self.getVector(obj)
        v.normalize()
        debug("Vector : {}".format(str(v)))
        wires = [Part.Wire(el) for el in Part.sortEdges(self.getEdges(obj.Tool))]
        union = Part.Compound(wires + [face])
        d = 2 * union.BoundBox.DiagonalLength
        cuttool = []
        for w in wires:
            w.translate(v * d)
            cuttool.append(w.extrude(-v * d * 2))
        # Part.show(cuttool)

        bf = splitAPI.slice(face, cuttool, "Split", 1e-6)
        debug("shape has {} faces".format(len(bf.Faces)))

        u = obj.PickedPoint.x
        v = obj.PickedPoint.y
        for f in bf.Faces:
            if f.isPartOfDomain(u, v):
                obj.Shape = f
                return
