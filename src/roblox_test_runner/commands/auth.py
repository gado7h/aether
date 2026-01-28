import os
from ..config import save_user_config

def command_auth(args):
    """Handle auth command for CI/CD"""
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

def command_set_api(args):
    """Handle set-api command"""
    if not args.key:
        print("[ERROR] API key required")
        return 1
    save_user_config("api_key", args.key)
    print("✅ API key saved to user configuration")
    return 0
