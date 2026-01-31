import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from aether.runner import run_tests_batch
from aether.bundler import bundle_scripts, bundle_testez

# Mock Config
config = {
    "api_key": "FAKE_KEY",
    "universe_id": "123",
    "place_id": "456",
    "rojo_project": "default.project.json",
    "json": False
}

def verify():
    print("--- Verifying Batch Execution Logic ---")
    
    # Paths
    root = Path("testing_workspace/dummy_project")
    tests_dir = root / "tests"
    src_dir = root / "src"
    
    files = list(tests_dir.glob("*.spec.luau"))
    print(f"Found {len(files)} spec files: {[f.name for f in files]}")
    
    # Bundles
    # We strip bundle_scripts to simple mock or let it fail?
    # bundle_scripts depends on reading file system.
    # We can mock bundle_scripts fallback if needed.
    # Let's just mock the bundle content to save time.
    bundle = "-- MOCK BUNDLE CONTENT --"
    
    # Mock requests
    with patch("aether.runner.requests") as mock_req:
        # Mock Response
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"path": "task/id"}
        mock_req.post.return_value = mock_resp
        
        mock_status = MagicMock()
        mock_status.json.return_value = {
            "state": "COMPLETE",
            "output": {
                "results": [
                    {
                        "status": "Success",
                        "failures": [],
                        "results": [
                            {"name": "Math should add", "status": "Success"},
                            {"name": "Failing should fail", "status": "Failure", "errors": ["TaskScript:50: Expected 1 to equal 2"]}
                        ]
                    }
                ]
            }
        }
        mock_req.get.return_value = mock_status
        
        # Run
        print("Running batch...")
        result = run_tests_batch(files, bundle, tests_dir, config, timeout=5)
        
        print(f"\nResult Success: {result['success']}")
        print(f"Results Count: {len(result['results'])}")
        
        # Verify Payload
        args, kwargs = mock_req.post.call_args
        payload = kwargs['json']['script']
        
        print("\nChecking Payload Content:")
        if "Master Bootstrap" in payload:
            print("[PASS] Master Bootstrap found")
        else:
            print("[FAIL] Master Bootstrap MISSING")
            
        if 'SpecModule.Name = "math"' in payload:
            print("[PASS] math.spec.luau mounted")
        else:
            print("[FAIL] math.spec.luau MISSING")
            
        if 'SpecModule.Name = "failing"' in payload:
            print("[PASS] failing.spec.luau mounted")
        else:
            print("[FAIL] failing.spec.luau MISSING")
            
        if "local plan = TestPlanner.createPlan(modules" in payload:
             print("[PASS] Test Plan creation found")
             
        # Check source map accumulation
        # run_tests_batch takes source_map arg.
        # It should append new mappings.
        
    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify()
