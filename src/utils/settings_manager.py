import json
import os

SETTINGS_FILE = "data/settings.json"
DEFAULT_THEME = "litera"

def load_app_settings():
    """Loads application settings from a JSON file."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                if not isinstance(settings, dict): # Basic validation
                    print(f"Warning: {SETTINGS_FILE} does not contain a valid dictionary. Using defaults.")
                    return {"theme": DEFAULT_THEME}
                if "theme" not in settings: # Ensure theme key exists
                     settings["theme"] = DEFAULT_THEME
                return settings
        except json.JSONDecodeError:
            print(f"Error decoding {SETTINGS_FILE}. Using default settings.")
            return {"theme": DEFAULT_THEME}
        except Exception as e:
            print(f"Error loading {SETTINGS_FILE}: {e}. Using default settings.")
            return {"theme": DEFAULT_THEME}
    else:
        # If settings file doesn't exist, create it with defaults
        print(f"{SETTINGS_FILE} not found. Creating with default settings.")
        default_settings = {"theme": DEFAULT_THEME}
        save_app_settings(default_settings)
        return default_settings

def save_app_settings(settings_dict):
    """Saves application settings to a JSON file."""
    try:
        # Ensure the data directory exists
        data_dir = os.path.dirname(SETTINGS_FILE)
        if not os.path.exists(data_dir) and data_dir: # Check if data_dir is not empty string
            os.makedirs(data_dir)
            print(f"Created directory: {data_dir}")
        
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_dict, f, indent=4)
        print(f"Settings saved to {SETTINGS_FILE}")
    except Exception as e:
        print(f"Error saving settings to {SETTINGS_FILE}: {e}")