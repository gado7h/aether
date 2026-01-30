"""
Aether - Configuration management

Handles configuration from:
1. CLI flags (highest priority)
2. Environment variables
3. TOML config files (hierarchical)
   - Current directory
   - Parent directories
   - User config (~/.config/aether/config.toml)
"""
import os
import sys
import getpass
from pathlib import Path
from dotenv import load_dotenv

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Load project .env if exists
load_dotenv()

# Config paths
USER_CONFIG_DIR = Path.home() / ".config" / "aether"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.toml"

def load_toml_file(path: Path) -> dict:
    """Load a single TOML file"""
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"[WARN] Failed to parse config {path}: {e}")
        return {}

def merge_config(base: dict, override: dict) -> dict:
    """Deep merge configuration dictionaries"""
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result

def load_config_hierarchy() -> dict:
    """Load configuration from all sources in order"""
    config = {}

    # 1. User global config
    config = merge_config(config, load_toml_file(USER_CONFIG_FILE))

    # 2. Walk up from current directory
    current = Path.cwd()
    root = Path(current.anchor)
    paths_to_check = []
    
    while current != root:
        paths_to_check.append(current / "aether.toml")
        current = current.parent
    paths_to_check.append(root / "aether.toml")
    
    # Load from root down to current (so closer configs override)
    for path in reversed(paths_to_check):
        config = merge_config(config, load_toml_file(path))

    return config

def get_config():
    """
    Get final configuration merged from files and environment
    """
    file_config = load_config_hierarchy()
    
    # Flatten structure for easy access, prioritizing env vars
    runner = file_config.get("runner", {})
    project = file_config.get("project", {})
    auth = file_config.get("auth", {})

    return {
        # Runnable settings
        "timeout": runner.get("timeout", 60),
        "watch_interval": runner.get("watch_interval", 1.0),
        "tests_folder": runner.get("tests_folder", "tests"),
        
        # Project integration
        "rojo_project": project.get("rojo_project", "default.project.json"),

        # Authentication
        "api_key": os.environ.get("ROBLOX_API_KEY") or auth.get("api_key") or "vGtiGKMpOUuH7X1i1ddehLEVXFLgZ2JjOtW/3gQCEwlvYLFQZXlKaGJHY2lPaUpTVXpJMU5pSXNJbXRwWkNJNkluTnBaeTB5TURJeExUQTNMVEV6VkRFNE9qVXhPalE1V2lJc0luUjVjQ0k2SWtwWFZDSjkuZXlKaGRXUWlPaUpTYjJKc2IzaEpiblJsY201aGJDSXNJbWx6Y3lJNklrTnNiM1ZrUVhWMGFHVnVkR2xqWVhScGIyNVRaWEoyYVdObElpd2lZbUZ6WlVGd2FVdGxlU0k2SW5aSGRHbEhTMDF3VDFWMVNEZFlNV2t4WkdSbGFFeEZWbGhHVEdkYU1rcHFUM1JYTHpOblVVTkZkMngyV1V4R1VTSXNJbTkzYm1WeVNXUWlPaUl4TURReU1ETXhPREkzTnlJc0ltVjRjQ0k2TVRjMk9UVTRNRFl4T1N3aWFXRjBJam94TnpZNU5UYzNNREU1TENKdVltWWlPakUzTmprMU56Y3dNVGw5Lmsyb29MTW9YVy05a0lNUUJPOThpZURDUW1CXzJtS3g4OW5JdEY3YlpQcWNYRmk5SVRadnJaZndHbkRuM19KSUg3aXBXQ3kyWWNQbUhFTmlmZGVGQ3ViUDlybkQxX21veS1OZW15LXQ2SUFRZVZYUXloT1JuYi1aUEFzR2FNdEsxdm1aZEJ0YS1PQlh5YzZvbGlkcnRZdUlPUl9pQThQTjdCZVVQTWdDMUFCaVU1enNDUGl3cTktdHMzUG1FV0NadENjRl83MkFabXhBcGtzMzJmVWJfVzU0dXd2RV9vckF2c0t1d3FFVEhVY3pYa3g4b2M0cmN5Tk1MMnQ4b2FjcTB1cVdoOXZpcFJ4aTRMRXZwTzNwbXVWbEY1MkJKa0g2TUdRQWJaMW83QmNBNk1uYU4tcVQyRWdncm5KdHlhV2ZqV09ONk9yUFFicnVheUVVN1F1ekd1QQ==",
        "universe_id": os.environ.get("UNIVERSE_ID") or auth.get("universe_id") or "9635698060",
        "place_id": os.environ.get("PLACE_ID") or auth.get("place_id") or "131722995820694",
    }

def save_user_config(key: str, value: str):
    """Save a specific key-value to the user config file"""
    # We need to write TOML. Since we only support reading (tomli), 
    # we'll do a simple append/update for the [auth] section manually 
    # or just tell the user to edit it if we want to avoid writing a full TOML writer.
    # But requested feature is `set-api`.
    
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Simple implementation: Read existing, update logic, write back.
    # Since we can't easily write TOML with tomli/tomllib, we will use a basic template approach 
    # for this specific use case to avoid adding a heavy write dependency.
    
    # However, to properly support editing, we might need 'tomli-w' or similar.
    # Given the constraint, we will append/rewrite for this simple case.
    
    content = ""
    if USER_CONFIG_FILE.exists():
        with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
            content = f.read()

    # If it's the API key, we want to put it under [auth]
    if key == "api_key":
        line = f'api_key = "{value}"'
        if "[auth]" not in content:
            content += "\n[auth]\n" + line + "\n"
        else:
            # Check if key exists
            import re
            if re.search(r"api_key\s*=", content):
                content = re.sub(r'api_key\s*=\s*".*"', line, content)
            else:
                 # Insert after [auth]
                 content = content.replace("[auth]", f"[auth]\n{line}")
    
    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"Updated {key} in {USER_CONFIG_FILE}")

def validate_config(config):
    """Check if all required config values are present"""
    missing = []
    if not config.get("api_key"):
        missing.append("ROBLOX_API_KEY (env) or api_key (config)")
    if not config.get("universe_id"):
        missing.append("UNIVERSE_ID (env) or universe_id (config)")
    if not config.get("place_id"):
        missing.append("PLACE_ID (env) or place_id (config)")
    return missing

def get_api_url(config):
    """Build API URL from config"""
    return f"https://apis.roblox.com/cloud/v2/universes/{config['universe_id']}/places/{config['place_id']}/luau-execution-session-tasks"
