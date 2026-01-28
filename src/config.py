"""
Roblox Test Runner - Configuration management

Handles API keys, universe/place IDs from multiple sources:
1. CLI flags
2. Environment variables  
3. Config file (~/.roblox-test-runner/config.json)
4. Project .env file
"""
import os
import json
import getpass
from pathlib import Path
from dotenv import load_dotenv

# Load project .env if exists
load_dotenv()

# Config file location
CONFIG_DIR = Path.home() / ".roblox-test-runner"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config_file():
    """Load config from user home directory"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config_file(config):
    """Save config to user home directory"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Config saved to {CONFIG_FILE}")

def get_config():
    """
    Load configuration from all sources with priority:
    1. Environment variables (for CI/CD)
    2. Config file (~/.roblox-test-runner/config.json)
    3. Defaults
    """
    file_config = load_config_file()
    
    # Defaults
    defaults = {
        "api_key": "vGtiGKMpOUuH7X1i1ddehLEVXFLgZ2JjOtW/3gQCEwlvYLFQZXlKaGJHY2lPaUpTVXpJMU5pSXNJbXRwWkNJNkluTnBaeTB5TURJeExUQTNMVEV6VkRFNE9qVXhPalE1V2lJc0luUjVjQ0k2SWtwWFZDSjkuZXlKaGRXUWlPaUpTYjJKc2IzaEpiblJsY201aGJDSXNJbWx6Y3lJNklrTnNiM1ZrUVhWMGFHVnVkR2xqWVhScGIyNVRaWEoyYVdObElpd2lZbUZ6WlVGd2FVdGxlU0k2SW5aSGRHbEhTMDF3VDFWMVNEZFlNV2t4WkdSbGFFeEZWbGhHVEdkYU1rcHFUM1JYTHpOblVVTkZkMngyV1V4R1VTSXNJbTkzYm1WeVNXUWlPaUl4TURReU1ETXhPREkzTnlJc0ltVjRjQ0k2TVRjMk9UVTRNRFl4T1N3aWFXRjBJam94TnpZNU5UYzNNREU1TENKdVltWWlPakUzTmprMU56Y3dNVGw5Lmsyb29MTW9YVy05a0lNUUJPOThpZURDUW1CXzJtS3g4OW5JdEY3YlpQcWNYRmk5SVRadnJaZndHbkRuM19KSUg3aXBXQ3kyWWNQbUhFTmlmZGVGQ3ViUDlybkQxX21veS1OZW15LXQ2SUFRZVZYUXloT1JuYi1aUEFzR2FNdEsxdm1aZEJ0YS1PQlh5YzZvbGlkcnRZdUlPUl9pQThQTjdCZVVQTWdDMUFCaVU1enNDUGl3cTktdHMzUG1FV0NadENjRl83MkFabXhBcGtzMzJmVWJfVzU0dXd2RV9vckF2c0t1d3FFVEhVY3pYa3g4b2M0cmN5Tk1MMnQ4b2FjcTB1cVdoOXZpcFJ4aTRMRXZwTzNwbXVWbEY1MkJKa0g2TUdRQWJaMW83QmNBNk1uYU4tcVQyRWdncm5KdHlhV2ZqV09ONk9yUFFicnVheUVVN1F1ekd1QQ==",
        "universe_id": "9635698060",
        "place_id": "131722995820694"
    }
    
    return {
        "api_key": os.environ.get("ROBLOX_API_KEY") or file_config.get("api_key") or defaults["api_key"],
        "universe_id": os.environ.get("UNIVERSE_ID") or file_config.get("universe_id") or defaults["universe_id"],
        "place_id": os.environ.get("PLACE_ID") or file_config.get("place_id") or defaults["place_id"],
    }

def validate_config(config):
    """Check if all required config values are present"""
    missing = []
    if not config.get("api_key"):
        missing.append("ROBLOX_API_KEY")
    if not config.get("universe_id"):
        missing.append("UNIVERSE_ID")
    if not config.get("place_id"):
        missing.append("PLACE_ID")
    return missing

def prompt_config():
    """Interactive configuration setup"""
    print("\n=== Roblox Test Runner Configuration ===\n")
    
    current = load_config_file()
    
    # API Key (masked input)
    print("Enter your Roblox Open Cloud API Key")
    print("(Get it from https://create.roblox.com/credentials)")
    if current.get("api_key"):
        print(f"Current: {'*' * 20}...{current['api_key'][-4:]}")
    api_key = getpass.getpass("API Key: ").strip()
    if not api_key and current.get("api_key"):
        api_key = current["api_key"]
    
    # Universe ID
    print("\nEnter your Universe ID")
    print("(Found in Game Settings > Basic Info)")
    if current.get("universe_id"):
        print(f"Current: {current['universe_id']}")
    universe_id = input("Universe ID: ").strip()
    if not universe_id and current.get("universe_id"):
        universe_id = current["universe_id"]
    
    # Place ID
    print("\nEnter your Place ID")
    print("(Found in the URL: roblox.com/games/PLACE_ID/...)")
    if current.get("place_id"):
        print(f"Current: {current['place_id']}")
    place_id = input("Place ID: ").strip()
    if not place_id and current.get("place_id"):
        place_id = current["place_id"]
    
    config = {
        "api_key": api_key,
        "universe_id": universe_id,
        "place_id": place_id,
    }
    
    save_config_file(config)
    print("\n✅ Configuration complete!")
    return config

def get_api_url(config):
    """Build API URL from config"""
    return f"https://apis.roblox.com/cloud/v2/universes/{config['universe_id']}/places/{config['place_id']}/luau-execution-session-tasks"
