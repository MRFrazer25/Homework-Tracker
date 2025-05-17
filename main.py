"""Main script to launch the Homework Tracker application."""

import tkinter as tk
# from ttkthemes import ThemedTk # No longer using ttkthemes
import ttkbootstrap as ttkbs # Import ttkbootstrap
from src.gui.app import HomeworkTrackerApp
from src.utils.settings_manager import load_app_settings, save_app_settings

def main():
    """Main entry point for the Homework Tracker application"""
    
    settings = load_app_settings()
    # ttkbootstrap themes are typically lowercase and might not match old ttkthemes names.
    # Default to a known ttkbootstrap theme like 'litera' (light) or 'darkly' (dark)
    # We'll refine this once app.py has its new theme list. For now, 'litera' is a safe default.
    initial_theme_name = settings.get("theme", "litera") 

    try:
        # ttkbootstrap.Window handles its own theme setting.
        # The themename argument directly sets the theme.
        root = ttkbs.Window(themename=initial_theme_name)
    except tk.TclError:
        print(f"Failed to apply ttkbootstrap theme '{initial_theme_name}'. Falling back to 'litera'.")
        root = ttkbs.Window(themename="litera") # Default fallback for ttkbootstrap
        settings["theme"] = "litera" # Update settings if fallback is used.
        save_app_settings(settings) # Save the updated settings with the fallback theme

    root.title("Homework Tracker with AI Assistant")
    root.geometry("1200x800")
    root.minsize(1000, 600)
    
    # HomeworkTrackerApp will now receive a ttkbootstrap.Window instance
    app = HomeworkTrackerApp(root, settings)
    app.run()

if __name__ == "__main__":
    main()
