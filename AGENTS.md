# Agent Instructions for FitCtrl - FTMS Fitness Equipment Control

## Build/Lint/Test Commands
- **Install deps**: `uv sync`
- **Quality check** (CI): `just check` (ruff check + mypy, fails on issues)
- **Format/fix code**: `just lint` (ruff format + ruff check --fix)
- **Unit tests**: `uv run python -m pytest tests/unit/`
- **Single test**: `uv run python -m pytest tests/unit/test_basic.py::test_display -v`
- **Integration tests** (requires device): `uv run python -m pytest tests/integration/ -s`

## Code Style Guidelines
- **Imports**: Group stdlib, third-party, local with blank lines between. Ruff handles formatting.
- **Type hints**: Strict mode enforced. All function parameters/returns must have type hints (mypy: disallow_untyped_defs=true).
- **Docstrings**: Triple-quoted for all classes and public methods.
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants.
- **Async**: Use async/await consistently for BLE operations; mark async tests with @pytest.mark.asyncio.
- **Error handling**: Specific exceptions only. Log with standard logging module.
- **Formatting**: f-strings for interpolation, pathlib.Path for file operations, private methods use single underscore prefix.

## Project Context
CLI/REPL for WalkingPad R3 via FTMS protocol. Production-ready with full type safety (mypy strict), async BLE control, rich terminal UI, and comprehensive tests.
