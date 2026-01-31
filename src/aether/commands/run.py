"""
Aether run command - Professional Watch Mode
"""
import time
import os
import sys
from pathlib import Path
from ..config import get_config, validate_config
from ..bundler import bundle_scripts, bundle_testez
from ..runner import run_test_suite, run_tests_batch
from ..utils import get_project_paths
from ..ui import Dashboard, get_key_press

def command(args):
    """Handle run command"""
    
    config = get_config()
    
    if args.timeout:
        config["timeout"] = args.timeout
    
    missing = validate_config(config)
    
    if missing:
        print("[ERROR] Missing configuration:")
        for m in missing:
            print(f"  - {m}")
        print("\nRun 'roblox-test-runner set-api <KEY>' or set environment variables.")
        return 1
    
    paths = get_project_paths()
    
    if config.get("tests_folder"):
        custom_tests = paths["root"] / config["tests_folder"]
        if custom_tests.exists():
            paths["tests"] = custom_tests
        else:
             print(f"[ERROR] Configured tests path not found: {custom_tests}")
             return 1
    
    tests_dir = paths["tests"]
    
    files = list(tests_dir.glob("*.spec.luau"))
    files = [f for f in files if not f.name.startswith("_")]
    
    if not files:
        print(f"[WARN] No .spec.luau files found in {tests_dir}")
        return 0
    
    if args.list:
        print("Available tests:")
        for f in sorted(files):
            print(f"  - {f.stem}")
        return 0
    
    # Watch mode
    if args.watch:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            print("[ERROR] Watch mode requires 'watchdog' package.")
            print("Install with: pip install watchdog")
            return 1
        
        dashboard = Dashboard()
        dashboard.rojo_project = config.get("rojo_project", "default.project.json")
        
        # State for debounce, smart detection, and commands
        watch_state = {
            "last_change_time": 0,
            "changed_path": None,
            "trigger_run": False,
            "run_mode": "all",  # "all", "failed", or "single"
            "last_results": None,
            "failed_files": set()
        }
        
        class ChangeHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.is_directory:
                    return
                if event.src_path.endswith(('.luau', '.lua', '.toml', '.json')):
                    watch_state["last_change_time"] = time.time()
                    watch_state["changed_path"] = event.src_path
                    watch_state["trigger_run"] = True
                    watch_state["run_mode"] = "smart"  # Will be determined by path
        
        def run_tests_with_dashboard(mode="all", specific_file=None):
            """Run tests with professional dashboard output"""
            files_to_run = list(tests_dir.glob("*.spec.luau"))
            files_to_run = [f for f in files_to_run if not f.name.startswith("_")]
            
            batch_mode = True
            
            # Determine which files to run
            if mode == "failed" and watch_state["failed_files"]:
                files_to_run = [f for f in files_to_run if f.stem in watch_state["failed_files"]]
                if not files_to_run:
                    mode = "all"
                    files_to_run = list(tests_dir.glob("*.spec.luau"))
                    files_to_run = [f for f in files_to_run if not f.name.startswith("_")]
            elif mode == "smart" and specific_file:
                p = Path(specific_file)
                if p.name.endswith(".spec.luau") and p.parent.resolve() == tests_dir.resolve():
                    matches = [f for f in files_to_run if f.resolve() == p.resolve()]
                    if matches:
                        files_to_run = matches
                        batch_mode = False
            elif mode == "single" and specific_file:
                p = Path(specific_file)
                matches = [f for f in files_to_run if f.resolve() == p.resolve()]
                if matches:
                    files_to_run = matches
                    batch_mode = False
            
            # Show running status
            dashboard.clear()
            dashboard.print_header()
            
            if batch_mode:
                file_display = f"{len(files_to_run)} test file(s)"
            else:
                file_display = files_to_run[0].name if files_to_run else "tests"
                
            dashboard.print_running(file_display)
            print()
            
            # Start spinner
            dashboard.start_spinner(file_display)
            
            try:
                # Build bundle
                testez_bundle = bundle_testez()
                scripts_bundle, source_map = bundle_scripts(paths, config)
                
                offset = testez_bundle.count('\n') + 1
                for mapping in source_map:
                    mapping["start"] += offset
                    mapping["end"] += offset
                
                bundle = testez_bundle + "\n" + scripts_bundle
                
                # Create a mock args object for the runner
                class MockArgs:
                    def __init__(self):
                        self.json = False
                        self.verbose = args.verbose
                        self.timeout = args.timeout
                        self.test = "all"
                        self.failed = False
                
                mock_args = MockArgs()
                config["json"] = False
                
                # Stop spinner before showing results
                dashboard.stop_spinner()
                
                # Clear and show results
                dashboard.clear()
                dashboard.print_header()
                
                # Run tests and collect results
                from ..runner import run_tests_batch as batch_runner, run_test as single_runner
                from ..utils import DEFAULT_TIMEOUT
                
                to = args.timeout or config.get("timeout") or DEFAULT_TIMEOUT
                
                start_time = time.time()
                all_results = []
                files_passed = 0
                files_failed = 0
                
                if batch_mode and len(files_to_run) > 1:
                    run_output = batch_runner(
                        files_to_run, bundle, tests_dir, config,
                        timeout=to, verbose=args.verbose, source_map=source_map
                    )
                    all_results = run_output.get("results", [])
                    duration = run_output.get("duration", 0)
                    
                    # For batch mode, show individual test results (not file-level)
                    # Since tests are flat, we display them directly
                    print()  # Add spacing after header
                    
                    for r in all_results:
                        name = r.get("name", "Unknown")
                        status = r.get("status", "FAILED")
                        
                        if status == "PASSED":
                            dashboard.print_result(name, "PASS", duration / max(len(all_results), 1))
                        elif status == "FAILED":
                            error = r.get("error", "")
                            traceback = r.get("traceback", "")
                            dashboard.print_result(name, "FAIL", 0, error, traceback)
                        else:
                            dashboard.print_result(name, "SKIP", 0)
                    
                    # Use file counts from batch result
                    files_passed = run_output.get("files_passed", len(files_to_run))
                    files_failed = run_output.get("files_failed", 0)
                    
                    # Update failed_files tracking for 'f' key
                    if files_failed > 0:
                        # We can't know exactly which files failed in batch mode,
                        # so mark all as suspect if any failed
                        for f in files_to_run:
                            watch_state["failed_files"].add(f.stem)
                    else:
                        for f in files_to_run:
                            watch_state["failed_files"].discard(f.stem)
                            
                else:
                    for f in files_to_run:
                        run_output = single_runner(
                            f, bundle, tests_dir, config,
                            timeout=to, verbose=args.verbose, source_map=source_map
                        )
                        
                        duration = run_output.get("duration", 0)
                        
                        if run_output.get("results"):
                             for r in run_output["results"]:
                                 dashboard.print_result(
                                     r["name"], 
                                     r["status"], 
                                     0, # No per-test duration available
                                     r.get("error"), 
                                     r.get("traceback")
                                 )
                        else:
                             # Fallback for system errors or empty results
                             rel_path = os.path.relpath(f, os.getcwd())
                             status = "PASS" if run_output.get("success") else "FAIL"
                             dashboard.print_result(rel_path, status, duration, run_output.get("error"))

                        if run_output.get("success"):
                            files_passed += 1
                            watch_state["failed_files"].discard(f.stem)
                        else:
                            files_failed += 1
                            watch_state["failed_files"].add(f.stem)
                        
                        all_results.extend(run_output.get("results", []))
                
                total_time = time.time() - start_time
                
                # Count test results
                tests_passed = sum(1 for r in all_results if r.get("status") == "PASSED")
                tests_failed = sum(1 for r in all_results if r.get("status") == "FAILED")
                tests_total = tests_passed + tests_failed
                
                # Print summary
                dashboard.print_summary(
                    files_passed, files_failed, len(files_to_run),
                    tests_passed, tests_failed, tests_total,
                    total_time
                )
                
                # Print watching status
                dashboard.print_watching()
                
                watch_state["last_results"] = all_results
                
            except Exception as e:
                dashboard.stop_spinner()
                dashboard.clear()
                dashboard.print_header()
                print(f"\n[ERROR] {e}")
                dashboard.print_watching()
        
        observer = Observer()
        handler = ChangeHandler()
        observer.schedule(handler, str(paths["src"]), recursive=True)
        observer.schedule(handler, str(tests_dir), recursive=True)
        observer.schedule(handler, str(paths["root"]), recursive=False)
        
        observer.start()
        
        # Initial run
        run_tests_with_dashboard("all")
        
        try:
            while True:
                time.sleep(0.05)  # Check more frequently for key presses
                
                # Check for key presses
                key = get_key_press()
                if key:
                    if key == 'q':
                        observer.stop()
                        observer.join()
                        print("\n\nGoodbye! 👋")
                        return 0
                    elif key == 'f':
                        run_tests_with_dashboard("failed")
                    elif key == 'a':
                        run_tests_with_dashboard("all")
                    elif key == 'enter':
                        run_tests_with_dashboard("all")
                
                # Check for file changes (with debounce)
                if watch_state["trigger_run"]:
                    if time.time() - watch_state["last_change_time"] > 0.3:
                        watch_state["trigger_run"] = False
                        path = watch_state["changed_path"]
                        run_tests_with_dashboard("smart", path)
                        
        except KeyboardInterrupt:
            observer.stop()
            observer.join()
            print("\n\nGoodbye! 👋")
            return 0
    
    # Normal execution (non-watch mode)
    testez_bundle = bundle_testez()
    scripts_bundle, source_map = bundle_scripts(paths, config)
    
    offset = testez_bundle.count('\n') + 1
    for mapping in source_map:
        mapping["start"] += offset
        mapping["end"] += offset

    bundle = testez_bundle + "\n" + scripts_bundle
    
    batch_mode = len(files) > 1 and args.test == "all"
    
    return run_test_suite(args, files, bundle, tests_dir, config, source_map=source_map, batch_mode=batch_mode)
