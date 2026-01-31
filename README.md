# Aether

A powerful CLI tool designed to execute Luau tests (TestEZ) directly on Roblox Cloud. It allows you to run unit tests from your local machine and see the results instantly, integrating seamlessly into your development workflow.

## Features

- **Run Tests on Cloud**: Execute tests in a live Roblox server environment.
- **Rojo Integration**: Automatically respects your `default.project.json` structure.
- **Configurable**: Use `aether.toml` to customize paths, timeouts, and more.
- **Watch Mode**: Automatically re-run tests when files change (`-w`).
- **CI/CD Ready**: Native support for GitHub Actions authentication.
- **Run Failed**: Easily retry only failed tests with `--failed`.

## Installation

### Using pip

```bash
pip install roblox-aether
```

### Using rokit

You can also install Aether using Rokit:

```bash
rokit add gado7h/aether
```

## Quick Start

1. **Initialize Configuration**:
   ```bash
   aether init
   ```
   This creates a default configuration file.

2. **Set API Key**:
   You can store your API key locally:
   ```bash
   aether set-api <YOUR_API_KEY>
   ```

3. **Run Tests**:
   ```bash
   aether run
   ```

   To watch for file changes:
   ```bash
   aether run --watch
   ```

   To provide the API key directly (useful for scripts):
   ```bash
   aether run --api <YOUR_API_KEY>
   ```

## Usage

### Commands

- `aether run [test_name]`: Run tests. Omit `test_name` to run all.
    - `--watch` (`-w`): Watch for changes and re-run.
    - `--api <KEY>`: Provide API key directly.
    - `--failed`: Run only tests that failed previously.
    - `--json` (`-j`): Output results in JSON format.
    - `--verbose` (`-v`): Show full logs.
- `aether init`: Create default configuration.
- `aether config`: View current configuration.
- `aether set-api <KEY>`: Save API key to user configuration.

### Configuration

Aether uses `aether.toml` for configuration.

```toml
[runner]
timeout = 60
tests_folder = "tests"

[project]
rojo_project = "default.project.json"
```

## Environment & Debugging

Tests run in a **Roblox Cloud** headless environment. Physics simulation is not active by default. Output from `print()` is streamed back to your terminal. Stack traces are automatically mapped to your local source files.

## Examples

Check the [examples](examples/) directory for sample setups.
