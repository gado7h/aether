# Roblox Test Runner

[![PyPI version](https://badge.fury.io/py/roblox-test-runner.svg)](https://badge.fury.io/py/roblox-test-runner)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Roblox Test Runner** is a powerful CLI tool designed to execute Luau tests (TestEZ) directly on Roblox Cloud. It allows you to run unit tests from your local machine and see the results instantly, integrating seamlessly into your development workflow.

## Features

- 🚀 **Run Tests on Cloud**: Execute tests in a live Roblox server environment.
- 📦 **Rojo Integration**: Automatically respects your `default.project.json` structure.
- ⚙️ **Configurable**: Use `roblox-test-runner.toml` to customize paths, timeouts, and more.
- 🔄 **Watch Mode**: Automatically re-run tests when files change (`-w`).
- 🤖 **CI/CD Ready**: Native support for GitHub Actions authentication.

## Installation

```bash
pip install roblox-test-runner
```

## Quick Start

1.  **Initialize Configuration**:
    ```bash
    roblox-test-runner init
    ```
    This creates a `roblox-test-runner.toml` file.

2.  **Set API Key** (for local development):
    ```bash
    roblox-test-runner set-api <YOUR_API_KEY>
    ```

3.  **Run Tests**:
    ```bash
    roblox-test-runner run
    ```
    or watch for changes:
    ```bash
    roblox-test-runner run --watch
    ```

## Usage

### Commands

- `run [test_name]`: Run tests. omit `test_name` to run all.
    - `-v, --verbose`: Show full logs.
    - `-w, --watch`: Watch mode.
    - `-j, --json`: JSON output.
- `init`: Create default configuration.
- `config`: View current configuration.
- `set-api <key>`: Save API key.
- `auth`: CI/CD authentication helper.

### Configuration (`roblox-test-runner.toml`)

```toml
[runner]
timeout = 60
tests_folder = "tests"

[project]
rojo_project = "default.project.json"
```

## Environment & Debugging

### Execution Environment
Tests run in a **Roblox Cloud** headless environment. This has some important limitations:
- **No Physics Simulation**: Gravity and physics stepping do not run automatically.
- **Headless**: No visual rendering.
- **Script Context**: Tests run inside a temporary script, often referred to as `TaskScript`.

### Debugging
The runner automatically maps stack traces from the bundled `TaskScript` back to your original source files (supported for `.luau` files managed by Rojo).
- If you see `TaskScript:123`, update to the latest version to see `src/my_script.server.luau:45`.
- Use `print()` debugging freely; logs are streamed back to your terminal.

### API Keys
API keys can be provided in three ways (checked in order):
1. **CLI Argument**: `roblox-test-runner run --key <KEY>` (mostly for CI)
2. **Environment Variable**: `ROBLOX_API_KEY`
3. **User Configuration**: Saved via `roblox-test-runner set-api <KEY>` (stored in your user home directory, not project)


## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
