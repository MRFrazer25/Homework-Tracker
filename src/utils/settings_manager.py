import json
from src.utils.paths import DATA_DIR

SETTINGS_FILE = DATA_DIR / "settings.json"
DEFAULT_THEME = "litera" # Must be a ttkbootstrap theme name
# Hugging Face model for the chat assistant; set "assistant_model" to null in settings.json to disable it
DEFAULT_ASSISTANT_MODEL = "ibm-granite/granite-4.0-1b"
# The exact commit of the default model that was tested; other models load their latest version
DEFAULT_ASSISTANT_REVISION = "6a7381ba1f54d684ff508d991aeb7dc580157103"

def load_app_settings():
    """Loads application settings from a JSON file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
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
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, indent=4)
        print(f"Settings saved to {SETTINGS_FILE}")
    except Exception as e:
        print(f"Error saving settings to {SETTINGS_FILE}: {e}")
