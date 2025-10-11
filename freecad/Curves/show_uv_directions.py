# -*- coding: utf-8 -*-

__title__ = 'Show UV Directions - Quick Debug Tool'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'Simple tool to show UV directions on selected face'

import FreeCAD
import FreeCADGui
from pivy import coin


def show_uv_directions():
    """
    Show UV direction arrows on the selected face.

    Usage: Select a face, then run this from Macro > Macros or add to toolbar.
    """
    sel = FreeCADGui.Selection.getSelectionEx()

    if len(sel) == 0:
        FreeCAD.Console.PrintError("Please select a face first!\n")
        return

    # Find first face in selection
    face_obj = None
    face_sub = None

    for sel_obj in sel:
        for sub in sel_obj.SubElementNames:
            if sub.startswith("Face"):
                face_obj = sel_obj.Object
                face_sub = sub
                break
        if face_obj:
            break

    if not face_obj:
        FreeCAD.Console.PrintError("No face found in selection!\n")
        return

    try:
        face_shape = face_obj.Shape.getElement(face_sub)
        surf = face_shape.Surface

        # Get UV bounds
        face_u_min, face_u_max, face_v_min, face_v_max = face_shape.ParameterRange

        u_center = (face_u_min + face_u_max) / 2.0
        v_center = (face_v_min + face_v_max) / 2.0
        u_range = face_u_max - face_u_min
        v_range = face_v_max - face_v_min

        # Create visualization root
        vis_root = coin.SoSeparator()
        sg = FreeCADGui.ActiveDocument.ActiveView.getSceneGraph()
        sg.addChild(vis_root)

        # U direction arrow (Yellow)
        u_start = surf.value(u_center, v_center)
        u_end = surf.value(u_center + u_range * 0.3, v_center)

        u_arrow_sep = coin.SoSeparator()
        u_arrow_mat = coin.SoMaterial()
        u_arrow_mat.diffuseColor = (1, 1, 0)  # Yellow
        u_arrow_sep.addChild(u_arrow_mat)

        u_arrow_style = coin.SoDrawStyle()
        u_arrow_style.lineWidth = 8
        u_arrow_sep.addChild(u_arrow_style)

        u_arrow_coords = coin.SoCoordinate3()
        u_arrow_coords.point.setValues(0, 2, [(u_start.x, u_start.y, u_start.z), (u_end.x, u_end.y, u_end.z)])
        u_arrow_sep.addChild(u_arrow_coords)
        u_arrow_sep.addChild(coin.SoLineSet())
        vis_root.addChild(u_arrow_sep)

        # V direction arrow (Magenta)
        v_start = surf.value(u_center, v_center)
        v_end = surf.value(u_center, v_center + v_range * 0.3)

        v_arrow_sep = coin.SoSeparator()
        v_arrow_mat = coin.SoMaterial()
        v_arrow_mat.diffuseColor = (1, 0, 1)  # Magenta
        v_arrow_sep.addChild(v_arrow_mat)

        v_arrow_style = coin.SoDrawStyle()
        v_arrow_style.lineWidth = 8
        v_arrow_sep.addChild(v_arrow_style)

        v_arrow_coords = coin.SoCoordinate3()
        v_arrow_coords.point.setValues(0, 2, [(v_start.x, v_start.y, v_start.z), (v_end.x, v_end.y, v_end.z)])
        v_arrow_sep.addChild(v_arrow_coords)
        v_arrow_sep.addChild(coin.SoLineSet())
        vis_root.addChild(v_arrow_sep)

        # Add center point marker
        center_sep = coin.SoSeparator()
        center_mat = coin.SoMaterial()
        center_mat.diffuseColor = (1, 1, 1)  # White
        center_sep.addChild(center_mat)

        center_style = coin.SoDrawStyle()
        center_style.pointSize = 15
        center_sep.addChild(center_style)

        center_coords = coin.SoCoordinate3()
        center_coords.point.setValues(0, 1, [(u_start.x, u_start.y, u_start.z)])
        center_sep.addChild(center_coords)
        center_sep.addChild(coin.SoPointSet())
        vis_root.addChild(center_sep)

        FreeCAD.Console.PrintMessage("="*50 + "\n")
        FreeCAD.Console.PrintMessage(f"UV Directions for {face_obj.Name}.{face_sub}\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")
        FreeCAD.Console.PrintMessage(f"Face UV range: U=[{face_u_min:.4f}, {face_u_max:.4f}], V=[{face_v_min:.4f}, {face_v_max:.4f}]\n")
        FreeCAD.Console.PrintMessage("\nVisualization:\n")
        FreeCAD.Console.PrintMessage("  🟡 YELLOW arrow = U direction (increasing U)\n")
        FreeCAD.Console.PrintMessage("  🟣 MAGENTA arrow = V direction (increasing V)\n")
        FreeCAD.Console.PrintMessage("  ⚪ WHITE dot = Face center\n")
        FreeCAD.Console.PrintMessage("\n")
        FreeCAD.Console.PrintMessage("Your curve needs to extend further in the V direction!\n")
        FreeCAD.Console.PrintMessage("="*50 + "\n")

        FreeCADGui.activeDocument().activeView().viewAxonometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")

    except Exception as e:
        FreeCAD.Console.PrintError(f"Error: {e}\n")
        import traceback
        traceback.print_exc()


# Auto-run when macro is executed
if __name__ == "__main__":
    show_uv_directions()
