import PyInstaller.__main__
from pathlib import Path
import shutil
import os
import sys

# Strategy: Use a local directory named 'roblox_test_runner' to ensure 
# PyInstaller finds the package without complex path manipulation.

SRC_DIR = Path("src")
PKG_DIR = Path("roblox_test_runner")
ENTRY_POINT = Path("build_entry.py")

# 1. Clean previous
for path in [Path("build"), Path("dist"), PKG_DIR, ENTRY_POINT]:
    if path.exists():
        if path.is_file(): path.unlink()
        else: shutil.rmtree(path)

try:
    # 2. Setup Package structure
    # Copy src contents to roblox_test_runner/
    print(f"Setting up package structure at {PKG_DIR}...")
    shutil.copytree(SRC_DIR, PKG_DIR)

    # 3. Create Entry Point
    with open(ENTRY_POINT, "w") as f:
        f.write("from roblox_test_runner.cli import main\n")
        f.write("if __name__ == '__main__':\n")
        f.write("    main()\n")

    # 4. Run PyInstaller
    print("Running PyInstaller...")
    separator = os.pathsep
    PyInstaller.__main__.run([
        str(ENTRY_POINT),
        '--name=roblox-test-runner',
        '--onefile',
        '--clean',
        f'--paths=.', 
        '--hidden-import=roblox_test_runner',
        '--hidden-import=roblox_test_runner.cli',
        '--hidden-import=roblox_test_runner.config',
        '--hidden-import=roblox_test_runner.bundler',
        '--hidden-import=roblox_test_runner.runner',
        '--hidden-import=roblox_test_runner.utils',
        # Data: Include the vendor folder
        f'--add-data={str(PKG_DIR / "vendor")}{separator}roblox_test_runner/vendor',
    ])

finally:
    # 5. Cleanup
    print("Cleaning up...")
    if PKG_DIR.exists(): shutil.rmtree(PKG_DIR)
    if ENTRY_POINT.exists(): ENTRY_POINT.unlink()

print("\nBuild complete. Executable is in dist/")
