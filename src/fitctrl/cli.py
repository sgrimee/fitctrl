"""
Main REPL application for FTMS fitness equipment control.

Interactive command loop with async support, auto-completion,
and live sensor display.
"""

import argparse
import asyncio
import logging
import sys
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import InMemoryHistory
from pyftms import ResultCode

from .commands import COMMANDS, CommandCompleter, get_command
from .controller import TreadmillController
from .display import DisplayManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


class FitCtrlREPL:
    """Interactive REPL for FTMS fitness equipment control."""

    def __init__(self) -> None:
        """Initialize REPL with controller and display manager."""
        self.controller = TreadmillController()
        self.display = DisplayManager()
        self.running = False
        self.session: PromptSession

        # Set up callbacks
        self.controller.set_on_update(self._on_sensor_update)
        self.controller.set_on_disconnect(self._on_device_disconnect)

        # Create prompt session with auto-completion
        self.session = PromptSession(
            completer=CommandCompleter(),
            history=InMemoryHistory(),
            enable_history_search=True,
        )

        # Background update task
        self._update_task: Optional[asyncio.Task] = None

    async def run(self) -> None:
        """Run the main REPL loop."""
        self.running = True
        self.display.print_banner()

        # Auto-connect to device on startup
        self.display.console.print("Attempting to connect to FTMS device...")
        try:
            if await self.controller.connect():
                self.display.console.print("✓ Connected successfully\n")
            else:
                self.display.console.print(
                    "⚠ Could not connect to device. Use 'connect' command to retry.\n"
                )
        except Exception as e:
            self.display.console.print(f"⚠ Connection failed: {e}\n")

        # Start update processing loop
        self._update_task = asyncio.create_task(self._update_loop())

        try:
            while self.running:
                try:
                    # Get user input
                    prompt_text = self._get_prompt()
                    text = await self.session.prompt_async(prompt_text)

                    # Parse and execute command
                    if text.strip():
                        await self._handle_input(text.strip())

                except KeyboardInterrupt:
                    # Just show new prompt on Ctrl+C
                    self.display.console.print()
                    continue

        except EOFError:
            # End of input (Ctrl+D)
            await self.cmd_quit([])
        finally:
            self.running = False
            if self._update_task:
                self._update_task.cancel()
                try:
                    await self._update_task
                except asyncio.CancelledError:
                    pass

    def _get_prompt(self) -> FormattedText:
        """Get dynamic prompt based on connection state.

        Returns:
            FormattedText for prompt_toolkit
        """
        if self.controller.is_connected:
            device_name = (
                self.controller._client.name if self.controller._client else "Device"
            )
            return FormattedText([("class:prompt", f"[{device_name}] > ")])
        else:
            return FormattedText([("class:prompt", "[disconnected] > ")])

    async def _handle_input(self, text: str) -> None:
        """Parse and dispatch command.

        Args:
            text: Raw user input text
        """
        parts = text.split(maxsplit=1)
        if not parts:
            return

        cmd_name = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        # Find command
        cmd = get_command(cmd_name)
        if not cmd:
            self.display.print_error(
                f"Unknown command: {cmd_name}. Type 'help' for available commands."
            )
            return

        # Get handler method
        handler_name = cmd.handler
        if not hasattr(self, handler_name):
            self.display.print_error(f"Handler not found: {handler_name}")
            return

        handler = getattr(self, handler_name)

        # Execute command
        try:
            await handler(args)
        except Exception as e:
            self.display.print_error(f"Command failed: {e}")
            logger.exception("Command exception")

    async def _update_loop(self) -> None:
        """Background task to process sensor updates."""
        try:
            async for update_data in self.controller.get_updates():
                if self.display.live_enabled:
                    self.display.update_live(update_data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Update loop error: {e}")

    def _on_sensor_update(self, data: dict) -> None:
        """Callback when sensor data is received.

        Args:
            data: Sensor data dictionary
        """
        # Handled by async update loop
        pass

    def _on_device_disconnect(self) -> None:
        """Callback when device disconnects."""
        if self.display.live_enabled:
            self.display.stop_live()
        self.display.print_info("Device disconnected")

    # ========== Command Handlers ==========

    async def cmd_connect(self, args: list) -> None:
        """Connect to treadmill."""
        if self.controller.is_connected:
            self.display.print_info("Already connected")
            return

        self.display.print_info("Scanning for KS-AP-RQ3...")
        if not await self.controller.discover():
            self.display.print_error(
                "Device not found. Make sure it's powered on and in range."
            )
            return

        self.display.print_info("Connecting...")
        if not await self.controller.connect():
            self.display.print_error("Connection failed. Please try again.")
            return

        # Display device info
        info = self.controller.device_info
        if info:
            self.display.print_info(
                f"Connected to {info.get('device_name', 'Device')} "
                f"(Firmware: {info.get('firmware_revision', 'Unknown')})"
            )
        else:
            self.display.print_info("Connected!")

        # Show status
        await self.cmd_status([])

    async def cmd_disconnect(self, args: list) -> None:
        """Disconnect from device."""
        if not self.controller.is_connected:
            self.display.print_info("Not connected")
            return

        if self.display.live_enabled:
            self.display.stop_live()

        await self.controller.disconnect()
        self.display.print_info("Disconnected")

    async def cmd_start(self, args: list) -> None:
        """Start or resume treadmill."""
        if not self.controller.is_connected:
            self.display.print_error("Not connected. Use 'connect' first.")
            return

        result = await self.controller.start()
        self.display.print_result("start", result)

        if result == ResultCode.SUCCESS:
            # Wait for status update
            await asyncio.sleep(1)
            # Show status
            status = self.controller.get_status()
            self.display.print_info(f"Status: {status['status']}")

    async def cmd_stop(self, args: list) -> None:
        """Stop treadmill."""
        if not self.controller.is_connected:
            self.display.print_error("Not connected. Use 'connect' first.")
            return

        # If running, pause to stop the belt
        status = self.controller.get_status()
        if status.get("status") == "MANUAL_MODE":
            self.display.print_info("Pausing treadmill to stop...")
            pause_result = await self.controller.pause()
            if pause_result == ResultCode.SUCCESS:
                self.display.print_info("Treadmill stopped (paused)")
            else:
                self.display.print_result("pause", pause_result)
                return
        else:
            # Already paused/stopped - try the stop command
            self.display.print_info("Treadmill is already stopped")
            result = await self.controller.stop()
            if result == ResultCode.SUCCESS:
                self.display.print_info("Stop command completed")
            # Don't fail if stop command isn't supported when already stopped

    async def cmd_pause(self, args: list) -> None:
        """Pause treadmill."""
        if not self.controller.is_connected:
            self.display.print_error("Not connected. Use 'connect' first.")
            return

        result = await self.controller.pause()
        self.display.print_result("pause", result)

        if result == ResultCode.SUCCESS:
            # Wait for status update
            await asyncio.sleep(1)
            status = self.controller.get_status()
            self.display.print_info(f"Status: {status['status']}")

    async def cmd_speed(self, args: list) -> None:
        """Set target speed in km/h."""
        if not self.controller.is_connected:
            self.display.print_error("Not connected. Use 'connect' first.")
            return

        if not args:
            self.display.print_error("Usage: speed <km/h>")
            self.display.print_info(
                f"Range: {self.controller.SPEED_MIN}-{self.controller.SPEED_MAX} km/h"
            )
            return

        try:
            speed = float(args[0])
        except ValueError:
            self.display.print_error(f"Invalid speed: {args[0]}")
            return

        result = await self.controller.set_speed(speed)

        if result == ResultCode.SUCCESS:
            self.display.print_info(f"Speed set to {speed:.1f} km/h")
        elif result == ResultCode.INVALID_PARAMETER:
            self.display.print_error(
                f"Speed out of range. Must be {self.controller.SPEED_MIN}-{self.controller.SPEED_MAX} km/h"
            )
        else:
            self.display.print_result("set_speed", result)

    async def cmd_status(self, args: list) -> None:
        """Show current sensor values."""
        status = self.controller.get_status()
        self.display.print_status(status)

    async def cmd_live(self, args: list) -> None:
        """Toggle live display mode."""
        enabled = self.display.toggle_live()
        if enabled:
            # Need initial status for live display
            status = self.controller.get_status()
            self.display.update_live(status)
        else:
            self.display.print_info("Live display disabled")

    async def cmd_info(self, args: list) -> None:
        """Show device and debug information."""
        if not self.controller.is_connected:
            self.display.print_error("Not connected. Use 'connect' first.")
            return

        info = self.controller.device_info
        if not info:
            self.display.print_error("Could not retrieve device info")
            return

        self.display.console.print("[bold cyan]Device Information[/bold cyan]")
        for key, value in info.items():
            self.display.console.print(f"  {key}: {value}")

        self.display.console.print()
        self.display.console.print("[bold cyan]Speed Settings[/bold cyan]")
        self.display.console.print(
            f"  Range: {self.controller.SPEED_MIN}-{self.controller.SPEED_MAX} km/h"
        )
        self.display.console.print(f"  Step: {self.controller.SPEED_STEP} km/h")

        self.display.console.print()
        self.display.console.print("[bold cyan]Debug Information[/bold cyan]")
        self.display.console.print(f"  Connected: {self.controller.is_connected}")
        self.display.console.print(f"  Running: {self.controller._is_running}")
        self.display.console.print(f"  Live enabled: {self.display.live_enabled}")
        self.display.console.print(
            f"  Update queue size: {self.controller._update_queue.qsize()}"
        )
        self.display.console.print(f"  Live data: {self.display._live_data}")

        if self.controller.is_connected and self.controller._client:
            self.display.console.print(f"  Device name: {self.controller._client.name}")
            self.display.console.print(
                f"  Training status: {self.controller.training_status}"
            )
            self.display.console.print(f"  Speed: {self.controller.current_speed}")

    async def cmd_help(self, args: list) -> None:
        """Show all available commands."""
        self.display.print_help(COMMANDS)

    async def cmd_quit(self, args: list) -> None:
        """Exit the REPL."""
        if self.display.live_enabled:
            self.display.stop_live()

        if self.controller.is_connected:
            self.display.print_info("Disconnecting...")
            await self.controller.disconnect()

        self.display.console.print("[cyan]Goodbye![/cyan]")
        self.running = False


async def run_cli_command(command: str) -> None:
    """Run a single CLI command and exit."""
    controller = TreadmillController()
    display = DisplayManager()

    try:
        # Handle commands that don't need connection first
        if command == "clear-cache":
            controller.clear_address_cache()
            display.print_info("Cleared cached device address")
            return

        # Auto-connect if not connected
        if not controller.is_connected:
            display.print_info("Connecting to device...")
            if not await controller.connect():
                display.print_error("Failed to connect to device")
                sys.exit(1)

        if command == "start":
            result = await controller.start()
            display.print_result("start", result)

        elif command == "pause":
            result = await controller.pause()
            display.print_result("pause", result)

        elif command == "stop":
            # If running, pause to stop the belt
            status = controller.get_status()
            if status.get("status") == "MANUAL_MODE":
                display.print_info("Pausing treadmill to stop...")
                pause_result = await controller.pause()
                if pause_result == ResultCode.SUCCESS:
                    display.print_info("Treadmill stopped (paused)")
                else:
                    display.print_result("pause", pause_result)
                    sys.exit(1)
            else:
                # Already paused/stopped
                display.print_info("Treadmill is already stopped")

            # Try the stop command for completeness (may not be supported)
            result = await controller.stop()
            if result == ResultCode.SUCCESS:
                display.print_info("Stop command completed")
            # Don't fail if stop command isn't supported - pause is sufficient

        elif command == "status":
            # Wait a moment for sensor updates to arrive after connecting
            await asyncio.sleep(1)
            status = controller.get_status()
            display.print_status(status)

        else:
            display.print_error(f"Unknown command: {command}")
            sys.exit(1)

    finally:
        # Ensure we disconnect if still connected
        if controller.is_connected:
            try:
                await controller.disconnect()
            except Exception:
                pass


def main() -> None:
    """Entry point for the REPL application."""
    parser = argparse.ArgumentParser(
        description="FTMS Fitness Equipment Control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fitctrl                    # Start interactive REPL
  fitctrl --start           # Start treadmill (auto-connects)
  fitctrl --resume          # Resume paused treadmill
  fitctrl --pause           # Pause treadmill
  fitctrl --status          # Get device status (auto-connects)
  fitctrl --stop            # Stop treadmill (auto-connects, pauses if running)
  fitctrl --clear-cache     # Clear cached device address
        """,
    )

    parser.add_argument("--start", action="store_true", help="Start/resume treadmill")

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume paused treadmill (alias for --start)",
    )

    parser.add_argument("--pause", action="store_true", help="Pause treadmill")

    parser.add_argument("--stop", action="store_true", help="Stop treadmill")

    parser.add_argument("--status", action="store_true", help="Show device status")

    parser.add_argument(
        "--clear-cache", action="store_true", help="Clear cached device address"
    )

    args = parser.parse_args()

    # Check which command was requested
    commands = []
    if args.start or args.resume:
        commands.append("start")
    if args.pause:
        commands.append("pause")
    if args.stop:
        commands.append("stop")
    if args.status:
        commands.append("status")
    if args.clear_cache:
        commands.append("clear-cache")

    # If no CLI commands, start REPL
    if not commands:
        try:
            repl = FitCtrlREPL()
            asyncio.run(repl.run())
        except KeyboardInterrupt:
            print("\nInterrupted")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Run CLI commands
        if len(commands) > 1:
            print("Error: Only one command can be specified at a time", file=sys.stderr)
            sys.exit(1)

        try:
            asyncio.run(run_cli_command(commands[0]))
        except KeyboardInterrupt:
            print("\nInterrupted")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
