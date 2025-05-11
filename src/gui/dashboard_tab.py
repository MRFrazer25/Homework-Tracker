import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta # If needed for summaries
from src.utils.helpers import get_priority_color # Import the helper

class DashboardTab(ttk.Frame):
    """Tab for displaying a dashboard overview, including upcoming assignments."""
    def __init__(self, parent, assignments_data_provider, app_callbacks):
        """
        Initializes the Dashboard tab.
        
        Args:
            parent: The parent widget (notebook).
            assignments_data_provider: Callable to get the list of assignments.
            app_callbacks: Dictionary of callbacks to the main application (not used by this tab yet).
        """
        super().__init__(parent)
        self.assignments_provider = assignments_data_provider
        self.app_callbacks = app_callbacks # Currently unused by this tab but kept for consistency
        
        self.summary_frame = None # Frame to hold the upcoming assignments list for easy refresh
        self.top_frame = None     # Main container frame for this tab's content

        self.setup_ui()
        self.refresh_data() # Populate initial data

    def _build_summary_frame(self, parent_frame):
        """Creates or recreates the frame displaying upcoming assignments."""
        if self.summary_frame:
            self.summary_frame.destroy() # Clear previous summary if refreshing
        
        self.summary_frame = ttk.Frame(parent_frame)
        self.summary_frame.pack(fill='x', expand=True, pady=5)
        
        assignments = self.assignments_provider()
        today = datetime.now().date() # Use .now().date() for today
        
        # Filter for active assignments due in the next 7 days
        upcoming_assignments_next_7_days = []
        if assignments:
            for i in range(7): # For today + next 6 days
                current_day = today + timedelta(days=i)
                assignments_for_day = [
                    a for a in assignments 
                    if not a.get('completed', False) and 
                       a.get('due_date') and isinstance(a.get('due_date'), datetime) and
                       a.get('due_date').date() == current_day
                ]
                if assignments_for_day:
                    # Sort assignments for the day by priority (optional, but good for consistency)
                    priority_map = {'High': 3, 'Medium': 2, 'Low': 1}
                    assignments_for_day.sort(key=lambda x: priority_map.get(x.get('priority', 'Low'), 0), reverse=True)
                    upcoming_assignments_next_7_days.append({'date': current_day, 'tasks': assignments_for_day})

        if not upcoming_assignments_next_7_days:
            ttk.Label(self.summary_frame, text="No upcoming assignments in the next 7 days.", foreground="#708090").pack(anchor='center', padx=10, pady=20)
            return

        for day_info in upcoming_assignments_next_7_days:
            day_date = day_info['date']
            tasks = day_info['tasks']
            day_name = day_date.strftime('%A') # Full day name
            if day_date == today:
                day_name = "Today"
            elif day_date == today + timedelta(days=1):
                day_name = "Tomorrow"

            frame_title = f"Due {day_name} ({day_date.strftime('%Y-%m-%d')}) - {len(tasks)} assignment(s)"
            day_frame = ttk.LabelFrame(self.summary_frame, text=frame_title)
            day_frame.pack(fill='x', expand=True, padx=5, pady=(5,2)) # Small bottom padding for frame

            for assignment in tasks:
                # Determine foreground color based on priority for visual cue
                priority = assignment.get('priority', 'Low')
                p_color = get_priority_color(priority) # Use helper function
                
                display_text = f"- {assignment.get('name', 'N/A')} ({assignment.get('class', 'N/A')})"
                ttk.Label(day_frame, text=display_text, foreground=p_color).pack(anchor='w', padx=10, pady=1)


    def setup_ui(self):
        """Creates and lays out the main UI elements for the Dashboard tab."""
        self.top_frame = ttk.Frame(self) 
        self.top_frame.pack(fill='x', padx=10, pady=5, side=tk.TOP, anchor='n') 

        # Dashboard Overview Title
        title_label = ttk.Label(
            self.top_frame,
            text="Dashboard Overview", 
            style="Header.TLabel" 
        )
        title_label.pack(pady=(0,5), anchor='nw') 

        # Separator line
        separator = ttk.Separator(self.top_frame, orient='horizontal')
        separator.pack(fill='x', pady=(0, 5)) # pady adds space below separator

        # The summary_frame (for upcoming assignments) will be built by refresh_data()
        # and packed into self.top_frame below the separator.
        # No quick add section here as per previous user request.

    def refresh_data(self):
        """
        Rebuilds the summary of upcoming assignments.
        Called on initialization and when data changes (via app's refresh_all_tabs).
        """
        if self.top_frame: # Ensure top_frame (parent for summary) exists
            self._build_summary_frame(self.top_frame)
            # print("DashboardTab: Summary frame refreshed.") # Debug print, can be removed
        else:
            # This case should ideally not be hit if setup_ui is called before refresh_data
            print("DashboardTab: Refresh skipped, top_frame not ready.")


if __name__ == '__main__':
    # Example usage for testing this tab independently
    root = tk.Tk()
    root.title("Dashboard Tab Test")

    # Apply a basic style for testing if Header.TLabel is used
    s = ttk.Style()
    s.configure('Header.TLabel', font=('Helvetica', 12, 'bold')) # Simpler header for test

    # Sample data and callbacks for testing
    # Ensure datetime and timedelta are available for sample_assignments
    from datetime import datetime, timedelta 
    sample_assignments = [
        {'name': 'Math HW Chapter 1', 'class': 'Math', 'due_date': datetime.now(), 'completed': False, 'priority': 'High'},
        {'name': 'History Reading Ch. 5', 'class': 'History', 'due_date': datetime.now() + timedelta(days=1), 'completed': False, 'priority': 'Medium'},
        {'name': 'Science Quiz Prep', 'class': 'Science', 'due_date': datetime.now() + timedelta(days=1), 'completed': True, 'priority': 'High'}, # Completed
        {'name': 'English Essay Draft', 'class': 'English', 'due_date': datetime.now() + timedelta(days=2), 'completed': False, 'priority': 'Medium'},
    ]
    # The top-level import of datetime, timedelta is sufficient.
    # Redundant import in test block can be removed if top-level is guaranteed.

    def get_sample_assignments():
        return sample_assignments

    app_cbs = {} # No specific callbacks needed for this simple dashboard yet
    
    tab = DashboardTab(root, get_sample_assignments, app_cbs)
    tab.pack(expand=True, fill='both')
    root.mainloop()
