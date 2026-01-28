import PyInstaller.__main__
from pathlib import Path
import shutil
import os

# Strategy: Create a clean "build_workspace" that looks like a standard python project
# build_workspace/
#   run_build.py
#   roblox_test_runner/  (copy of src)
#     __init__.py
#     cli.py
#     ...

WORKSPACE = Path("build_workspace")
PKG_DIR = WORKSPACE / "roblox_test_runner"

# 1. Clean previous
if Path("build").exists(): shutil.rmtree("build")
if Path("dist").exists(): shutil.rmtree("dist")
if WORKSPACE.exists(): shutil.rmtree(WORKSPACE)

# 2. Setup Workspace
WORKSPACE.mkdir()
print(f"Setting up workspace at {WORKSPACE}...")
shutil.copytree("src", PKG_DIR)

# 3. Create Entry Point inside workspace
entry_point = WORKSPACE / "run_build.py"
with open(entry_point, "w") as f:
    f.write("from roblox_test_runner.cli import main\n")
    f.write("if __name__ == '__main__':\n")
    f.write("    main()\n")

# 4. Run PyInstaller
# We point to the script INSIDE the workspace
# We add the workspace to paths so it finds 'roblox_test_runner' package
try:
    separator = os.pathsep
    PyInstaller.__main__.run([
        str(entry_point),
        '--name=roblox-test-runner',
        '--onefile',
        '--clean',
        f'--paths={str(WORKSPACE.resolve())}', 
        '--hidden-import=roblox_test_runner',
        '--hidden-import=roblox_test_runner.cli',
        # Data: Include the vendor folder from the workspace copy
        f'--add-data={str(PKG_DIR / "vendor")}{separator}roblox_test_runner/vendor',
    ])
finally:
    # Cleanup workspace
    if WORKSPACE.exists(): shutil.rmtree(WORKSPACE)

print("\nBuild complete. Executable is in dist/")
