"""
Display manager for Rich-based REPL output and live updates.

Handles all console output including formatted tables, status display,
and toggle-able live display updates.
"""

import logging
from typing import Any, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)


class DisplayManager:
    """Manages console output with Rich library."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize display manager.

        Args:
            console: Rich Console instance (creates one if None)
        """
        self.console = console or Console()
        self.live_enabled = False
        self._live: Optional[Live] = None
        self._live_data: dict[str, Any] = {}

    def print_banner(self) -> None:
        """Print startup banner."""
        panel = Panel(
            "[bold cyan]FitCtrl - FTMS Equipment Control[/bold cyan]\n"
            "[dim]Type 'help' for commands, 'quit' to exit[/dim]",
            expand=False,
        )
        self.console.print(panel)

    def print_status(self, data: dict) -> None:
        """Display one-time sensor status table.

        Args:
            data: Dictionary with status, speed, distance, time, steps, calories
        """
        table = self.format_status_table(data)
        self.console.print(table)

    def print_result(self, cmd: str, result) -> None:  # type: ignore[no-untyped-def]
        """Display command result.

        Args:
            cmd: Command name
            result: ResultCode enum
        """
        from pyftms import ResultCode

        if result == ResultCode.SUCCESS:
            self.console.print(f"[green]✓[/green] {cmd} succeeded", highlight=False)
        elif result == ResultCode.NOT_SUPPORTED:
            self.console.print(
                f"[yellow]⚠[/yellow] {cmd} not supported by device",
                highlight=False,
            )
        elif result == ResultCode.INVALID_PARAMETER:
            self.console.print(
                f"[red]✗[/red] {cmd} invalid parameter",
                highlight=False,
            )
        elif result == ResultCode.FAILED:
            self.console.print(f"[red]✗[/red] {cmd} failed", highlight=False)
        elif result == ResultCode.NOT_PERMITTED:
            self.console.print(
                f"[red]✗[/red] {cmd} not permitted",
                highlight=False,
            )
        else:
            self.console.print(
                f"[yellow]?[/yellow] {cmd} result: {result.name}", highlight=False
            )

    def print_error(self, message: str) -> None:
        """Print red error message.

        Args:
            message: Error message text
        """
        self.console.print(f"[red]Error:[/red] {message}", highlight=False)

    def print_info(self, message: str) -> None:
        """Print blue info message.

        Args:
            message: Info message text
        """
        self.console.print(f"[cyan]Info:[/cyan] {message}", highlight=False)

    def print_help(self, commands: list) -> None:
        """Display command reference.

        Args:
            commands: List of Command objects
        """
        table = Table(title="Available Commands", show_header=True)
        table.add_column("Command", style="cyan")
        table.add_column("Aliases", style="magenta")
        table.add_column("Description", style="white")
        table.add_column("Usage", style="yellow")

        for cmd in commands:
            aliases = ", ".join(cmd.aliases) if cmd.aliases else "-"
            table.add_row(cmd.name, aliases, cmd.description, cmd.usage)

        self.console.print(table)
        self.console.print(
            "[dim]Keyboard shortcuts: Ctrl+C to interrupt, Ctrl+D to exit[/dim]"
        )

    def start_live(self) -> None:
        """Start live display refresh mode."""
        if self.live_enabled:
            return

        self.live_enabled = True
        # Create initial renderable (will be updated)
        self._live_data = {
            "status": "Connecting...",
            "speed": 0.0,
            "distance": 0,
            "time": 0,
            "steps": 0,
            "calories": 0,
        }
        renderable = self._create_live_table()
        self._live = Live(renderable, console=self.console, refresh_per_second=2)
        self._live.start()
        self.console.print(
            "[dim]Live display enabled [Ctrl+L or 'live' to disable][/dim]"
        )

    def stop_live(self) -> None:
        """Stop live display refresh mode."""
        if not self.live_enabled:
            return

        self.live_enabled = False
        if self._live is not None:
            self._live.stop()
            self._live = None

    def update_live(self, data: dict) -> None:
        """Update live display with new sensor data.

        Args:
            data: UpdateEventData dict with sensor values
        """
        if not self.live_enabled or self._live is None:
            return

        # Normalize FTMS keys to match status command format
        normalized_data = {}
        for key, value in data.items():
            if key == "speed_instant":
                normalized_data["speed"] = value
            elif key == "distance_total":
                normalized_data["distance"] = value
            elif key == "time_elapsed":
                normalized_data["time"] = value
            elif key == "step_count":
                normalized_data["steps"] = value
            elif key == "energy_total":
                normalized_data["calories"] = value
            elif key == "training_status":
                # Convert training status enum to name
                normalized_data["status"] = (
                    value.name if hasattr(value, "name") else str(value)
                )
            else:
                normalized_data[key] = value

        # Update local cache with normalized values
        self._live_data.update(normalized_data)

        # Update the live display
        try:
            renderable = self._create_live_table()
            self._live.update(renderable)
        except Exception as e:
            logger.error(f"Live update error: {e}")

    def toggle_live(self) -> bool:
        """Toggle live display on/off.

        Returns:
            New live display state (True = on, False = off)
        """
        if self.live_enabled:
            self.stop_live()
        else:
            self.start_live()
        return self.live_enabled

    def _create_live_table(self) -> Table:
        """Create the live display table.

        Returns:
            Rich Table with current sensor data
        """
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Status", self._live_data.get("status", "UNKNOWN"))
        table.add_row("Speed", self.format_speed(self._live_data.get("speed", 0.0)))
        table.add_row(
            "Distance", self.format_distance(self._live_data.get("distance", 0))
        )
        table.add_row("Time", self.format_time(self._live_data.get("time", 0)))
        table.add_row("Steps", f"{self._live_data.get('steps', 0):,}")
        table.add_row(
            "Calories", self.format_energy(self._live_data.get("calories", 0))
        )

        return table

    def format_status_table(self, data: dict) -> Table:
        """Create Rich Table for sensor display.

        Args:
            data: Dictionary with status, speed, distance, time, steps, calories

        Returns:
            Rich Table object
        """
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Status", data.get("status", "UNKNOWN"))
        table.add_row("Speed", self.format_speed(data.get("speed", 0.0)))
        table.add_row("Distance", self.format_distance(data.get("distance", 0)))
        table.add_row("Time", self.format_time(data.get("time", 0)))
        table.add_row("Steps", f"{data.get('steps', 0):,}")
        table.add_row("Calories", self.format_energy(data.get("calories", 0)))

        return table

    @staticmethod
    def format_time(seconds: int) -> str:
        """Convert seconds to MM:SS format.

        Args:
            seconds: Number of seconds

        Returns:
            Formatted time string
        """
        if not isinstance(seconds, int):
            seconds = int(seconds)  # type: ignore[unreachable]
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"

    @staticmethod
    def format_speed(km_h: float) -> str:
        """Format speed value.

        Args:
            km_h: Speed in km/h

        Returns:
            Formatted speed string
        """
        return f"{km_h:.1f} km/h"

    @staticmethod
    def format_distance(meters: int) -> str:
        """Format distance value intelligently.

        Args:
            meters: Distance in meters

        Returns:
            Formatted distance (km if >1000m, otherwise m)
        """
        if meters >= 1000:
            km = meters / 1000
            return f"{km:.2f} km"
        return f"{meters} m"

    @staticmethod
    def format_energy(kcal: int) -> str:
        """Format energy value.

        Args:
            kcal: Energy in kilocalories

        Returns:
            Formatted energy string
        """
        return f"{kcal} kcal"
