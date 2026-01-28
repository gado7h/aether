from ..config import get_config

def command(args):
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
