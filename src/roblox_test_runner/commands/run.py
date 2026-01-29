import time
from ..config import get_config, validate_config
from ..bundler import bundle_scripts, bundle_testez
from ..runner import run_test_suite
from ..utils import get_project_paths

def command(args):
    """Handle run command"""
    
    # Load and validate config
    config = get_config()
    
    # Override config with CLI args
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
    
    # Use configured tests folder
    if config.get("tests_folder"):
        custom_tests = paths["root"] / config["tests_folder"]
        if custom_tests.exists():
            paths["tests"] = custom_tests
        else:
             print(f"[ERROR] Configured tests path not found: {custom_tests}")
             return 1

    tests_dir = paths["tests"]
    
    # Check if we have tests
    files = list(tests_dir.glob("*.spec.luau"))
    files = [f for f in files if not f.name.startswith("_")]
    
    if not files:
        print(f"[WARN] No .spec.luau files found in {tests_dir}")
        return 0
    
    # List mode
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
        
        class ChangeHandler(FileSystemEventHandler):
            def __init__(self, callback):
                self.callback = callback
                self.last_run = 0
                
            def on_modified(self, event):
                if event.is_directory:
                    return
                # Watch both lua files and TOML config
                if event.src_path.endswith(('.luau', '.lua', '.toml', '.json')):
                    if time.time() - self.last_run < config["watch_interval"]:
                        return
                    self.last_run = time.time()
                    print(f"\n[WATCH] Detected change: {event.src_path}")
                    self.callback()
        
        def run_tests_for_watch():
            testez_bundle = bundle_testez()
            scripts_bundle, source_map = bundle_scripts(paths, config)
            
            # Adjust source map offsets
            offset = testez_bundle.count('\n') + 1
            for mapping in source_map:
                mapping["start"] += offset
                mapping["end"] += offset
            
            bundle = testez_bundle + "\n" + scripts_bundle
            run_test_suite(args, files, bundle, tests_dir, config, source_map=source_map)
        
        observer = Observer()
        handler = ChangeHandler(run_tests_for_watch)
        observer.schedule(handler, str(paths["src"]), recursive=True)
        observer.schedule(handler, str(tests_dir), recursive=True)
        observer.schedule(handler, str(paths["root"]), recursive=False)
        
        observer.start()
        
        print(f"[WATCH] Monitoring for changes...")
        print("Press Ctrl+C to stop")
        
        # Initial run
        run_tests_for_watch()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            observer.join()
            return 0
    
    # Normal execution
    testez_bundle = bundle_testez()
    scripts_bundle, source_map = bundle_scripts(paths, config)
    
    # Adjust source map offsets
    offset = testez_bundle.count('\n') + 1
    for mapping in source_map:
        mapping["start"] += offset
        mapping["end"] += offset

    bundle = testez_bundle + "\n" + scripts_bundle
    return run_test_suite(args, files, bundle, tests_dir, config, source_map=source_map)
