import PyInstaller.__main__
from pathlib import Path
import shutil
import os

# Strategy: Point PyInstaller directly to the main entry point 
# in the standard src/roblox_test_runner layout.

SRC_DIR = Path("src")
ENTRY_POINT = SRC_DIR / "roblox_test_runner" / "__main__.py"

# Clean previous
for path in [Path("build"), Path("dist")]:
    if path.exists():
        shutil.rmtree(path)

print(f"Building from {ENTRY_POINT}...")

# Run PyInstaller
separator = os.pathsep
PyInstaller.__main__.run([
    str(ENTRY_POINT),
    '--name=roblox-test-runner',
    '--onefile',
    '--clean',
    f'--paths={str(SRC_DIR.resolve())}', 
    '--hidden-import=roblox_test_runner',
    '--hidden-import=roblox_test_runner.cli',
    '--hidden-import=roblox_test_runner.config',
    '--hidden-import=roblox_test_runner.bundler',
    '--hidden-import=roblox_test_runner.runner',
    '--hidden-import=roblox_test_runner.utils',
    # Data: Include the vendor folder
    f'--add-data={str(SRC_DIR / "roblox_test_runner" / "vendor")}{separator}roblox_test_runner/vendor',
])

print("\nBuild complete. Executable is in dist/")
