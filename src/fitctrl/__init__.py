"""
FitCtrl - FTMS Fitness Equipment Control Library

A Python library for controlling FTMS-compatible fitness equipment via Bluetooth.
"""

__version__ = "0.1.0"
__author__ = "OpenCode"
__description__ = (
    "CLI and REPL interface for controlling FTMS-compatible fitness equipment"
)

from .controller import TreadmillController
from .display import DisplayManager

__all__ = ["TreadmillController", "DisplayManager"]
