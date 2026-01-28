import PyInstaller.__main__
from pathlib import Path
import shutil
import os

# 1. Setup temporary build environment to mirror package structure
# This fixes "ModuleNotFoundError: No module named 'roblox_test_runner'"
# by creating a literal 'roblox_test_runner' folder containing src files.
TEMP_DIR = Path("temp_build_env")
PKG_DIR = TEMP_DIR / "roblox_test_runner"

# Clean previous build artifacts
if Path("build").exists(): shutil.rmtree("build")
if Path("dist").exists(): shutil.rmtree("dist")
if TEMP_DIR.exists(): shutil.rmtree(TEMP_DIR)

# Copy src contents to temp_build_env/roblox_test_runner
print(f"Creating temporary package structure in {PKG_DIR}...")
shutil.copytree("src", PKG_DIR)

# 2. Create Entry Point
entry_point = Path("build_entry.py")
with open(entry_point, "w") as f:
    f.write("from roblox_test_runner.cli import main\n")
    f.write("if __name__ == '__main__':\n")
    f.write("    main()\n")

# 3. Run PyInstaller
separator = os.pathsep
print("Running PyInstaller...")
try:
    PyInstaller.__main__.run([
        str(entry_point),
        '--name=roblox-test-runner',
        '--onefile',
        '--clean',
        # Add TEMP_DIR to python path so 'import roblox_test_runner' works
        f'--paths={str(TEMP_DIR)}', 
        # Force import of the package and cli
        '--hidden-import=roblox_test_runner',
        '--hidden-import=roblox_test_runner.cli',
        # Include vendor files. Source is in the temp pkg dir. Dest is inside package at runtime.
        f'--add-data={str(PKG_DIR / "vendor")}{separator}roblox_test_runner/vendor',
    ])
finally:
    # 4. Cleanup
    if entry_point.exists(): entry_point.unlink()
    if TEMP_DIR.exists(): shutil.rmtree(TEMP_DIR)

print("\nBuild complete. Executable is in dist/")
