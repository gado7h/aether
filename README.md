# Roblox Test Runner

Execute Luau tests on Roblox Cloud with ease.

## Features

- ✅ Execute TestEZ tests on Roblox Cloud
- ✅ Watch mode for automatic re-running
- ✅ JSON output for CI/CD integration
- ✅ Customizable timeouts
- ✅ Clean, modular codebase

## Installation

### From Tooling Managers (Foreman, Aftman, Rokit)

Add this to your configuration file (e.g., `foreman.toml`, `aftman.toml`, `rokit.toml`):

```toml
[tools]
roblox-test-runner = { source = "gado7h/roblox-test-runner", version = "1.0.0" }
```

### As a Standalone Package

```bash
pip install roblox-test-runner
```

### From Source

```bash
git clone https://github.com/yourusername/roblox-test-runner.git
cd roblox-test-runner
pip install -e .
```

## Usage

### Configuration (Required)

You must configure your API credentials. You can do this via environment variables or the config command.

**Method 1: Interactive Config**
```bash
roblox-test-runner config
```

**Method 2: Environment Variables**
Create a `.env` file or set these variables:
```env
ROBLOX_API_KEY=your_api_key_here
UNIVERSE_ID=9635698060
PLACE_ID=131722995820694
```

Get your API key from [Roblox Creator Dashboard](https://create.roblox.com/credentials).

## Project Structure

The test runner expects the following structure:

```
your-project/
├── src/              # Luau source files
│   ├── shared/       → ReplicatedStorage
│   ├── server/       → ServerScriptService
│   └── client/       → StarterPlayer
├── Packages/         # Wally packages
├── tests/            # Test files (*.spec.luau)
└── .env              # API credentials
```

## CLI Reference

```
usage: roblox-test-runner [-h] [-l] [-v] [-j] [-w] [-t SECONDS] [test]

Options:
  -l, --list            List all available tests
  -v, --verbose         Show detailed output
  -j, --json            Output results as JSON
  -w, --watch           Watch for changes
  -t, --timeout SECONDS Custom timeout per test (default: 60)
```

## Development

```bash
# Install in development mode
cd tools
pip install -e .[dev]

# Run tests
pytest
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please open an issue or PR.
