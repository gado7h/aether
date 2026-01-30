import PyInstaller.__main__
from pathlib import Path
import shutil
import os

# Strategy: Create a temporary launcher script at the root
# that imports the package from the 'src' directory.
# This ensures PyInstaller correctly identifies 'aether'
# as a package and bundles it correctly.

SRC_DIR = Path("src")
LAUNCHER = Path("aether_launcher_temp.py")

# 1. Clean previous builds
for path in [Path("build"), Path("dist")]:
    if path.exists():
        shutil.rmtree(path)

# 2. Create the launcher script
print(f"Creating launcher at {LAUNCHER}...")
with open(LAUNCHER, "w") as f:
    f.write("import sys\n")
    f.write("import os\n")
    # Add _MEIPASS support for PyInstaller bundles
    f.write("if hasattr(sys, '_MEIPASS'):\n")
    f.write("    sys.path.insert(0, sys._MEIPASS)\n")
    f.write("from aether.cli import main\n")
    f.write("if __name__ == '__main__':\n")
    f.write("    main()\n")

try:
    print(f"Building executable...")
    
    # Platform-specific path separator
    separator = os.pathsep
    
    # Run PyInstaller
    PyInstaller.__main__.run([
        str(LAUNCHER),
        '--name=aether',
        '--onefile',
        '--clean',
        # Add 'src' to search path so it finds 'aether' package
        f'--paths={str(SRC_DIR.resolve())}', 
        '--hidden-import=aether',
        '--hidden-import=aether.cli',
        '--hidden-import=aether.config',
        '--hidden-import=aether.bundler',
        '--hidden-import=aether.runner',
        '--hidden-import=aether.utils',
        # Data: Include the vendor folder (path relative to the package)
        f'--add-data={str(SRC_DIR / "aether" / "vendor")}{separator}aether/vendor',
    ])

finally:
    # 3. Cleanup launcher
    if LAUNCHER.exists():
        LAUNCHER.unlink()

print("\nBuild complete. Executable is in dist/")
