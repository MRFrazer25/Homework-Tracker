"""Main script to launch the Homework Tracker application."""

import tkinter as tk
from src.gui.app import HomeworkTrackerApp

def main():
    """Main entry point for the Homework Tracker application"""
    root = tk.Tk()
    root.title("Homework Tracker")
    root.geometry("1200x800")
    root.minsize(1000, 600)
    
    # Create and run the main application
    app = HomeworkTrackerApp(root)
    app.run()

if __name__ == "__main__":
    main()
