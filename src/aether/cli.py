"""
Aether - CLI interface
"""
import sys
import argparse
from .commands import run, init, config, auth

def create_parser():
    """Create CLI argument parser with subcommands"""
    parser = argparse.ArgumentParser(
        prog="aether",
        description="Aether - Execute Luau tests on Roblox Cloud",
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
        "--failed",
        action="store_true",
        help="Run only tests that failed in the previous run"
    )
    run_parser.add_argument(
        "-t", "--timeout",
        type=int,
        metavar="SECONDS",
        help=f"Timeout per test in seconds"
    )
    
    # --- config command ---
    subparsers.add_parser("config", help="Show current configuration")
    
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


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Default to help if no command specified
    if args.command is None:
         parser.print_help()
         sys.exit(0)
    
    if args.command == "config":
        sys.exit(config.command(args))
    elif args.command == "auth":
        sys.exit(auth.command_auth(args))
    elif args.command == "set-api":
        sys.exit(auth.command_set_api(args))
    elif args.command == "init":
        sys.exit(init.command(args))
    elif args.command == "run":
        sys.exit(run.command(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
