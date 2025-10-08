# -*- coding: utf-8 -*-

__title__ = 'Trim face with dialog'
__author__ = 'Reuben Thomas'
__license__ = 'LGPL 2.1'
__doc__ = 'Trim a face with a projected curve using a fluid NX-style dialog'

# BACKWARD COMPATIBILITY WRAPPER
# This file maintains backward compatibility by re-exporting all components
# from the refactored module structure.

from .selection_handlers import (
    SelectionGate,
    EdgeSelectionObserver,
    FaceSelectionObserver,
    PointSelectionObserver
)
from .trim_logic import TrimFaceLogic
from .dialog_panel import TrimFaceDialogTaskPanel
from .command import TrimFaceDialogCommand, TOOL_ICON
from . import debug, DEBUG

__all__ = [
    'SelectionGate',
    'EdgeSelectionObserver',
    'FaceSelectionObserver',
    'PointSelectionObserver',
    'TrimFaceLogic',
    'TrimFaceDialogTaskPanel',
    'TrimFaceDialogCommand',
    'TOOL_ICON',
    'DEBUG',
    'debug'
]
