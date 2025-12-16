"""
Core constants and utilities for FTMS fitness equipment control.
"""

# FTMS (Fitness Machine Service) UUID for device discovery
FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"

# Speed constraints (device-dependent, WalkingPad R3 as reference)
SPEED_MIN = 1.0
SPEED_MAX = 12.0
SPEED_STEP = 0.1

# Application metadata
__version__ = "0.1.0"
__author__ = "OpenCode"
__description__ = (
    "CLI and REPL interface for controlling FTMS-compatible fitness equipment"
)
