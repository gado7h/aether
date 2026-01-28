"""
Roblox Test Runner - CLI interface
"""
import sys
import time
import argparse
from pathlib import Path
from .config import get_config, validate_config, get_api_url, save_user_config
from .bundler import bundle_scripts, bundle_testez
from .runner import run_test_suite

DEFAULT_TIMEOUT = 60


def create_parser():
    """Create CLI argument parser with subcommands"""
    parser = argparse.ArgumentParser(
        prog="roblox-test-runner",
        description="Roblox Test Runner - Execute Luau tests on Roblox Cloud",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # --- run command (default) ---
    run_parser = subparsers.add_parser("run", help="Run tests")
    run_parser.add_argument(
        "test",
        nargs="?",
        default="all",
        help="Test name to run (fuzzy match) or 'all' for all tests"
    )
    run_parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all available tests without running them"
    )
    run_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output including logs"
    )
    run_parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Output results in JSON format (for CI/CD)"
    )
    run_parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Watch for file changes and auto re-run tests"
    )
    run_parser.add_argument(
        "-t", "--timeout",
        type=int,
        metavar="SECONDS",
        help=f"Timeout per test in seconds"
    )
    
    # --- config command ---
    config_parser = subparsers.add_parser("config", help="Show current configuration")
    
    # --- set-api command ---
    set_api_parser = subparsers.add_parser("set-api", help="Save API key to user config")
    set_api_parser.add_argument(
        "key",
        help="Roblox Open Cloud API Key"
    )

    # --- auth command (legacy/CI) ---
    auth_parser = subparsers.add_parser("auth", help="Authenticate for CI/CD")
    auth_parser.add_argument(
        "--github",
        action="store_true",
        help="Use GitHub Actions environment variables"
    )
    auth_parser.add_argument(
        "--key",
        type=str,
        help="Provide API key directly"
    )
    auth_parser.add_argument(
        "--universe",
        type=str,
        help="Universe ID"
    )
    auth_parser.add_argument(
        "--place",
        type=str,
        help="Place ID"
    )
    
    # --- init command ---
    subparsers.add_parser("init", help="Create default configuration file")

    return parser


def cmd_init(args):
    """Handle init command"""
    config_path = Path("roblox-test-runner.toml")
    if config_path.exists():
        print("[ERROR] roblox-test-runner.toml already exists")
        return 1
    
    default_config = """# Roblox Test Runner Configuration

[runner]
# Timeout for each test in seconds
timeout = 60
# How often to check for file changes in watch mode (seconds)
watch_interval = 1.0
# Folder containing your test files
tests_folder = "tests"

[project]
# Path to your Rojo project file
rojo_project = "default.project.json"

[auth]
# Optional: Set your Universe and Place IDs here
universe_id = "9635698060"
place_id = "131722995820694"
# API Key (Default alt account provided for testing)
api_key = "vGtiGKMpOUuH7X1i1ddehLEVXFLgZ2JjOtW/3gQCEwlvYLFQZXlKaGJHY2lPaUpTVXpJMU5pSXNJbXRwWkNJNkluTnBaeTB5TURJeExUQTNMVEV6VkRFNE9qVXhPalE1V2lJc0luUjVjQ0k2SWtwWFZDSjkuZXlKaGRXUWlPaUpTYjJKc2IzaEpiblJsY201aGJDSXNJbWx6Y3lJNklrTnNiM1ZrUVhWMGFHVnVkR2xqWVhScGIyNVRaWEoyYVdObElpd2lZbUZ6WlVGd2FVdGxlU0k2SW5aSGRHbEhTMDF3VDFWMVNEZFlNV2t4WkdSbGFFeEZWbGhHVEdkYU1rcHFUM1JYTHpOblVVTkZkMngyV1V4R1VTSXNJbTkzYm1WeVNXUWlPaUl4TURReU1ETXhPREkzTnlJc0ltVjRjQ0k2TVRjMk9UVTRNRFl4T1N3aWFXRjBJam94TnpZNU5UYzNNREU1TENKdVltWWlPakUzTmprMU56Y3dNVGw5Lmsyb29MTW9YVy05a0lNUUJPOThpZURDUW1CXzJtS3g4OW5JdEY3YlpQcWNYRmk5SVRadnJaZndHbkRuM19KSUg3aXBXQ3kyWWNQbUhFTmlmZGVGQ3ViUDlybkQxX21veS1OZW15LXQ2SUFRZVZYUXloT1JuYi1aUEFzR2FNdEsxdm1aZEJ0YS1PQlh5YzZvbGlkcnRZdUlPUl9pQThQTjdCZVVQTWdDMUFCaVU1enNDUGl3cTktdHMzUG1FV0NadENjRl83MkFabXhBcGtzMzJmVWJfVzU0dXd2RV9vckF2c0t1d3FFVEhVY3pYa3g4b2M0cmN5Tk1MMnQ4b2FjcTB1cVdoOXZpcFJ4aTRMRXZwTzNwbXVWbEY1MkJKa0g2TUdRQWJaMW83QmNBNk1uYU4tcVQyRWdncm5KdHlhV2ZqV09ONk9yUFFicnVheUVVN1F1ekd1QQ=="
"""
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(default_config)
    
    print("✅ Created roblox-test-runner.toml")
    return 0


def cmd_config(args):
    """Handle config command"""
    config = get_config()
    print("\n=== Current Configuration ===")
    if config.get("api_key"):
        masked = "*" * 20 + "..." + config["api_key"][-4:]
        print(f"API Key: {masked}")
    else:
        print("API Key: (not set)")
    print(f"Universe ID: {config.get('universe_id', '(not set)')}")
    print(f"Place ID: {config.get('place_id', '(not set)')}")
    print(f"Tests Folder: {config.get('tests_folder', '(default)')}")
    print(f"Rojo Project: {config.get('rojo_project', '(default)')}")
    return 0


def cmd_set_api(args):
    """Handle set-api command"""
    if not args.key:
        print("[ERROR] API key required")
        return 1
    save_user_config("api_key", args.key)
    print("✅ API key saved to user configuration")
    return 0


def cmd_auth(args):
    """Handle auth command for CI/CD"""
    import os
    
    if args.github:
        # Read from GitHub Actions environment
        api_key = os.environ.get("ROBLOX_API_KEY")
        universe_id = os.environ.get("UNIVERSE_ID") or args.universe
        place_id = os.environ.get("PLACE_ID") or args.place
        
        if not api_key:
            print("[ERROR] ROBLOX_API_KEY environment variable not found")
            print("Make sure it's set in GitHub Secrets and passed to the workflow")
            return 1
            
        if not universe_id or not place_id:
            print("[ERROR] UNIVERSE_ID and PLACE_ID required")
            print("Set them as environment variables or use --universe and --place flags")
            return 1
        
        print("✅ Authenticated via GitHub Actions environment")
        print(f"   Universe: {universe_id}")
        print(f"   Place: {place_id}")
        return 0
    
    if args.key:
        # Legacy support: use set-api logic
        save_user_config("api_key", args.key)
        print("✅ Credentials saved")
        return 0
    
    print("[ERROR] Use --github for CI/CD or --key to provide API key directly")
    return 1


def cmd_run(args):
    """Handle run command"""
    from .utils import get_project_paths
    
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
            # If default tests folder was different, update it
        else:
             # Fallback or strict error? 
             # Let's warn but check default if custom doesn't exist, 
             # OR strictly fail. The user asked for "configurable", usually implies strict.
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
            # Reload config on change? For now, just re-run with existing args but fresh bundle
            # Ideally we reload config, but that's complex
            testez_bundle = bundle_testez()
            scripts_bundle = bundle_scripts(paths, config)
            bundle = testez_bundle + "\n" + scripts_bundle
            run_test_suite(args, files, bundle, tests_dir, config)
        
        observer = Observer()
        handler = ChangeHandler(run_tests_for_watch)
        observer.schedule(handler, str(paths["src"]), recursive=True)
        observer.schedule(handler, str(tests_dir), recursive=True)
        # Also watch project root for config files?
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
    scripts_bundle = bundle_scripts(paths, config)
    bundle = testez_bundle + "\n" + scripts_bundle
    return run_test_suite(args, files, bundle, tests_dir, config)


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Default to 'run' if no command specified
    if args.command is None:
        # Check if first arg looks like a test name
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            # Treat as "run <test>"
            args.command = "run"
            args.test = sys.argv[1]
            args.list = False
            args.verbose = False
            args.json = False
            args.watch = False
            args.timeout = None
        else:
            args.command = "run"
            args.test = "all"
            args.list = False
            args.verbose = False
            args.json = False
            args.watch = False
            args.timeout = None
    
    if args.command == "config":
        sys.exit(cmd_config(args))
    elif args.command == "auth":
        sys.exit(cmd_auth(args))
    elif args.command == "set-api":
        sys.exit(cmd_set_api(args))
    elif args.command == "init":
        sys.exit(cmd_init(args))
    elif args.command == "run":
        sys.exit(cmd_run(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
