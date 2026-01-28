import PyInstaller.__main__
from pathlib import Path
import shutil
import os

# Strategy: Create a temporary launcher script at the root
# that imports the package from the 'src' directory.
# This ensures PyInstaller correctly identifies 'roblox_test_runner'
# as a package and bundles it correctly.

SRC_DIR = Path("src")
LAUNCHER = Path("roblox_test_runner_launcher.py")

# 1. Clean previous builds
for path in [Path("build"), Path("dist")]:
    if path.exists():
        shutil.rmtree(path)

# 2. Create the launcher script
print(f"Creating launcher at {LAUNCHER}...")
with open(LAUNCHER, "w") as f:
    f.write("import sys\n")
    f.write("from roblox_test_runner.cli import main\n")
    f.write("if __name__ == '__main__':\n")
    f.write("    main()\n")

try:
    print(f"Building executable...")
    
    # Platform-specific path separator
    separator = os.pathsep
    
    # Run PyInstaller
    PyInstaller.__main__.run([
        str(LAUNCHER),
        '--name=roblox-test-runner',
        '--onefile',
        '--clean',
        # Add 'src' to search path so it finds 'roblox_test_runner' package
        f'--paths={str(SRC_DIR.resolve())}', 
        '--hidden-import=roblox_test_runner',
        '--hidden-import=roblox_test_runner.cli',
        '--hidden-import=roblox_test_runner.config',
        '--hidden-import=roblox_test_runner.bundler',
        '--hidden-import=roblox_test_runner.runner',
        '--hidden-import=roblox_test_runner.utils',
        # Data: Include the vendor folder (path relative to the package)
        f'--add-data={str(SRC_DIR / "roblox_test_runner" / "vendor")}{separator}roblox_test_runner/vendor',
    ])

finally:
    # 3. Cleanup launcher
    if LAUNCHER.exists():
        LAUNCHER.unlink()

print("\nBuild complete. Executable is in dist/")
