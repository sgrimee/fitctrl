# FitCtrl - FTMS Fitness Equipment Control Commands

# Default target - list available commands
default:
    just --list

# Run code quality checks (for CI - fails on issues)
check:
    uv run ruff check .
    uv run mypy src/

# Run code formatting and auto-fixing
lint:
    uv run ruff format .
    uv run ruff check --fix .

# Run unit tests (no device required)
test:
    uv run python -m pytest tests/unit/

# Run integration tests (requires device)
test-integration:
    uv run python -m pytest tests/integration/ -s

# Scan for BLE devices
scan:
    uv run python scan.py

# Start the treadmill (auto-connects)
start:
    uv run fitctrl --start

# Resume paused treadmill (auto-connects)
resume:
    uv run fitctrl --resume

# Pause the treadmill (auto-connects)
pause:
    uv run fitctrl --pause

# Stop the treadmill (auto-connects)
stop:
    uv run fitctrl --stop

# Get device status (auto-connects)
status:
    uv run fitctrl --status

# Show current training mode
mode-status:
    uv run fitctrl --mode status

# Attempt to switch to manual mode (may not be supported)
mode-manual:
    uv run fitctrl --mode manual

# Start interactive REPL
repl:
    uv run fitctrl

# Install/update dependencies
install:
    uv sync



# Clear cached device address
clear-cache:
    uv run fitctrl --clear-cache

# Clean up cache files
clean:
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type d -name "*.pyc" -delete
    rm -rf .pytest_cache/