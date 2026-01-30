from pathlib import Path

def command(args):
    """Handle init command"""
    config_path = Path("aether.toml")
    if config_path.exists():
        print("[ERROR] aether.toml already exists")
        return 1
    
    default_config = """# Aether Configuration

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
    
    print("[OK] Created aether.toml")
    return 0
