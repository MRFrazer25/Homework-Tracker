import tkinter as tk
from tkinter import ttk, messagebox # filedialog might be needed for add/edit dialogs later

# Core components
from src.core.data_handler import DataHandler
from src.core.assignment_manager import AssignmentManager
# Chatbot core logic is used by ChatbotTab, not directly here unless app needs to send messages

# GUI Tab Modules
from .dashboard_tab import DashboardTab
from .assignments_tab import AssignmentsTab
from .statistics_tab import StatisticsTab
from .calendar_tab import CalendarTab
from .chatbot_tab import ChatbotTab

# Utilities (if needed directly by app.py, otherwise imported by tabs)
# from src.utils.helpers import format_date

class HomeworkTrackerApp:
    """Main application class for the Homework Tracker."""
    def __init__(self, root):
        """
        Initializes the main application.
        Sets up data handling, assignment management, styles, and UI widgets.
        """
        self.root = root
        self.data_handler = DataHandler()
        self.assignment_manager = AssignmentManager(self.data_handler)
        
        self.notebook = None
        # References to tab instances for potential cross-tab communication or refresh
        self.dashboard_tab_instance = None
        self.assignments_tab_instance = None
        self.statistics_tab_instance = None
        self.calendar_tab_instance = None
        self.chatbot_tab_instance = None
        
        self._setup_styles()
        self._create_main_widgets()
        self._create_menu()
        self.apply_theme()

    def _setup_styles(self):
        """Configures the application's visual style using ttk themes and custom accents."""
        self.style = ttk.Style()
        
        # Attempt to use 'clam' theme, fallback to system default.
        try:
            self.style.theme_use('clam') 
        except tk.TclError:
            print("Clam theme not available, using system default ttk theme.")
            # ttk will use its default theme for the OS.
            pass 

        # Base font configurations (applied after theme_use to ensure they take effect)
        self.style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'))
        self.style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))
        self.style.configure("TNotebook.Tab", font=('Helvetica', 10, 'normal'), padding=[5,2])

        # Define a more vibrant accent color
        vibrant_blue_accent = "#1E90FF"  # DodgerBlue
        selection_text_color = "white" # White text on vibrant blue for better contrast

        # Apply vibrant blue accents to specific widget states
        self.style.map("Treeview",
                       background=[("selected", vibrant_blue_accent)],
                       foreground=[("selected", selection_text_color)])
        
        self.style.configure("TButton", padding=5) 
        self.style.map("TButton",
                       background=[("active", vibrant_blue_accent)],
                       foreground=[("active", selection_text_color)]) # Ensure text is visible on active button
        
        # Minimal theme settings for dialogs or custom widgets needing specific colors.
        self.app_theme_settings = {
            "date_entry_style": {
                "selectbackground": vibrant_blue_accent,
                "selectforeground": selection_text_color,
                # Other DateEntry colors will use tkcalendar's defaults for a light theme.
            },
            "entry_bg": "white", # Default background for tk.Text
            "entry_fg": "black"  # Default foreground for tk.Text
        }

    def get_current_theme_settings(self):
        """Returns theme settings, mainly for dialogs or custom widgets."""
        return self.app_theme_settings

    def apply_theme(self):
        """
        Applies the configured theme settings.
        Currently, most styling is handled by ttk's default theme and accents in _setup_styles.
        This method can be expanded if more dynamic theme application is needed.
        """
        # Root background uses system default.
        
        # Call on_theme_changed on tabs if they implement it, for any custom adjustments.
        for tab_instance in [self.dashboard_tab_instance, self.assignments_tab_instance, 
                             self.statistics_tab_instance, self.calendar_tab_instance, 
                             self.chatbot_tab_instance]:
            if tab_instance and hasattr(tab_instance, 'on_theme_changed'):
                tab_instance.on_theme_changed() 
        print("Applied default theme with vibrant blue accents.")

    def _create_main_widgets(self):
        """Creates and packs the main UI components like the notebook for tabs."""
        self.notebook = ttk.Notebook(self.root)
        
        # Data provider function for tabs
        assignments_provider = self.assignment_manager.get_assignments

        # Callbacks for tabs to interact with the main application logic
        app_callbacks = {
            'edit_assignment': self.handle_edit_assignment_request,
            'add_assignment': self.handle_add_assignment_request,
            'delete_assignment': self.handle_delete_assignment_request,
            'toggle_completion': self.handle_toggle_completion_request,
            'refresh_all_tabs': self.refresh_all_tabs,
            'get_theme_settings': self.get_current_theme_settings 
        }

        # Dashboard Tab
        self.dashboard_tab_instance = DashboardTab(self.notebook, assignments_provider, app_callbacks)
        self.notebook.add(self.dashboard_tab_instance, text='Dashboard')

        # Assignments Tab
        self.assignments_tab_instance = AssignmentsTab(self.notebook, assignments_provider, app_callbacks)
        self.notebook.add(self.assignments_tab_instance, text='Assignments')

        # Statistics Tab (currently does not use app_callbacks beyond what might be passed for data)
        self.statistics_tab_instance = StatisticsTab(self.notebook, assignments_provider) 
        self.notebook.add(self.statistics_tab_instance, text='Statistics')
        
        # Calendar Tab
        self.calendar_tab_instance = CalendarTab(self.notebook, assignments_provider, app_callbacks)
        self.notebook.add(self.calendar_tab_instance, text='Calendar')

        # Chatbot Tab (data_handler for its own logic, assignments_provider for context)
        self.chatbot_tab_instance = ChatbotTab(self.notebook, self.data_handler, assignments_provider, app_callbacks) # Pass app_callbacks
        self.notebook.add(self.chatbot_tab_instance, text='AI Chatbot')
        
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

    def _create_menu(self):
        """Configures the main application menu. Currently sets an empty menu."""
        # Set an empty menu to remove any default File/View menus.
        empty_menu = tk.Menu(self.root)
        self.root.config(menu=empty_menu)


    # --- Callback Handlers for Tabs ---
    def handle_add_assignment_request(self, assignment_data):
        """Handles request to add a new assignment from a tab's dialog."""
        try:
            success, message_or_id = self.assignment_manager.add_assignment(assignment_data)
            if success:
                messagebox.showinfo("Success", "Assignment added successfully!", parent=self.root)
            else:
                err_msg = message_or_id if isinstance(message_or_id, str) else "Failed to add assignment."
                messagebox.showerror("Add Error", err_msg, parent=self.root)
            self.refresh_all_tabs() # Always refresh to show current state
        except Exception as e:
            messagebox.showerror("Add Error", f"An unexpected error occurred: {e}", parent=self.root)
            self.refresh_all_tabs() # Refresh to maintain UI consistency

    def handle_edit_assignment_request(self, assignment_data):
        """Handles request to update an existing assignment from a tab's dialog."""
        try:
            success, message = self.assignment_manager.update_assignment(assignment_data)
            if success:
                messagebox.showinfo("Success", "Assignment updated successfully!", parent=self.root)
            else:
                err_msg = message if message else "Failed to update assignment."
                messagebox.showerror("Update Error", err_msg, parent=self.root)
            self.refresh_all_tabs() # Always refresh
        except Exception as e:
            messagebox.showerror("Update Error", f"An unexpected error occurred: {e}", parent=self.root)
            self.refresh_all_tabs()

    def handle_delete_assignment_request(self, assignment_obj):
        """Handles request to delete an assignment. Expects assignment_obj with 'id' and 'name'."""
        assignment_id = assignment_obj.get('id')
        assignment_name = assignment_obj.get('name', 'the selected assignment')

        if not assignment_id:
            messagebox.showerror("Delete Error", "Cannot delete assignment: ID missing.", parent=self.root)
            return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{assignment_name}'?", parent=self.root):
            success, message = self.assignment_manager.delete_assignment(assignment_id)
            if success:
                messagebox.showinfo("Success", f"'{assignment_name}' deleted.", parent=self.root)
            else:
                err_msg = message if message else "Failed to delete assignment."
                messagebox.showerror("Error", err_msg, parent=self.root)
            self.refresh_all_tabs() # Always refresh
    
    def handle_toggle_completion_request(self, assignment_obj):
        """Handles request to toggle completion status. Expects assignment_obj with 'id'."""
        assignment_id = assignment_obj.get('id')
        if not assignment_id:
            messagebox.showerror("Error", "Cannot toggle completion: ID missing.", parent=self.root)
            return

        success, message = self.assignment_manager.toggle_completion(assignment_id)
        if success:
            # No specific success message for toggle, refresh will show change.
            pass
        else:
            err_msg = message if message else "Failed to update completion status."
            messagebox.showerror("Error", err_msg, parent=self.root)
        self.refresh_all_tabs() # Always refresh

    def refresh_all_tabs(self):
        """Calls a data refresh method on each tab instance if it exists."""
        if self.statistics_tab_instance and hasattr(self.statistics_tab_instance, 'refresh_charts'):
            self.statistics_tab_instance.refresh_charts()
        
        if self.dashboard_tab_instance and hasattr(self.dashboard_tab_instance, 'refresh_data'):
            self.dashboard_tab_instance.refresh_data()
        if self.assignments_tab_instance and hasattr(self.assignments_tab_instance, 'update_assignments_list'):
            self.assignments_tab_instance.update_assignments_list() 
        if self.calendar_tab_instance and hasattr(self.calendar_tab_instance, 'refresh_data'):
            self.calendar_tab_instance.refresh_data()
        
        print("All tabs refreshed.")

    def run(self):
        """Starts the Tkinter main event loop."""
        self.root.mainloop()

# No if __name__ == '__main__': block here, main.py handles app startup.
