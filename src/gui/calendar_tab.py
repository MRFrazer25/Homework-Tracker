import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar # Ensure tkcalendar is installed
from datetime import datetime, timedelta
# from ...utils.helpers import format_date # If needed for displaying event details

class CalendarTab(ttk.Frame):
    """
    Tab displaying a calendar view with assignments marked on due dates.
    
    Initializes the Calendar tab.
    Args:
        parent: The parent widget (notebook).
        assignments_data_provider: Callable to get the list of assignments.
        app_callbacks: Dictionary of callbacks to the main application.
    """
    def __init__(self, parent, assignments_data_provider, app_callbacks):
        super().__init__(parent)
        self.assignments_provider = assignments_data_provider
        self.app_callbacks = app_callbacks # e.g., for showing assignment details on date select
        
        self.calendar = None
        self.selected_date_label = None
        self.assignments_on_date_listbox = None # Using tk.Listbox for simplicity

        self.setup_ui()
        self.mark_due_dates()

    def setup_ui(self):
        """Creates and lays out the UI elements for the Calendar tab."""
        # Calendar widget from tkcalendar library
        self.calendar = Calendar(
            self, 
            selectmode='day', 
            date_pattern='yyyy-mm-dd', # Format for get_date()
            # Default year/month/day is current, which is usually desired.
            # Example: Set specific start date
            # year=2023, month=1, day=1 
        )
        self.calendar.pack(pady=10, padx=10, fill="x")
        self.calendar.bind("<<CalendarSelected>>", self.on_date_selected) # Event when a date is clicked

        # Frame for displaying information about the selected date
        info_frame = ttk.LabelFrame(self, text="Assignments on Selected Date")
        info_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.selected_date_label = ttk.Label(info_frame, text="Select a date to see assignments.")
        self.selected_date_label.pack(pady=5)
        
        # Listbox to show assignments for the selected date
        self.assignments_on_date_listbox = tk.Listbox(info_frame, height=10)
        self.assignments_on_date_listbox.pack(pady=5, padx=5, fill="both", expand=True)
        # Future enhancement: Bind double-click on listbox item to show details or edit.

    def mark_due_dates(self):
        """Marks assignment due dates on the calendar."""
        if not self.calendar:
            return
            
        # Clear all previously marked events to prevent duplicates on refresh
        self.calendar.calevent_remove('all') 

        assignments = self.assignments_provider()
        for assignment in assignments:
            if not assignment.get('completed', False) and assignment.get('due_date'):
                due_date = assignment['due_date']
                # Ensure due_date is a datetime.date or datetime.datetime object
                if not hasattr(due_date, 'year'): # Simple check if it's not date/datetime like
                    try: # Attempt to parse if it's a string
                        due_date = datetime.strptime(str(due_date), '%Y-%m-%d %H:%M:%S').date()
                    except ValueError:
                        try:
                            due_date = datetime.strptime(str(due_date), '%Y-%m-%d').date()
                        except ValueError:
                            print(f"Warning: Could not parse due_date for assignment '{assignment.get('name')}': {due_date}")
                            continue # Skip marking this assignment
                
                event_text = f"{assignment['name']} ({assignment.get('priority', 'N/A')})"
                # Use priority as a tag for styling; convert to lowercase for consistency
                tag = str(assignment.get('priority', 'default')).lower()
                self.calendar.calevent_create(due_date, event_text, tags=tag)
        
        # Configure styles for event tags (priority based) - Updated vibrant colors
        self.calendar.tag_config('high', background='#FF6347', foreground='white') # Tomato, white text
        self.calendar.tag_config('medium', background='#FFA500', foreground='black') # Orange, black text
        self.calendar.tag_config('low', background='#32CD32', foreground='black')    # LimeGreen, black text
        self.calendar.tag_config('default', background='#778899', foreground='white') # LightSlateGray, white text

    def on_date_selected(self, event=None):
        """Handles the event when a date is selected on the calendar."""
        if not self.calendar: # Should not happen if UI is set up
            return

        try:
            selected_date_str = self.calendar.get_date()
            # Convert string date from calendar to a datetime.date object
            selected_date_obj = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except Exception as e:
            print(f"Error parsing selected date: {e}")
            self.selected_date_label.config(text="Error: Could not parse selected date.")
            self.assignments_on_date_listbox.delete(0, tk.END)
            return
        
        self.selected_date_label.config(text=f"Assignments due on: {selected_date_obj.strftime('%A, %B %d, %Y')}")
        
        self.assignments_on_date_listbox.delete(0, tk.END) # Clear previous entries
        
        assignments = self.assignments_provider()
        found_assignments_on_date = False
        for assignment in assignments:
            assignment_due_date = assignment.get('due_date')
            if not assignment_due_date:
                continue

            # Ensure assignment_due_date is a date object for comparison
            if hasattr(assignment_due_date, 'date'): # If it's a datetime object
                compare_date = assignment_due_date.date()
            elif isinstance(assignment_due_date, datetime.date): # If it's already a date object
                compare_date = assignment_due_date
            else: # Try to parse if it's a string or other type
                try:
                    compare_date = datetime.strptime(str(assignment_due_date), '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    try:
                        compare_date = datetime.strptime(str(assignment_due_date), '%Y-%m-%d').date()
                    except ValueError:
                        continue # Skip if date is unparseable

            if compare_date == selected_date_obj:
                display_text = f"{assignment.get('name', 'N/A')} ({assignment.get('class', 'N/A')}) - P: {assignment.get('priority', 'N/A')}"
                if assignment.get('completed', False):
                    display_text += " (Completed)"
                self.assignments_on_date_listbox.insert(tk.END, display_text)
                found_assignments_on_date = True
        
        if not found_assignments_on_date:
            self.assignments_on_date_listbox.insert(tk.END, "No assignments due on this date.")

    def refresh_data(self):
        """Reloads and re-marks assignments on the calendar and updates selected date info."""
        self.mark_due_dates()
        # Re-trigger on_date_selected to update the listbox for the currently selected date (if any)
        # This ensures the listbox reflects changes even if the selected date itself hasn't changed.
        if self.calendar and self.calendar.selection_get() is not None: # Check if a date is selected
            self.on_date_selected() 
        else: # If no date is selected, clear the listbox and reset label
            if self.selected_date_label:
                self.selected_date_label.config(text="Select a date to see assignments.")
            if self.assignments_on_date_listbox:
                 self.assignments_on_date_listbox.delete(0, tk.END)


if __name__ == '__main__':
    # Example usage for testing this tab independently
    root = tk.Tk()
    root.title("Calendar Tab Test")

    # Sample assignments data for testing
    # datetime and timedelta are imported at the top of the file
    sample_assignments = [
        {'name': 'Math HW', 'class': 'Math', 'priority': 'High', 'due_date': datetime.now() + timedelta(days=2), 'completed': False},
        {'name': 'History Reading', 'class': 'History', 'priority': 'Medium', 'due_date': datetime.now() + timedelta(days=2), 'completed': False},
        {'name': 'Science Project', 'class': 'Science', 'priority': 'Low', 'due_date': datetime.now() + timedelta(days=5), 'completed': True},
        {'name': 'Art Sketch', 'class': 'Art', 'priority': 'DefaultTest', 'due_date': datetime.now() + timedelta(days=1), 'completed': False}, # Test default tag
    ]
    # Removed redundant import of datetime, timedelta from here.

    def get_sample_assignments():
        return sample_assignments

    app_cbs = {} 
    
    tab = CalendarTab(root, get_sample_assignments, app_cbs)
    tab.pack(expand=True, fill='both')
    root.mainloop()
