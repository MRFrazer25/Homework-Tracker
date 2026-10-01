import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta # If needed for summaries
import tkinter.font as tkFont # ADDED IMPORT
from src.utils.helpers import get_priority_color, PRIORITY_RANK

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
        self.app_callbacks = app_callbacks
        self.master_app = app_callbacks.get('get_master_app')() # Expect app to provide this callback
        
        self.summary_frame = None # Frame to hold the upcoming assignments list for easy refresh
        self.top_frame = None     # Main container frame for this tab's content
        self.assignment_name_font = tkFont.Font(family="Helvetica", size=12, weight="normal") # ADDED FONT DEFINITION
        self.theme_var = tk.StringVar()

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
                    assignments_for_day.sort(key=lambda x: PRIORITY_RANK.get(x.get('priority'), 0), reverse=True)
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
                ttk.Label(day_frame, text=display_text, foreground=p_color, font=self.assignment_name_font).pack(anchor='w', padx=10, pady=1)


    def setup_ui(self):
        """Creates and lays out the main UI elements for the Dashboard tab."""
        self.top_frame = ttk.Frame(self) 
        self.top_frame.pack(fill='x', padx=10, pady=5, side=tk.TOP, anchor='n') 

        # Header Frame for Title and Theme Button
        header_controls_frame = ttk.Frame(self.top_frame)
        header_controls_frame.pack(fill='x', expand=True)

        title_label = ttk.Label(
            header_controls_frame,
            text="Dashboard Overview", 
            style="Header.TLabel" 
        )
        title_label.pack(side=tk.LEFT, pady=(0,5), anchor='nw') 

        # Theme selection Combobox
        if self.master_app and hasattr(self.master_app, 'CURATED_THEMES') and hasattr(self.master_app, 'settings'):
            theme_labels = [label for label, name in self.master_app.CURATED_THEMES]
            self.theme_combobox = ttk.Combobox(header_controls_frame, textvariable=self.theme_var, values=theme_labels, state="readonly", width=25)
            
            current_theme_name = self.master_app.settings.get("theme", "litera")
            current_theme_label = ""
            for label, name in self.master_app.CURATED_THEMES:
                if name == current_theme_name:
                    current_theme_label = label
                    break
            if not current_theme_label and theme_labels: # Fallback if current theme name not in labels (e.g. old settings file)
                current_theme_label = theme_labels[0] 
            
            self.theme_var.set(current_theme_label)
            self.theme_combobox.bind("<<ComboboxSelected>>", self._on_theme_selected)
            self.theme_combobox.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))
        else:
            ttk.Label(header_controls_frame, text="(Themes N/A)").pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        separator = ttk.Separator(self.top_frame, orient='horizontal')
        separator.pack(fill='x', pady=(0, 5), after=header_controls_frame)

        # The summary_frame (for upcoming assignments) will be built by refresh_data()
        # and packed into self.top_frame below the separator.
        # No quick add section here as per previous user request.

    def _on_theme_selected(self, event=None): # event is passed by bind
        selected_label = self.theme_var.get()
        if self.master_app and hasattr(self.master_app, 'change_theme'):
            self.master_app.change_theme(selected_label) # app.change_theme can handle labels
        else:
            messagebox.showerror("Error", "Cannot change theme.", parent=self.winfo_toplevel())

    def refresh_data(self):
        """
        Rebuilds the summary of upcoming assignments.
        Called on initialization and when data changes (via app's refresh_all_tabs).
        """
        if self.master_app and hasattr(self.master_app, 'settings') and hasattr(self.master_app, 'CURATED_THEMES') and hasattr(self, 'theme_combobox'):
            current_theme_name = self.master_app.settings.get("theme", "litera")
            current_theme_label = ""
            for label, name in self.master_app.CURATED_THEMES:
                if name == current_theme_name:
                    current_theme_label = label
                    break
            if current_theme_label and self.theme_var.get() != current_theme_label:
                self.theme_var.set(current_theme_label)
        
        if self.top_frame: # Ensure top_frame (parent for summary) exists
            self._build_summary_frame(self.top_frame)
        else:
            # This case should ideally not be hit if setup_ui is called before refresh_data
            print("DashboardTab: Refresh skipped, top_frame not ready.")