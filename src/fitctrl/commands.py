"""
Command definitions and auto-completion for REPL.

Defines all available commands with metadata and provides a completer
for prompt_toolkit auto-completion.
"""

from dataclasses import dataclass
from typing import Any, List

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


@dataclass
class Command:
    """Command definition with metadata."""

    name: str
    aliases: List[str]
    description: str
    usage: str
    handler: str


# Define all available commands
COMMANDS = [
    Command(
        name="connect",
        aliases=["c"],
        description="Connect to treadmill",
        usage="connect",
        handler="cmd_connect",
    ),
    Command(
        name="disconnect",
        aliases=["dc"],
        description="Disconnect from device",
        usage="disconnect",
        handler="cmd_disconnect",
    ),
    Command(
        name="start",
        aliases=["s"],
        description="Start or resume treadmill",
        usage="start",
        handler="cmd_start",
    ),
    Command(
        name="resume",
        aliases=["r"],
        description="Resume paused treadmill",
        usage="resume",
        handler="cmd_start",
    ),
    Command(
        name="stop",
        aliases=["x"],
        description="Stop treadmill",
        usage="stop",
        handler="cmd_stop",
    ),
    Command(
        name="pause",
        aliases=["p"],
        description="Pause treadmill",
        usage="pause",
        handler="cmd_pause",
    ),
    Command(
        name="speed",
        aliases=["sp"],
        description="Set target speed in km/h",
        usage="speed <km/h>",
        handler="cmd_speed",
    ),
    Command(
        name="status",
        aliases=["st"],
        description="Show current sensor values",
        usage="status",
        handler="cmd_status",
    ),
    Command(
        name="live",
        aliases=["l"],
        description="Toggle live display mode",
        usage="live",
        handler="cmd_live",
    ),
    Command(
        name="info",
        aliases=["i"],
        description="Show device and debug information",
        usage="info",
        handler="cmd_info",
    ),
    Command(
        name="help",
        aliases=["h", "?"],
        description="Show all available commands",
        usage="help",
        handler="cmd_help",
    ),
    Command(
        name="quit",
        aliases=["q", "exit"],
        description="Exit the REPL",
        usage="quit",
        handler="cmd_quit",
    ),
]


def get_command(name: str) -> Command | None:
    """Get command by name or alias.

    Args:
        name: Command name or alias

    Returns:
        Command object if found, None otherwise
    """
    for cmd in COMMANDS:
        if cmd.name == name or name in cmd.aliases:
            return cmd
    return None


class CommandCompleter(Completer):
    """Auto-completion for commands and arguments."""

    def __init__(self) -> None:
        """Initialize completer."""
        self._command_names = set()
        self._command_aliases = set()

        for cmd in COMMANDS:
            self._command_names.add(cmd.name)
            self._command_aliases.update(cmd.aliases)

    def get_completions(self, document: Document, complete_event) -> Any:  # type: ignore[no-untyped-def]
        """Get completion suggestions for current input.

        Args:
            document: Current input document
            complete_event: Completion event

        Yields:
            Completion objects for matching commands/arguments
        """
        text = document.text_before_cursor.lstrip()
        parts = text.split()

        # If no text yet, suggest nothing (avoid spam)
        if not text:
            return []

        # First part: complete command name
        if len(parts) <= 1:
            partial_cmd = parts[0].lower() if parts else ""
            all_names = self._command_names | self._command_aliases

            for name in sorted(all_names):
                if name.startswith(partial_cmd):
                    # Calculate completion (what needs to be added)
                    completion = name[len(partial_cmd) :]
                    yield Completion(
                        completion,
                        start_position=-len(partial_cmd),
                        display=f"({name})",
                    )

        # Second part: suggest speed values if command is "speed"
        elif len(parts) >= 2:
            first_cmd = parts[0].lower()
            if first_cmd in ("speed", "sp"):
                # Suggest speed values
                partial = parts[-1].lower() if parts[-1] else ""

                # Suggest common speeds: 1.0, 1.5, 2.0, ..., 12.0
                suggested_speeds = []
                speed = 1.0
                while speed <= 12.0:
                    suggested_speeds.append(f"{speed:.1f}")
                    speed += 0.5

                for speed_str in suggested_speeds:
                    if speed_str.startswith(partial):
                        completion = speed_str[len(partial) :]
                        yield Completion(
                            completion,
                            start_position=-len(partial),
                            display=speed_str,
                        )
