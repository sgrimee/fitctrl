#!/usr/bin/env python
"""Debug script to test live display update issue."""

import asyncio
import logging
import pytest
from fitctrl.controller import TreadmillController
from fitctrl.display import DisplayManager

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(message)s")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_display():
    """Test live display updates with real device."""
    controller = TreadmillController()
    display = DisplayManager()

    print("=== Testing Live Display ===")

    # Connect to device
    print("Connecting...")
    if not await controller.discover():
        pytest.skip("WalkingPad R3 device not found - skipping integration test")
        return

    if not await controller.connect():
        print("Connection failed")
        return

    print("Connected!")

    # Test initial status
    status = controller.get_status()
    print(f"Initial status: {status}")

    # Start live display
    print("Starting live display...")
    display.start_live()

    # Start update processing loop
    async def update_loop():
        try:
            async for update_data in controller.get_updates():
                if display.live_enabled:
                    display.update_live(update_data)
        except Exception as e:
            print(f"Update loop error: {e}")

    update_task = asyncio.create_task(update_loop())

    # Wait a bit
    await asyncio.sleep(2)

    # Start treadmill
    print("Starting treadmill...")
    result = await controller.start()
    print(f"Start result: {result}")

    # Wait for updates
    await asyncio.sleep(5)

    # Cancel update task
    update_task.cancel()
    try:
        await update_task
    except asyncio.CancelledError:
        pass

    # Show debug info
    print(f"Queue size: {controller._update_queue.qsize()}")
    print(f"Live data: {display._live_data}")

    # Stop live display
    display.stop_live()

    # Stop the treadmill to ensure clean test completion
    # Integration tests must leave devices in a safe state
    print("Pausing treadmill first...")
    pause_result = await controller.pause()
    print(f"Pause result: {pause_result}")

    print("Stopping treadmill...")
    stop_result = await controller.stop()
    print(f"Stop result: {stop_result}")

    # Disconnect
    await controller.disconnect()
    print("Disconnected")


if __name__ == "__main__":
    asyncio.run(test_live_display())
