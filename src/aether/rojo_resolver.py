"""
Aether - Rojo Sourcemap Resolver

Resolves file paths to Roblox instance paths using Rojo's sourcemap.
"""
import json
import subprocess
import shutil
from pathlib import Path

class RojoResolver:
    def __init__(self, project_file: str = "default.project.json"):
        self.project_file = Path(project_file)
        self.sourcemap = None
        self.mappings = {}  # {file_path: [instance_path_components]}

    def generate_sourcemap(self):
        """Generate sourcemap using rojo CLI or read existing sourcemap.json"""
        # 1. Prefer generating fresh from project file if it exists and rojo is installed
        if self.project_file.exists() and shutil.which("rojo"):
            try:
                result = subprocess.run(
                    ["rojo", "sourcemap", str(self.project_file)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.sourcemap = json.loads(result.stdout)
                self._build_mappings(self.sourcemap, [])
                return True
            except subprocess.CalledProcessError as e:
                print(f"[WARN] Failed to run rojo sourcemap: {e}")
        
        # 2. Fallback to existing sourcemap.json
        sourcemap_path = Path("sourcemap.json")
        if sourcemap_path.exists():
            try:
                with open(sourcemap_path, "r", encoding="utf-8") as f:
                    self.sourcemap = json.load(f)
                self._build_mappings(self.sourcemap, [])
                return True
            except Exception as e:
                print(f"[WARN] Failed to read sourcemap.json: {e}")
        
        return False

    def _build_mappings(self, node, current_path):
        """Recursively build file-to-path mappings"""
        # Handle file paths
        if "filePaths" in node:
            for file_path in node["filePaths"]:
                abs_path = Path(file_path).resolve()
                self.mappings[abs_path] = current_path
        
        # Handle children
        if "children" in node:
            for child in node["children"]:
                # The sourcemap structure for children is a list of node objects
                # Each node has "name", "className", "filePaths", "children"
                name = child["name"]
                self._build_mappings(child, current_path + [name])

    def get_roblox_path(self, file_path: Path):
        """Get Roblox path components for a file"""
        resolved_path = file_path.resolve()
        
        # Exact match
        if resolved_path in self.mappings:
            path = self.mappings[resolved_path]
            # Root services are usually correct, but let's ensure we return (Service, [Path])
            if not path:
                return None
            return path
            
        return None

    def get_all_scripts(self):
        """Get all scripts defined in the sourcemap"""
        # Used for bundling iteration
        return list(self.mappings.keys())
