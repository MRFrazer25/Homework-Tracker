import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import matplotlib.dates as mdates # Moved import here
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# from ...utils.helpers import format_date # If needed
from datetime import datetime, timedelta # Added timedelta for sample data

class StatisticsTab(ttk.Frame):
    """Tab for displaying various statistical charts about assignments."""
    def __init__(self, parent, assignments_data_provider):
        """
        Initializes the Statistics tab.

        Args:
            parent: The parent widget (notebook).
            assignments_data_provider: Callable to get the list of assignments.
                                       This is expected to be a list of assignment dicts.
        """
        super().__init__(parent)
        # Store the assignments data directly if it's a list, or the provider if it's a callable
        self.assignments_data_source = assignments_data_provider
        
        self.fig = None
        self.canvas = None
        self.ax_priority = None
        self.ax_category = None
        self.ax_difficulty = None
        self.ax_timeline = None
        
        self.charts_container_frame = ttk.Frame(self) # Parent for canvas OR no_data_label
        self.charts_container_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.no_data_label = None # Will be created in setup_charts_ui

        self.setup_charts_ui() # Creates canvas and no_data_label
        self.refresh_charts()  # Initial data load and display logic

    def get_assignments(self):
        """Fetches assignments from the data source."""
        if callable(self.assignments_data_source):
            return self.assignments_data_source()
        return self.assignments_data_source # If it's already a list

    def setup_charts_ui(self):
        """Sets up the Matplotlib Figure, Axes, Canvas, and 'no data' label.
           This is called once during initialization.
        """
        # Create the Matplotlib figure and axes
        self.fig = plt.Figure(figsize=(10, 8), dpi=100)
        self.ax_priority = self.fig.add_subplot(221)
        self.ax_category = self.fig.add_subplot(222)
        self.ax_difficulty = self.fig.add_subplot(223)
        self.ax_timeline = self.fig.add_subplot(224)
        
        # Create the TkAgg canvas and pack it (it will be managed by pack_forget/pack later)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.charts_container_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        # Initially pack it, refresh_charts will manage visibility
        self.canvas_widget.pack(fill='both', expand=True) 

        # Create the "no data" label (initially hidden or not packed)
        self.no_data_label = ttk.Label(
            self.charts_container_frame,
            text="No assignments to analyze for statistics.",
            style='Header.TLabel' # Assuming Header.TLabel is defined in app.py
        )
        # Do not pack no_data_label here; refresh_charts will manage it.

    def refresh_charts(self):
        """Clears and redraws all charts with current assignment data, or shows 'no data' message."""
        if not self.fig or not self.canvas: # Ensure UI is set up
            print("Warning: Charts UI not ready for refresh.")
            return

        current_assignments = self.get_assignments()

        if not current_assignments:
            self.canvas_widget.pack_forget() # Hide canvas
            if not self.no_data_label.winfo_ismapped(): # Show "no data" label if not already visible
                 self.no_data_label.pack(pady=20, padx=20, anchor='center', expand=True, fill='both')
            return
        
        # Data exists, ensure canvas is visible and "no data" label is hidden
        if self.no_data_label.winfo_ismapped():
            self.no_data_label.pack_forget()
        if not self.canvas_widget.winfo_ismapped():
            self.canvas_widget.pack(fill='both', expand=True)

        # Clear previous plot content from each axis
        self.ax_priority.clear()
        self.ax_category.clear()
        self.ax_difficulty.clear()
        self.ax_timeline.clear()

        # Recreate charts with new data
        self._create_priority_chart(self.ax_priority, current_assignments)
        self._create_category_chart(self.ax_category, current_assignments)
        self._create_difficulty_chart(self.ax_difficulty, current_assignments)
        self._create_timeline_chart(self.ax_timeline, current_assignments)
        
        self.fig.tight_layout() # Adjust layout to prevent overlap
        self.canvas.draw()      # Redraw the canvas

    def _create_priority_chart(self, ax, assignments):
        """Creates a pie chart of assignment priorities."""
        priority_counts = {"High": 0, "Medium": 0, "Low": 0, "Other": 0}
        for a in assignments:
            p = a.get('priority', 'Other')
            if p in priority_counts:
                priority_counts[p] += 1
            else: # Handle unexpected priority values
                priority_counts["Other"] += 1
        
        # Filter out priorities with zero count
        active_priorities = {k: v for k, v in priority_counts.items() if v > 0}
        
        if not active_priorities: # If all counts are zero
             ax.text(0.5, 0.5, "No priority data", ha='center', va='center', transform=ax.transAxes)
             ax.set_title('Assignments by Priority') # Still set title
             return # Return early if no data to plot

        labels = list(active_priorities.keys())
        values = list(active_priorities.values())
        
        # Updated vibrant colors
        colors_map = {'High': '#FF6347', 'Medium': '#FFA500', 'Low': '#32CD32', 'Other': '#778899'} # Tomato, Orange, LimeGreen, LightSlateGray
        pie_colors = [colors_map.get(label, '#778899') for label in labels]

        ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            colors=pie_colors
        )
        ax.set_title('Assignments by Priority')
        
    def _create_category_chart(self, ax, assignments):
        """Creates a bar chart of assignment categories (using 'class' as category)."""
        category_counts = {}
        for a in assignments:
            # Using 'class' field as 'category' as per other tabs
            category = a.get('class', 'Uncategorized') 
            category_counts[category] = category_counts.get(category, 0) + 1
        
        if not category_counts:
            ax.text(0.5, 0.5, "No category data", ha='center', va='center', transform=ax.transAxes)
        else:
            ax.bar(list(category_counts.keys()), list(category_counts.values()), color='#FFD700') # Gold bars
        ax.set_title('Assignments by Subject/Class')
        ax.tick_params(axis='x', labelrotation=45) # Simpler rotation
        # Ensure labels fit if many categories
        if len(category_counts) > 5:
             self.fig.subplots_adjust(bottom=0.2) # Adjust bottom margin if many x-labels

    def _create_difficulty_chart(self, ax, assignments):
        """Creates a histogram of assignment difficulties."""
        difficulties = [a.get('difficulty') for a in assignments if a.get('difficulty') is not None]
        if not difficulties:
            ax.text(0.5, 0.5, "No difficulty data", ha='center', va='center', transform=ax.transAxes)
        else:
            ax.hist(difficulties, bins=10, range=(0.5, 10.5), edgecolor='darkgrey', color='#3CB371') # MediumSeaGreen bars
        ax.set_title('Difficulty Distribution')
        ax.set_xlabel('Difficulty Level (1-10)')
        ax.set_ylabel('Number of Assignments')
        ax.set_xticks(range(1, 11)) # Ensure ticks are at integer difficulty levels
        
    def _create_timeline_chart(self, ax, assignments):
        """Creates a scatter plot timeline of upcoming assignments."""
        upcoming = [a for a in assignments if not a.get('completed', False) and a.get('due_date')]
        
        if upcoming:
            dates = []
            for a in upcoming: # Ensure dates are datetime objects
                due_date = a['due_date']
                if isinstance(due_date, str):
                    try:
                        dates.append(datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S'))
                    except ValueError:
                        try:
                            dates.append(datetime.strptime(due_date, '%Y-%m-%d'))
                        except ValueError:
                            continue # Skip if unparseable
                elif isinstance(due_date, datetime):
                    dates.append(due_date)
                # else skip if not datetime or parsable string
            
            if not dates: # If all upcoming had unparseable dates
                ax.text(0.5, 0.5, "No valid upcoming dates", ha='center', va='center', transform=ax.transAxes)
            else:
                # Re-filter upcoming based on successfully parsed dates
                valid_upcoming = [a for a in upcoming if isinstance(a['due_date'], datetime) or (isinstance(a['due_date'], str) and any(isinstance(d, datetime) and (d.strftime('%Y-%m-%d %H:%M:%S') == a['due_date'] or d.strftime('%Y-%m-%d') == a['due_date']) for d in dates))]

                priorities = [a.get('priority', 'Other') for a in valid_upcoming]
                
                # Updated vibrant colors for timeline scatter
                color_map = {'High': '#FF6347', 'Medium': '#FFA500', 'Low': '#32CD32', 'Other': '#778899'} # Tomato, Orange, LimeGreen, LightSlateGray
                plot_colors = [color_map.get(p, '#778899') for p in priorities]
                
                ax.scatter(dates, [1] * len(dates), c=plot_colors, s=100, alpha=0.7)
            
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.tick_params(axis='x', labelrotation=45)
            self.fig.subplots_adjust(bottom=0.2) # Adjust for rotated labels
        else:
            ax.text(0.5, 0.5, "No upcoming assignments", ha='center', va='center', transform=ax.transAxes)
        
        ax.set_title('Assignment Timeline (Upcoming)')
        ax.set_xlabel('Due Date')
        ax.set_yticks([]) # Hide y-axis as it's not meaningful here


if __name__ == '__main__':
    # Example usage for testing this tab independently
    root = tk.Tk()
    root.title("Statistics Tab Test")
    
    # Sample assignments data for testing
    # datetime and timedelta are imported at the top of the file
    sample_assignments = [
        {'name': 'Math HW 1', 'priority': 'High', 'class': 'Math', 'difficulty': 7, 'due_date': datetime.now() + timedelta(days=2), 'completed': False},
        {'name': 'History Essay', 'priority': 'Medium', 'class': 'History', 'difficulty': 5, 'due_date': datetime.now() + timedelta(days=5), 'completed': False},
        {'name': 'Science Lab', 'priority': 'High', 'class': 'Science', 'difficulty': 8, 'due_date': datetime.now() + timedelta(days=1), 'completed': False},
        {'name': 'English Reading', 'priority': 'Low', 'class': 'English', 'difficulty': 3, 'due_date': datetime.now() + timedelta(days=10), 'completed': True}, # This one is completed
        {'name': 'CS Project', 'priority': 'High', 'class': 'CS', 'difficulty': 9, 'due_date': datetime.now() + timedelta(days=7), 'completed': False},
        {'name': 'Art Sketch', 'priority': 'Other', 'class': 'Art', 'difficulty': 2, 'due_date': datetime.now() + timedelta(days=3), 'completed': False}, # Test 'Other' priority
        {'name': 'Music Practice', 'priority': 'Medium', 'class': 'Music', 'difficulty': None, 'due_date': datetime.now() + timedelta(days=4), 'completed': False}, # Test missing difficulty
    ]

    # In the main app, assignments_data_provider is a callable.
    # For testing, we can pass the list directly or wrap it.
    def get_test_assignments():
        return sample_assignments

    tab = StatisticsTab(root, get_test_assignments) # Pass the callable
    tab.pack(expand=True, fill='both')
    root.mainloop()
