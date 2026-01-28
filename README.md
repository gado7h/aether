# Roblox Test Runner

**About**

A simple tool to run your Roblox (TestEZ) tests in the cloud. It works with your Rojo project and lets you automate testing easily.

**Installation**

To install with [Rokit](https://github.com/rojo-rbx/rokit):

```toml
[tools]
roblox-test-runner = "gado7h/roblox-test-runner@latest"
```

Or with Pip:

```bash
pip install roblox-test-runner
```

**Commands**

*   `roblox-test-runner init` - Creates a default `roblox-test-runner.toml` config file.
*   `roblox-test-runner set-api <KEY>` - Securely saves your Roblox API key.
*   `roblox-test-runner run` - Runs all your tests in the `tests/` folder.
*   `roblox-test-runner run --watch` - Watches your files and re-runs tests on save.

**License**

MIT License.
