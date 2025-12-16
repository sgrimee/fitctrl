#!/usr/bin/env python
"""Basic functionality test for REPL components without device."""

import asyncio
import pytest
from fitctrl.display import DisplayManager
from fitctrl.commands import COMMANDS, get_command, CommandCompleter
from pyftms import ResultCode


@pytest.mark.asyncio
async def test_display():
    """Test display functionality."""
    print("\n=== Testing Display Manager ===")
    display = DisplayManager()

    # Test banner
    print("\n1. Testing banner:")
    display.print_banner()

    # Test status display
    print("\n2. Testing status display:")
    test_status = {
        "status": "MANUAL_MODE",
        "speed": 4.5,
        "distance": 1240,
        "time": 125,
        "steps": 156,
        "calories": 12,
    }
    display.print_status(test_status)

    # Test command result
    print("\n3. Testing command results:")
    display.print_result("start", ResultCode.SUCCESS)
    display.print_result("pause", ResultCode.INVALID_PARAMETER)
    display.print_result("stop", ResultCode.FAILED)

    # Test messages
    print("\n4. Testing messages:")
    display.print_info("This is an info message")
    display.print_error("This is an error message")

    # Test formatting
    print("\n5. Testing format functions:")
    print(f"  Time 125s -> {display.format_time(125)}")
    print(f"  Speed 4.5 km/h -> {display.format_speed(4.5)}")
    print(f"  Distance 1240m -> {display.format_distance(1240)}")
    print(f"  Distance 2500m -> {display.format_distance(2500)}")
    print(f"  Energy 45 kcal -> {display.format_energy(45)}")

    # Test help
    print("\n6. Testing help display:")
    display.print_help(COMMANDS)


@pytest.mark.asyncio
async def test_commands():
    """Test command definitions."""
    print("\n=== Testing Commands ===")

    print(f"\n1. Total commands defined: {len(COMMANDS)}")

    print("\n2. Command lookup:")
    for cmd_str in ["connect", "c", "speed", "sp", "help", "h"]:
        cmd = get_command(cmd_str)
        if cmd:
            print(f"  '{cmd_str}' -> {cmd.name} ({cmd.description})")

    print("\n3. Command completer:")
    completer = CommandCompleter()
    print(f"  Completer initialized with {len(completer._command_names)} names")
    print(
        f"  Total completions available: {len(completer._command_names | completer._command_aliases)}"
    )


@pytest.mark.asyncio
async def test_controller_properties():
    """Test controller properties (without connection)."""
    print("\n=== Testing Controller (Disconnected) ===")
    from fitctrl.controller import TreadmillController

    controller = TreadmillController()

    print("\n1. Initial state:")
    print(f"  is_connected: {controller.is_connected}")
    print(f"  device_info: {controller.device_info}")
    print(f"  current_speed: {controller.current_speed}")
    print(f"  training_status: {controller.training_status}")

    print("\n2. Speed constraints:")
    print(f"  MIN: {controller.SPEED_MIN} km/h")
    print(f"  MAX: {controller.SPEED_MAX} km/h")
    print(f"  STEP: {controller.SPEED_STEP} km/h")

    print("\n3. Status when disconnected:")
    status = controller.get_status()
    print(f"  {status}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("WalkingPad R3 REPL - Basic Component Tests")
    print("=" * 60)

    try:
        await test_display()
        await test_commands()
        await test_controller_properties()

        print("\n" + "=" * 60)
        print("✓ All basic tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
