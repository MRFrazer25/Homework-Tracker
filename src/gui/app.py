import tkinter as tk
from tkinter import ttk, messagebox

# Core components
from src.core.data_handler import DataHandler
from src.core.assignment_manager import AssignmentManager
from src.core.study_tips import StudyTipsGenerator
from src.core.chatbot import Chatbot

# GUI Tab Modules
from .dashboard_tab import DashboardTab
from .assignments_tab import AssignmentsTab
from .statistics_tab import StatisticsTab
from .calendar_tab import CalendarTab
from .chatbot_tab import ChatbotTab
from src.utils.settings_manager import save_app_settings

# Dark themes: https://ttkbootstrap.readthedocs.io/en/latest/themes/dark/
# Light themes: https://ttkbootstrap.readthedocs.io/en/latest/themes/light/
KNOWN_DARK_THEMES = ['darkly', 'cyborg', 'superhero', 'solar']
CURATED_THEMES_LIST = [
    ("Light - Cosmo", "cosmo"),
    ("Light - Flatly", "flatly"),
    ("Light - Litera", "litera"),
    ("Light - Sandstone", "sandstone"),
    ("Dark - Cyborg", "cyborg"),
    ("Dark - Darkly", "darkly"),
    ("Dark - Solar", "solar"),
    ("Dark - Superhero", "superhero"),
]

class HomeworkTrackerApp:
    """Main application class for the Homework Tracker."""
    def __init__(self, root, settings):
        """
        Initializes the main application.
        Sets up data handling, assignment management, styles, and UI widgets.
        """
        self.root = root
        self.settings = settings
        self.data_handler = DataHandler()
        self.assignment_manager = AssignmentManager(self.data_handler)
        self.study_tips_generator = StudyTipsGenerator()

        self.CURATED_THEMES = CURATED_THEMES_LIST
        self.KNOWN_DARK_THEMES = KNOWN_DARK_THEMES

        try:
            self.chatbot_instance = Chatbot(self.assignment_manager, self.study_tips_generator)
        except Exception as e:
            print(f"Failed to initialize Chatbot in App: {e}")
            self.chatbot_instance = None
            messagebox.showerror("Chatbot Initialization Error",
                                 f"The Chatbot could not be initialized: {e}\r\n"
                                 "Chat functionality will be limited.")
        
        self.notebook = None
        # References to tab instances for potential cross-tab communication or refresh
        self.dashboard_tab_instance = None
        self.assignments_tab_instance = None
        self.statistics_tab_instance = None
        self.calendar_tab_instance = None
        self.chatbot_tab_instance = None
        
        self._setup_styles()  # ttkbootstrap handles much of this via the Window's theme
        self._create_main_widgets()
        # self.apply_theme() # Initial theme is set by ttkbootstrap.Window in main.py
        self.refresh_themed_widgets()

    def _setup_styles(self):
        """Configures application's visual style. ttkbootstrap handles the base theme.
           Custom ttk.Style configurations can still be applied if needed for specific widgets
           not fully covered by the theme, or for custom named styles.
        """
        self.style = self.root.style # Get the style object from the ttkbootstrap Window

        try:
            self.style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'))
        except AttributeError as e:
            if 'object has no attribute \'theme\'' in str(e):
                print("WARNING: Failed to configure 'Header.TLabel' due to a ttkbootstrap style issue "
                      "(possibly related to Python version or theme initialization). "
                      "The 'Header.TLabel' style will not be applied.")
                print(f"         Details: {e}")
            else:
                raise # Re-raise if it's a different AttributeError
        except tk.TclError as e: # Catch TclErrors too if styling fails at that level
            print(f"WARNING: TclError configuring 'Header.TLabel': {e}. Style may not be applied.")
        
        # Treeview.Heading font might be well-handled by ttkbootstrap themes.
        # Check appearance before re-adding:
        self.style.configure("TNotebook.Tab", font=('Helvetica', 10, 'normal'), padding=[5,2])

        # Accent colors: ttkbootstrap themes have primary, secondary, success, info, warning, danger colors.
        
        self.style.configure("TButton", padding=5)

        self.app_theme_settings = {
            "date_entry_style": { # For tkcalendar DateEntry
                "selectbackground": self.style.colors.primary if hasattr(self.style, 'colors') else "#0078D4",
                "selectforeground": "white", # Assuming primary is dark enough for white text
            },
            "entry_bg": self.style.colors.get('inputbg') if hasattr(self.style, 'colors') else "white",
            "entry_fg": self.style.colors.get('inputfg') if hasattr(self.style, 'colors') else "black"
        }

    def is_dark_theme(self):
        """Checks if the current theme is considered dark."""
        current_theme_name = self.settings.get("theme", "litera") # Default to a light theme
        return current_theme_name in self.KNOWN_DARK_THEMES

    def get_current_theme_settings(self):
        """Returns theme settings, primarily for dialogs or custom widgets like tk.Text."""
        # With ttkbootstrap, many widget colors are derived from the theme's color palette.
        is_dark = self.is_dark_theme()
        
        # Attempt to get colors directly from ttkbootstrap style
        try:
            entry_bg = self.root.style.colors.get('inputbg')
            entry_fg = self.root.style.colors.get('inputfg')
            select_bg = self.root.style.colors.primary
            # Determine select_fg based on perceived brightness of primary
            # This is a simple heuristic; proper contrast calculation is complex.
            r, g, b = self.root.winfo_rgb(select_bg)
            brightness = (r * 299 + g * 587 + b * 114) / 1000 / 255 # Normalize to 0-1 range approx
            select_fg = "white" if brightness < 0.5 else "black"

        except (AttributeError, tk.TclError): # Fallback if colors object isn't there or theme not fully loaded
            entry_bg = "#2B2B2B" if is_dark else "white"
            entry_fg = "white" if is_dark else "black"
            select_bg = "#0078D4" # Default blue
            select_fg = "white"
            
        return {
            "date_entry_style": { # For tkcalendar DateEntry
                "selectbackground": select_bg,
                "selectforeground": select_fg,
            },
            "entry_bg": entry_bg, # For tk.Text or custom entry-like widgets
            "entry_fg": entry_fg
        }

    def _create_main_widgets(self):
        """Creates and packs the main UI components like the notebook for tabs."""
        self.notebook = ttk.Notebook(self.root)
        
        assignments_provider = self.assignment_manager.get_assignments

        app_callbacks = {
            'edit_assignment': self.handle_edit_assignment_request,
            'add_assignment': self.handle_add_assignment_request,
            'delete_assignment': self.handle_delete_assignment_request,
            'set_completion_status': self.handle_set_completion_status_request,
            'refresh_all_tabs': self.refresh_all_tabs,
            'get_theme_settings': self.get_current_theme_settings, # Crucial for dialogs/custom tk widgets
            'get_master_app': lambda: self,
            'get_date_format_template_name': lambda: self.settings.get('date_format_template_name', 'default')
        }

        self.dashboard_tab_instance = DashboardTab(self.notebook, assignments_provider, app_callbacks)
        self.notebook.add(self.dashboard_tab_instance, text='Dashboard')

        self.assignments_tab_instance = AssignmentsTab(self.notebook, assignments_provider, app_callbacks)
        self.notebook.add(self.assignments_tab_instance, text='Assignments')

        self.statistics_tab_instance = StatisticsTab(self.notebook, assignments_provider, app_callbacks) 
        self.notebook.add(self.statistics_tab_instance, text='Statistics')
        
        self.calendar_tab_instance = CalendarTab(self.notebook, assignments_provider, app_callbacks)
        self.notebook.add(self.calendar_tab_instance, text='Calendar')

        self.chatbot_tab_instance = ChatbotTab(
            self.notebook,
            self, 
            self.chatbot_instance, 
            self.assignment_manager,
            self.study_tips_generator
        ) 
        self.notebook.add(self.chatbot_tab_instance, text='Chatbot')
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

    def change_theme(self, theme_name_or_label):
        """Changes the application theme using ttkbootstrap and saves the setting."""
        actual_theme_name = theme_name_or_label
        # Extract actual theme name if a label like "Dark - Darkly" is passed
        for label, name in self.CURATED_THEMES:
            if label == theme_name_or_label:
                actual_theme_name = name
                break
        
        try:
            # ttkbootstrap uses the style object from the root window
            self.root.style.theme_use(actual_theme_name)
            self.settings["theme"] = actual_theme_name
            save_app_settings(self.settings)
            print(f"Theme changed to: {actual_theme_name} using ttkbootstrap.")
            
            # Crucially, update styles that might depend on the new theme's color palette
            self._setup_styles() # Re-run to pick up new self.style.colors if they changed
            self.refresh_themed_widgets()

        except tk.TclError as e:
            messagebox.showerror("Theme Error", f"Could not apply ttkbootstrap theme '{actual_theme_name}': {e}", parent=self.root)
            previous_theme = self.settings.get("theme", "litera") # Default to a light theme
            try:
                self.root.style.theme_use(previous_theme)
            except tk.TclError:
                 self.root.style.theme_use("litera") # Fallback ttkbootstrap theme
                 self.settings["theme"] = "litera"
                 save_app_settings(self.settings)
            # Ensure styles and widgets are refreshed even on fallback
            self._setup_styles()
            self.refresh_themed_widgets()

    def refresh_themed_widgets(self):
        """Calls on_theme_changed on tabs to refresh widgets that need manual theme updates."""
        is_dark = self.is_dark_theme()

        # Update app_theme_settings before tabs query it
        current_settings = self.get_current_theme_settings()
        self.app_theme_settings.update(current_settings)
        
        for tab_instance in [
            self.dashboard_tab_instance, 
            self.assignments_tab_instance, 
            self.statistics_tab_instance, 
            self.calendar_tab_instance, 
            self.chatbot_tab_instance
        ]:
            if tab_instance:
                if hasattr(tab_instance, 'on_theme_changed'):
                    try:
                        tab_instance.on_theme_changed(is_dark)
                    except Exception as e:
                        print(f"Error calling on_theme_changed for {type(tab_instance).__name__}: {e}")
                # Fallback refresh if on_theme_changed not present or for data sync
                elif hasattr(tab_instance, 'refresh_data'):
                    if isinstance(tab_instance, StatisticsTab) and hasattr(tab_instance, 'refresh_charts'):
                        tab_instance.refresh_charts()
                    else:
                        tab_instance.refresh_data()
                elif hasattr(tab_instance, 'update_assignments_list'): # For AssignmentsTab
                     tab_instance.update_assignments_list()

    # Callback Handlers for Tabs
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
    
    def handle_set_completion_status_request(self, assignment_obj, status: bool):
        """Handles request to set completion status. Expects assignment_obj with 'id' and desired status."""
        assignment_id = assignment_obj.get('id')
        if not assignment_id:
            messagebox.showerror("Error", "Cannot update completion: ID missing.", parent=self.root)
            return

        success, message = self.assignment_manager.set_completion_status(assignment_id, status)
        if success:
            # More specific message if no change was made by the manager
            if "already marked" not in message:
                # Simple success, no specific message, refresh will show.
                pass 
            else:
                # Inform user if no actual change occurred (e.g. already complete)
                messagebox.showinfo("Status", message, parent=self.root)
        else:
            err_msg = message if message else "Failed to update completion status."
            messagebox.showerror("Error", err_msg, parent=self.root)
        self.refresh_all_tabs() # Always refresh

    def refresh_all_tabs(self):
        """Calls a data refresh method on each tab instance if it exists."""
        # This method is primarily for data refresh, not theme refresh.
        # Theme refresh is handled by refresh_themed_widgets calling on_theme_changed.

        if self.statistics_tab_instance and hasattr(self.statistics_tab_instance, 'refresh_charts'):
            self.statistics_tab_instance.refresh_charts()
        
        if self.dashboard_tab_instance and hasattr(self.dashboard_tab_instance, 'refresh_data'):
            self.dashboard_tab_instance.refresh_data()
        if self.assignments_tab_instance and hasattr(self.assignments_tab_instance, 'update_assignments_list'):
            self.assignments_tab_instance.update_assignments_list() 
        if self.calendar_tab_instance and hasattr(self.calendar_tab_instance, 'refresh_data'):
            self.calendar_tab_instance.refresh_data()

    def run(self):
        """Starts the Tkinter main event loop."""
        self.root.mainloop()
