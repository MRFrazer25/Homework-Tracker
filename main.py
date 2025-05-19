"""Main script to launch the Homework Tracker application."""

import tkinter as tk
import ttkbootstrap as ttkbs # Import ttkbootstrap
from src.gui.app import HomeworkTrackerApp
from src.utils.settings_manager import load_app_settings, save_app_settings

def main():
    """Main entry point for the Homework Tracker application"""
    
    settings = load_app_settings()
    initial_theme_name = settings.get("theme", "litera") 

    try:
        # The themename argument directly sets the theme.
        root = ttkbs.Window(themename=initial_theme_name)
    except tk.TclError:
        print(f"Failed to apply ttkbootstrap theme '{initial_theme_name}'. Falling back to 'litera'.")
        root = ttkbs.Window(themename="litera") # Default fallback for ttkbootstrap
        settings["theme"] = "litera" # Update settings if fallback is used.
        save_app_settings(settings) # Save the updated settings with the fallback theme

    root.title("Homework Tracker with Chatbot Assistant")
    root.geometry("1200x800")
    root.minsize(1000, 600)
    
    # HomeworkTrackerApp will now receive a ttkbootstrap.Window instance
    app = HomeworkTrackerApp(root, settings)
    app.run()

if __name__ == "__main__":
    main()
