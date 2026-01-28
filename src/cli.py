"""
Roblox Test Runner - CLI interface
"""
import sys
import time
import argparse
from pathlib import Path
from .config import get_config, validate_config, prompt_config, get_api_url
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
        default=DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help=f"Timeout per test in seconds (default: {DEFAULT_TIMEOUT})"
    )
    
    # --- config command ---
    config_parser = subparsers.add_parser("config", help="Configure API credentials")
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration (API key masked)"
    )
    
    # --- auth command (for CI/CD) ---
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
    
    return parser


def cmd_config(args):
    """Handle config command"""
    from .config import load_config_file
    
    if args.show:
        config = load_config_file()
        print("\n=== Current Configuration ===")
        if config.get("api_key"):
            masked = "*" * 20 + "..." + config["api_key"][-4:]
            print(f"API Key: {masked}")
        else:
            print("API Key: (not set)")
        print(f"Universe ID: {config.get('universe_id', '(not set)')}")
        print(f"Place ID: {config.get('place_id', '(not set)')}")
        return 0
    
    # Interactive setup
    prompt_config()
    return 0


def cmd_auth(args):
    """Handle auth command for CI/CD"""
    import os
    from .config import save_config_file
    
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
        config = {
            "api_key": args.key,
            "universe_id": args.universe,
            "place_id": args.place,
        }
        save_config_file(config)
        print("✅ Credentials saved")
        return 0
    
    print("[ERROR] Use --github for CI/CD or --key to provide API key directly")
    return 1


def cmd_run(args):
    """Handle run command"""
    from .utils import get_project_paths
    
    # Load and validate config
    config = get_config()
    missing = validate_config(config)
    
    if missing:
        print("[ERROR] Missing configuration:")
        for m in missing:
            print(f"  - {m}")
        print("\nRun 'roblox-test-runner config' to set up credentials")
        return 1
    
    paths = get_project_paths()
    tests_dir = paths["tests"]
    
    files = list(tests_dir.glob("*.spec.luau"))
    files = [f for f in files if not f.name.startswith("_")]
    
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
                if event.src_path.endswith(('.luau', '.lua')):
                    if time.time() - self.last_run < 1:
                        return
                    self.last_run = time.time()
                    print(f"\n[WATCH] Detected change: {event.src_path}")
                    self.callback()
        
        def run_tests_for_watch():
            testez_bundle = bundle_testez()
            scripts_bundle = bundle_scripts(paths)
            bundle = testez_bundle + "\n" + scripts_bundle
            run_test_suite(args, files, bundle, tests_dir, config)
        
        observer = Observer()
        handler = ChangeHandler(run_tests_for_watch)
        observer.schedule(handler, str(paths["src"]), recursive=True)
        observer.schedule(handler, str(tests_dir), recursive=True)
        observer.start()
        
        print(f"[WATCH] Monitoring {paths['src']} and {tests_dir} for changes...")
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
    scripts_bundle = bundle_scripts(paths)
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
            args.timeout = DEFAULT_TIMEOUT
        else:
            args.command = "run"
            args.test = "all"
            args.list = False
            args.verbose = False
            args.json = False
            args.watch = False
            args.timeout = DEFAULT_TIMEOUT
    
    if args.command == "config":
        sys.exit(cmd_config(args))
    elif args.command == "auth":
        sys.exit(cmd_auth(args))
    elif args.command == "run":
        sys.exit(cmd_run(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
