# Aether

[![PyPI version](https://badge.fury.io/py/roblox-aether.svg)](https://badge.fury.io/py/roblox-aether)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Aether** is a minimalist, high-signal CLI tool for executing Luau tests directly on Roblox Cloud. Run tests from your local machine with instant feedback and a professional developer experience.

## ✨ Features

- **Minimalist UI**: Clean, high-signal output with semantic coloring and no visual noise.
- **Smart Watch Mode**: Automatically re-runs only relevant tests on file change.
- **Rojo Integration**: Seamlessly respects your project structure.
- **CI/CD Ready**: Built-in authentication support for GitHub Actions.
- **Developer Experience**: "Test Cards" layout, instant feedback, and clean tracebacks.

## 🚀 Quick Start

### Installation

```bash
pip install roblox-aether
# OR
rokit add gado7h/aether
```

### Usage

**1. Initialize:**
```bash
aether init
```

**2. Set API Key:**
```bash
aether set-api <YOUR_API_KEY>
```

**3. Run Tests:**
```bash
aether run
```

**4. Watch Mode:**
```bash
aether run --watch
```

## 🛠️ Configuration

Configure via `aether.toml`:
```toml
[runner]
timeout = 60
tests_folder = "tests"

[project]
rojo_project = "default.project.json"
```

## 💻 Environment

Tests run in a headless **Roblox Cloud** environment.
- **Relative Path Tracebacks**: Stack traces are automatically mapped to local source files.
- **Static Physics**: Physics simulation is paused; manually step if required.

## 🤝 Contributing

We welcome contributions! Open an issue or submit a PR on GitHub.

## 📄 License

MIT License.
