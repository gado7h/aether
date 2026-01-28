# Roblox Test Runner

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Rokit](https://img.shields.io/badge/rokit-compatible-green.svg)](https://github.com/rojo-rbx/rokit)

**Next-generation test runner for Roblox.** Execute TestEZ test suites directly on Roblox Cloud with ease, locally or in CI/CD pipelines.

## ✨ Features

*   🚀 **Cloud Execution**: Run tests in a real Roblox environment via Open Cloud.
*   🔄 **Rojo Integration**: Seamlessly maps your project files using `sourcemap.json` or `default.project.json`.
*   ⚙️ **Flexible Configuration**: Use `roblox-test-runner.toml` (per-project or global) for easy setup.
*   👀 **Watch Mode**: Automatically re-run tests on file changes.
*   📊 **CI/CD Ready**: Supports JSON output for automated pipelines.

## 📦 Installation

### Using Rokit (Recommended)

Add to your `rokit.toml`:
```toml
[tools]
roblox-test-runner = "gado7h/roblox-test-runner@latest"
```

### From PyPI

```bash
pip install roblox-test-runner
```

## 🛠️ Configuration

Configuration is loaded hierarchically from:
1.  **CLI Arguments** (highest priority)
2.  **`roblox-test-runner.toml`** (current directory, then parent directories)
3.  **User Config** (`~/.config/roblox-test-runner/config.toml`)
4.  **Environment Variables**

### 1. set-api Command (Secure)
To store your API key securely in your user configuration:

```bash
roblox-test-runner set-api <YOUR_API_KEY>
```

### 2. Project Configuration (`roblox-test-runner.toml`)
Create this file in your project root to share settings with your team:

```toml
[runner]
timeout = 60            # Test timeout in seconds
watch_interval = 1.0    # Poll interval for watch mode (seconds)
tests_folder = "tests"  # Directory containing .spec.luau files

[project]
rojo_project = "default.project.json" # Path to your Rojo project file

[auth]
# Optional: Define Universe/Place IDs here
universe_id = "9635698060"
place_id = "131722995820694"
```

### 3. Environment Variables (CI/CD)
For GitHub Actions or other CI environments:
*   `ROBLOX_API_KEY`
*   `UNIVERSE_ID`
*   `PLACE_ID`

## 📂 Project Structure

The runner supports **any project structure** defined by your Rojo project (`default.project.json`).

By default, it looks for tests in the `tests/` folder. You can customize this in `roblox-test-runner.toml`.

**Example:**
```
my-game/
├── default.project.json  # Rojo project definition
├── roblox-test-runner.toml
├── src/
│   ├── modules/
│   └── server/
└── tests/
    └── player_data.spec.luau
```

## 🚀 Usage

### Run all tests
```bash
roblox-test-runner run
```

### Run specific test (fuzzy match)
```bash
roblox-test-runner run player
```

### Watch mode
```bash
roblox-test-runner run --watch
```

### CI/CD Output
```bash
roblox-test-runner run --json
```

## 🤝 Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
