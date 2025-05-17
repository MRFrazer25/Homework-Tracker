import tkinter as tk
from tkinter import ttk
# from tkcalendar import Calendar # No longer using tkcalendar
import ttkbootstrap as ttkb # For DateEntry and other ttkbootstrap widgets
from ttkbootstrap.dialogs import DatePickerDialog # Though DateEntry uses it internally
from datetime import datetime, date # Ensure date is imported

# # from ...utils.helpers import format_date # If needed for displaying event details # Removed

class CalendarTab(ttk.Frame):
    """
    Tab displaying a DateEntry to select a date and a list of assignments for that date.
    """
    def __init__(self, parent, assignments_data_provider, app_callbacks):
        super().__init__(parent)
        self.assignments_provider = assignments_data_provider
        self.app_callbacks = app_callbacks
        self.app_instance = self.app_callbacks['get_master_app']()
        self.selected_date = date.today() # Store the currently selected date

        self.date_format_str = "%Y-%m-%d" # Define date format for parsing and display

        self._setup_ui()
        self.on_theme_changed(self.app_instance.is_dark_theme()) # Apply initial theme
        self.refresh_data()

    def _setup_ui(self):
        """Sets up the UI elements for the Calendar tab."""
        self.main_frame = ttk.Frame(self, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.update_idletasks() # Explicitly update main_frame's geometry

        # DateEntry for date selection
        self.date_entry = ttkb.DateEntry(
            self.main_frame,
            dateformat=self.date_format_str,
            firstweekday=0, # Monday: 0=Monday, ..., 6=Sunday (DateEntry default is 6)
            startdate=self.selected_date
        )
        self.date_entry.pack(pady=(0, 10), fill=tk.X, padx=0)

        self.date_entry.entry.bind("<<DateEntrySelected>>", self.on_date_selected)
        self.date_entry.entry.bind("<FocusOut>", self.on_date_selected)
        self.date_entry.entry.bind("<Return>", self.on_date_selected)

        # Frame for displaying events for the selected date
        self.info_frame = ttk.LabelFrame(self.main_frame, text="Assignments for Selected Date", padding=10)
        self.info_frame.pack(pady=10, padx=0, fill="both", expand=True)

        self.event_listbox = tk.Listbox(
            self.info_frame,
            height=10,
            # Font and colors will be set in on_theme_changed
        )
        self.event_listbox_scrollbar = ttk.Scrollbar(
            self.info_frame,
            orient=tk.VERTICAL,
            command=self.event_listbox.yview
        )
        self.event_listbox.configure(yscrollcommand=self.event_listbox_scrollbar.set)
        self.event_listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.event_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        self.error_label = None # Placeholder for other errors if needed


    def on_date_selected(self, event=None):
        """
        Called when a date is selected in the DateEntry or entry loses focus/enter pressed.
        Updates the event listbox with assignments for the new date.
        """
        try:
            date_str = self.date_entry.entry.get()
            if not date_str:
                self.selected_date = date.today() 
            else:
                self.selected_date = datetime.strptime(date_str, self.date_format_str).date()
            
        except ValueError:
            print(f"Invalid date format in DateEntry: {self.date_entry.entry.get()}. Using last valid date: {self.selected_date}")
            # Update entry to show the last valid date to prevent user confusion
            if self.selected_date:
                self.date_entry.entry.delete(0, tk.END)
                self.date_entry.entry.insert(0, self.selected_date.strftime(self.date_format_str))
            self._update_event_list_for_selected_date() 
            return

        if hasattr(self.info_frame, 'config'): 
             self.info_frame.config(text=f"Assignments for {self.selected_date.strftime('%A, %B %d, %Y')}")
        self._update_event_list_for_selected_date()

    def _update_event_list_for_selected_date(self):
        """Updates the event listbox with assignments due on the self.selected_date."""
        if not hasattr(self, 'event_listbox') or not self.event_listbox.winfo_exists():
            return 

        self.event_listbox.delete(0, tk.END)
        assignments = self.assignments_provider()
        
        found_assignments = False
        if assignments and self.selected_date:
            for assignment in assignments:
                try:
                    due_date_val = assignment.get('due_date')
                    if not due_date_val:
                        continue

                    if isinstance(due_date_val, datetime):
                        due_date = due_date_val.date()
                    elif isinstance(due_date_val, date):
                        due_date = due_date_val
                    elif isinstance(due_date_val, str):
                        due_date = datetime.strptime(due_date_val, '%Y-%m-%d').date()
                    else:
                        print(f"Warning: Due date for assignment '{assignment.get('title', 'Unknown')}' has an unexpected type: {type(due_date_val)}")
                        continue

                    if due_date == self.selected_date:
                        status = "Complete" if assignment.get('completed', False) else "Incomplete"
                        assignment_name = assignment.get('name', 'N/A') 
                        priority_val = assignment.get('priority', 'N/A')
                        class_name = assignment.get('class', 'N/A')
                        display_text = (
                            f"{assignment_name} (Class: {class_name}) - Priority: {priority_val} "
                            f"- Status: {status}"
                        )
                        self.event_listbox.insert(tk.END, display_text)
                        found_assignments = True
                except ValueError:
                    print(f"Warning: Could not parse due_date string '{due_date_val}' for assignment '{assignment.get('title', 'Unknown')}'. Ensure format is YYYY-MM-DD.")
                    continue 
        
        if not found_assignments:
            self.event_listbox.insert(tk.END, "No assignments due on this date.")

    def refresh_data(self):
        """Refreshes the displayed assignment data for the currently selected date."""
        self.on_date_selected()

    def on_theme_changed(self, is_dark_theme):
        """Handles theme changes for the Calendar tab."""
        if not hasattr(self, 'main_frame') or not self.main_frame.winfo_exists():
            return

        bs_colors = self.app_instance.root.style.colors
        
        list_bg = bs_colors.get('inputbg')
        if list_bg is None: list_bg = '#3C3C3C' if is_dark_theme else 'white'
        
        list_fg = bs_colors.get('inputfg')
        if list_fg is None: list_fg = 'white' if is_dark_theme else 'black'

        select_bg = bs_colors.get('primary')
        if select_bg is None: select_bg = '#0078D7'
        
        select_fg = bs_colors.get('selectfg') 
        if select_fg is None: select_fg = bs_colors.get('inputfg') 
        if select_fg is None: select_fg = 'white' if is_dark_theme else 'black'

        if hasattr(self, 'event_listbox') and self.event_listbox:
            self.event_listbox.configure(
                background=list_bg,
                foreground=list_fg,
                selectbackground=select_bg,
                selectforeground=select_fg, 
                font=("Segoe UI", 10) 
            )

        if self.error_label and self.error_label.winfo_exists():
            err_fg = bs_colors.get('danger') or ('#FF5555' if is_dark_theme else '#CC0000')
            self.error_label.configure(
                background=bs_colors.get('bg'), 
                foreground=err_fg
            )

# if __name__ == '__main__':
#     # Example usage for testing this tab independently
#     # This __main__ block needs to be updated if used, as MockApp and ttkbootstrap aren't fully set up here.
#     # For instance, ttkbootstrap.Style() would be needed for a ThemedTk equivalent.
#     root = tk.Tk() # Basic Tk root for simple testing
#     root.title("Calendar Tab Test")
#     try:
#         from ttkbootstrap import Style
#         Style(theme='litera') # Apply a theme for ttk widgets
#     except ImportError:
#         print("ttkbootstrap not found for independent test styling.")


#     # Sample assignments data for testing
#     sample_assignments = [
#         {'title': 'Math HW', 'class': 'Math', 'priority': 'High', 'due_date': datetime.now().date() + timedelta(days=2), 'completed': False},
#         {'title': 'History Reading', 'class': 'History', 'priority': 'Medium', 'due_date': datetime.now().date() + timedelta(days=2), 'completed': False},
#         {'title': 'Science Project', 'class': 'Science', 'priority': 'Low', 'due_date': datetime.now().date() + timedelta(days=5), 'completed': True},
#         {'title': 'Art Sketch', 'class': 'Art', 'priority': 'DefaultTest', 'due_date': datetime.now().date() + timedelta(days=1), 'completed': False},
#     ]

#     def get_sample_assignments():
#         return sample_assignments

#     class MockAppForCalendar: # Simpler mock, focusing on what CalendarTab needs
#         def __init__(self, tk_root):
#             self.root = tk_root
#             self._is_dark = False
#             if hasattr(tk_root, 'style'): # If using ttkbootstrap.Window
#                 self._is_dark = "dark" in tk_root.style.theme_use().lower()

#         def is_dark_theme(self):
#             if hasattr(self.root, 'style'):
#                  self._is_dark = "dark" in self.root.style.theme_use().lower()
#             return self._is_dark
        
#         def get_master_app(self): 
#             return self

#     mock_app_instance = MockAppForCalendar(root)
#     app_cbs = { 
#         'get_master_app': mock_app_instance.get_master_app
#     }
    
#     tab = CalendarTab(root, get_sample_assignments, app_cbs)
#     tab.pack(expand=True, fill='both')
    
#     # Example: Add a button to toggle theme for testing (if root is a ttkbootstrap.Window)
#     if hasattr(root, "style"):
#         def toggle_theme_test():
#             current_theme = root.style.theme_use()
#             if "dark" in current_theme or "cyborg" in current_theme : # Example dark themes
#                 root.style.theme_use("litera")
#             else:
#                 root.style.theme_use("cyborg")
#             # Manually trigger on_theme_changed for the tab after theme switch
#             if hasattr(tab, 'on_theme_changed') and hasattr(mock_app_instance, 'is_dark_theme'):
#                 tab.on_theme_changed(mock_app_instance.is_dark_theme())
#             tab.refresh_data()


#         theme_button = ttk.Button(root, text="Toggle Theme (Test)", command=toggle_theme_test)
#         theme_button.pack(pady=5)

#     root.mainloop()
