# Agent Instructions for FitCtrl - FTMS Fitness Equipment Control

## Build/Lint/Test Commands
- **Install dependencies**: `uv sync`
- **Run code quality checks**: `just check` (fails on issues - for CI)
- **Run code formatting/fixing**: `just lint` (formats and auto-fixes)
- **Run unit tests**: `uv run python -m pytest tests/unit/`
- **Run integration tests**: `uv run python -m pytest tests/integration/`
- **Run single test**: `uv run python -m pytest tests/unit/test_basic.py::test_display -v`
- **Lint with ruff**: `uv run ruff check .`
- **Format with ruff**: `uv run ruff format .`

## Code Style Guidelines
- **Imports**: Group standard library, third-party, then local imports with blank lines between groups
- **Type hints**: Use typing module for all function parameters and return types
- **Async/await**: Use async patterns consistently for BLE operations
- **Docstrings**: Use triple-quoted docstrings for all classes and public methods
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Error handling**: Use try/except with specific exceptions, log errors appropriately
- **Path handling**: Use pathlib.Path instead of string paths
- **String formatting**: Use f-strings for dynamic strings
- **Logging**: Use standard logging module with appropriate levels
- **Private methods**: Prefix with single underscore (_method_name)
- **Testing**: Use pytest-asyncio for async tests, descriptive test function names

## Project Context
WalkingPad R3 control application using FTMS protocol. Fully implemented and production-ready with REPL interface, CLI commands, and comprehensive test suite. No Cursor or Copilot rules found.
