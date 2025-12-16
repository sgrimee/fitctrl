# FitCtrl

```
███████╗██╗████████╗ ██████╗████████╗██████╗ ██╗
██╔════╝██║╚══██╔══╝██╔════╝╚══██╔══╝██╔══██╗██║
█████╗  ██║   ██║   ██║        ██║   ██████╔╝██║
██╔══╝  ██║   ██║   ██║        ██║   ██╔══██╗██║
██║     ██║   ██║   ╚██████╗   ██║   ██║  ██║███████╗
╚═╝     ╚═╝   ╚═╝    ╚═════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝
```

CLI and REPL interface for controlling FTMS-compatible fitness equipment (treadmills, ellipticals, etc.) via Bluetooth LE.

### Tested Devices

All FTMS control commands work correctly on the WalkingPad R3:

- **Start/Resume**: ✓ Works
- **Stop**: ✓ Works
- **Pause**: ✓ Works
- **Speed Control**: ✓ Works (1.0 - 12.0 km/h)

Other FTMS-compatible devices may work but have not been tested.

## Quick Start

### Setup

```bash
git clone https://github.com/sgrimee/fitctrl.git
cd fitctrl
uv sync
```

### Run the REPL

```bash
# Interactive REPL
uv run fitctrl

# Or CLI commands directly
uv run fitctrl --start    # Start treadmill
uv run fitctrl --status   # Show current status
uv run fitctrl --stop     # Stop treadmill
```

## Features

- **12 Core Commands**: connect, disconnect, start, resume, stop, pause, speed, status, live, info, help, quit
- **Live Display**: Real-time sensor updates (status, speed, distance, time, steps, calories)
- **Auto-Completion**: Command names, aliases, and speed suggestions
- **Device Info**: Show manufacturer, model, firmware, capabilities
- **Speed Control**: Set speed in 0.1 increments (device-dependent range)
- **Device Caching**: Automatic Bluetooth address caching for faster connections
- **Multi-Device Support**: Works with any FTMS-compatible fitness equipment

## Commands

| Command | Aliases | Description | Usage |
|---------|---------|-------------|-------|
| connect | c | Connect to treadmill | `connect` |
| disconnect | dc | Disconnect from device | `disconnect` |
| start | s | Start or resume treadmill | `start` |
| resume | r | Resume paused treadmill | `resume` |
| stop | x | Stop treadmill | `stop` |
| pause | p | Pause treadmill | `pause` |
| speed | sp | Set target speed | `speed <km/h>` |
| status | st | Show sensor values | `status` |
| live | l | Toggle live display | `live` |
| info | i | Show device and debug information | `info` |
| help | h, ? | Show all commands | `help` |
| quit | q, exit | Exit REPL | `quit` |

## Example Session

```
[disconnected] > connect
Scanning for FTMS devices...
Found: WalkingPad R3 (XX:XX:XX:XX:XX:XX)
Connecting...
✓ Connected to WalkingPad R3
  Firmware: V0.0.7
  Features: Speed, Distance, Time, Steps, Energy

[WalkingPad R3] > status
┏━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Metric   ┃ Value        ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Status   │ IDLE         │
│ Speed    │ 0.0 km/h     │
│ Distance │ 0 m          │
│ Time     │ 0:00         │
│ Steps    │ 0            │
│ Calories │ 0 kcal       │
└──────────┴──────────────┘

[WalkingPad R3] > start
✓ start succeeded
Status: MANUAL_MODE

[WalkingPad R3] > speed 3.5
✓ Speed set to 3.5 km/h

[WalkingPad R3] > live
Live display enabled [Ctrl+L or 'live' to disable]
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Metric   ┃ Value         ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Status   │ MANUAL_MODE   │
│ Speed    │ 3.5 km/h      │
│ Distance │ 124 m         │
│ Time     │ 00:45         │
│ Steps    │ 156           │
│ Calories │ 12 kcal       │
└──────────┴───────────────┘

[WalkingPad R3] > pause
✓ pause succeeded

[WalkingPad R3] > disconnect
✓ Disconnected

[disconnected] > quit
Goodbye!
```

## Quick Commands (using just)

The project includes a `justfile` with convenient commands:

```bash
just                    # List all commands
just test              # Run unit tests (no device required)
just test-integration  # Run integration tests (requires device)
just start             # Start treadmill
just resume            # Resume paused treadmill
just pause             # Pause treadmill
just status            # Get device status
just stop              # Stop treadmill (pauses if running)
just repl              # Start interactive REPL (auto-connects on startup)
just clean             # Clean up cache files
```

## Device Address Caching

The CLI automatically caches the device Bluetooth address after the first successful connection. Subsequent commands will try the cached address first (much faster) before falling back to scanning if the cached address fails.

- **Cache location**: `~/.cache/fitctrl/device_address.json` (follows XDG Base Directory spec)
- **Clear cache**: `fitctrl --clear-cache` or `just clear-cache`
- **Benefits**: ~6x faster connection after initial discovery

## Testing

Run unit tests (no device required):

```bash
# Using just (recommended)
just test

# Or directly with pytest
uv run python -m pytest tests/unit/
```

Run integration tests (requires device):

```bash
# Using just (recommended)
just test-integration

# Or directly with pytest
uv run python -m pytest tests/integration/
```

## Troubleshooting

### Device Not Found

1. Ensure your FTMS-compatible device is powered on
1. Device is in Bluetooth range
1. Try `connect` again
1. Check Bluetooth on your computer
1. Ensure the device is not already connected to another Bluetooth application

## References

- **FTMS Specification**: https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0/
- **python-pyftms**: https://github.com/dudanov/python-pyftms
- **pyftms (PyPI)**: https://pypi.org/project/pyftms/
- **hassio-ftms**: https://github.com/dudanov/hassio-ftms
- **WalkingPad reverse-engineering**: https://github.com/ph4r05/ph4-walkingpad
- **darnfish/walkingpad**: https://github.com/darnfish/walkingpad
