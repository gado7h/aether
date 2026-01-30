"""
Aether - Configuration and utilities
"""
from pathlib import Path


DEFAULT_TIMEOUT = 60  # seconds per test


# Project paths (relative to where the package is run from)
def get_project_paths():
    """Get project paths relative to current working directory"""
    root = Path.cwd()
    return {
        "root": root,
        "src": root / "src",
        "packages": root / "Packages",
        "tests": root / "tests"
    }
