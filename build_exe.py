import PyInstaller.__main__
from pathlib import Path

# Clean build artifacts (only build folder, leave dist for wheel integration)
import shutil
if Path("build").exists():
    shutil.rmtree("build")

# Define path to helper script
# We need a small entry script for PyInstaller
entry_point = Path("build_entry.py")
with open(entry_point, "w") as f:
    f.write("from roblox_test_runner.cli import main\n")
    f.write("if __name__ == '__main__':\n")
    f.write("    main()\n")

import os

# Run PyInstaller
separator = os.pathsep
PyInstaller.__main__.run([
    str(entry_point),
    '--name=roblox-test-runner',
    '--onefile',
    '--clean',
    '--paths=src',  # Tell PyInstaller where to look for modules
    '--hidden-import=roblox_test_runner',
    '--hidden-import=roblox_test_runner.cli',
    f'--add-data=src/vendor{separator}roblox_test_runner/vendor',  # Include vendored files
])

# Cleanup
entry_point.unlink()
print("\nBuild complete. Executable is in dist/")
