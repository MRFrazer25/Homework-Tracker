from tkinter import ttk
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta, date
from collections import Counter

# Default FALLBACK Matplotlib style parameters if ttkbootstrap colors are unavailable
LIGHT_MPL_STYLE_FALLBACK = {
    "figure.facecolor": "#F0F0F0",
    "axes.facecolor": "white",
    "axes.edgecolor": "black",
    "axes.labelcolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "text.color": "black",
    "patch.edgecolor": "black"
}

DARK_MPL_STYLE_FALLBACK = {
    "figure.facecolor": "#2E2E2E",
    "axes.facecolor": "#3C3C3C",
    "axes.edgecolor": "white",
    "axes.labelcolor": "white",
    "xtick.color": "white",
    "ytick.color": "white",
    "text.color": "white",
    "patch.edgecolor": "white"
}

class StatisticsTab(ttk.Frame):
    """Tab for displaying various statistical charts about assignments."""
    def __init__(self, parent, assignments_data_provider, app_callbacks):
        """
        Initializes the Statistics tab.

        Args:
            parent: The parent widget (notebook).
            assignments_data_provider: Callable to get the list of assignments.
            app_callbacks: Dictionary of callbacks to the main application,
                           including get_master_app.
        """
        super().__init__(parent)
        self.assignments_data_source = assignments_data_provider
        self.app_callbacks = app_callbacks
        self.app_instance = self.app_callbacks['get_master_app']() # type: ignore
        
        self.fig = None
        self.canvas = None
        self.ax_priority = None
        self.ax_category = None # This will be for 'Assignments by Class' or similar bar chart
        self.ax_difficulty = None
        self.ax_timeline = None

        # Initialize theme-related attributes to sensible defaults
        self.text_color = 'black'
        self.plot_bg_color = 'white'
        self.figure_bg_color = '#F0F0F0'
        self.grid_color = 'lightgrey'
        self.chart_font_size = 12
        self.axis_label_font_size = 10
        self.tick_label_font_size = 9
        
        self.charts_container_frame = ttk.Frame(self) # Parent for canvas OR no_data_label
        self.charts_container_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.no_data_label = None # Will be created in setup_charts_ui

        self.setup_charts_ui() # Creates canvas and no_data_label
        # Defer refresh_charts until after on_theme_changed is called once
        # to ensure plots are styled correctly on initial load.
        # self.refresh_charts() # Called by on_theme_changed
        
        # Initial theme setup
        self.after(10, self._initial_theme_setup)

    def _get_matplotlib_style(self, is_dark_theme):
        """Generates Matplotlib style dictionary based on ttkbootstrap theme colors."""
        # Determine fallback style first
        fallback_style = DARK_MPL_STYLE_FALLBACK if is_dark_theme else LIGHT_MPL_STYLE_FALLBACK

        try:
            bs_style = self.app_instance.root.style
            
            bg_color = bs_style.colors.get('bg') or fallback_style["figure.facecolor"]
            fg_color = bs_style.colors.get('fg') or fallback_style["text.color"]
            inputbg_color = bs_style.colors.get('inputbg') or fallback_style["axes.facecolor"] # Default axes to inputbg or its fallback
            
            axes_bg = inputbg_color 
            
            if bg_color == inputbg_color:
                if is_dark_theme:
                    try: 
                        r, g, b = self.app_instance.root.winfo_rgb(bg_color)
                        # Attempt to create a slightly lighter shade for axes_bg
                        # Ensure values are within 0-255 before formatting
                        r_ax = min(255, int(r / 256 * 1.15)) # Increase brightness a bit more (e.g. *1.15)
                        g_ax = min(255, int(g / 256 * 1.15))
                        b_ax = min(255, int(b / 256 * 1.15))
                        axes_bg_candidate = f"#{r_ax:02x}{g_ax:02x}{b_ax:02x}"
                        # Check if the new color is different enough, otherwise use fallback axes color
                        if axes_bg_candidate != bg_color: # Check if it actually changed
                           axes_bg = axes_bg_candidate
                        else: # if it's still same as bg_color (e.g. bg_color was already very light like #FFFFFF)
                           axes_bg = fallback_style["axes.facecolor"] # use specific fallback for axes
                    except:
                        axes_bg = fallback_style["axes.facecolor"]
                else:
                    axes_bg = "white" # Often white is best for light theme plot backgrounds
            
            return {
                "figure.facecolor": bg_color,
                "axes.facecolor": axes_bg, 
                "axes.edgecolor": fg_color,
                "axes.labelcolor": fg_color,
                "xtick.color": fg_color,
                "ytick.color": fg_color,
                "text.color": fg_color,
                "patch.edgecolor": fg_color
            }
        except Exception as e:
            return fallback_style

    def _initial_theme_setup(self):
        """Safely performs initial theme setup and chart refresh."""
        if self.app_instance and hasattr(self.app_instance, 'is_dark_theme'):
            self.on_theme_changed(self.app_instance.is_dark_theme())
        else:
            # Fallback if app or settings are not ready (should not happen ideally)
            print("Warning: StatisticsTab could not access app_instance for initial theme setup.")
            self.on_theme_changed(False) # Assume light theme as default
        self.refresh_charts() # Now refresh with initial theme

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
        self.fig = plt.Figure(figsize=(8, 6), dpi=100)
        self.ax_priority = self.fig.add_subplot(221)
        self.ax_category = self.fig.add_subplot(222)
        self.ax_difficulty = self.fig.add_subplot(223)
        self.ax_timeline = self.fig.add_subplot(224)
        
        # Create the TkAgg canvas and pack it
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.charts_container_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        # Initially pack it, refresh_charts will manage visibility
        self.canvas_widget.pack(fill='both', expand=True) 

        # Create the "no data" label (initially hidden or not packed)
        self.no_data_label = ttk.Label(
            self.charts_container_frame,
            text="No assignments to analyze for statistics.",
            font=("TkDefaultFont", 12)
            # style='Header.TLabel' # Style might not be available or might clash
        )
        # Do not pack no_data_label here; refresh_charts will manage it.

    def on_theme_changed(self, is_dark_theme):
        """Updates chart and label styles based on the theme."""
        if not self.fig: # Not yet initialized
            return
        
        style_to_apply = self._get_matplotlib_style(is_dark_theme)
        theme_settings = {} # Default empty dict

        if not self.app_instance or not hasattr(self.app_instance, 'is_dark_theme') or not hasattr(self.app_instance, 'get_current_theme_settings'):
            print("Warning: StatisticsTab cannot access app_instance or full theme settings.")
            # Use fallback style_to_apply and derive basic colors
            self.text_color = style_to_apply.get("text.color", 'white' if is_dark_theme else 'black')
            self.plot_bg_color = style_to_apply.get("axes.facecolor", '#3C3C3C' if is_dark_theme else 'white')
            self.figure_bg_color = style_to_apply.get("figure.facecolor", '#2E2E2E' if is_dark_theme else '#F0F0F0')
            self.grid_color = style_to_apply.get("axes.edgecolor", 'white' if is_dark_theme else 'black') # Using edgecolor for grid
            text_color_fallback = self.text_color
            bg_color_fallback = self.plot_bg_color # For no_data_label background
            
            if self.no_data_label:
                 self.no_data_label.configure(
                    foreground=text_color_fallback,
                    background=bg_color_fallback 
                )
        else:
            theme_settings = self.app_instance.get_current_theme_settings()
            # Set instance attributes for colors and fonts from theme_settings or style_to_apply
            self.text_color = theme_settings.get('text_color', style_to_apply.get("text.color", 'white' if is_dark_theme else 'black'))
            self.plot_bg_color = theme_settings.get('plot_bg', style_to_apply.get("axes.facecolor", '#3C3C3C' if is_dark_theme else 'white'))
            self.figure_bg_color = theme_settings.get('background_color', style_to_apply.get("figure.facecolor", '#2E2E2E' if is_dark_theme else '#F0F0F0'))
            self.grid_color = theme_settings.get('grid_color', style_to_apply.get("axes.edgecolor", 'gray')) # A dedicated grid color or fallback

        # Font sizes
        self.chart_font_size = theme_settings.get('chart_font_size', 12)
        self.axis_label_font_size = theme_settings.get('axis_label_font_size', 10)
        self.tick_label_font_size = theme_settings.get('tick_label_font_size', 9)
        
        # Apply the chosen style to Matplotlib rcParams
        plt.rcParams.update(style_to_apply)

        # Specific adjustments for our figure and axes
        self.fig.patch.set_facecolor(self.figure_bg_color)
        for ax in [self.ax_priority, self.ax_category, self.ax_difficulty, self.ax_timeline]:
            if ax: # Ensure axis exists
                ax.set_facecolor(self.plot_bg_color)
                ax.tick_params(colors=self.text_color, which='both') # For x and y ticks
                ax.xaxis.label.set_color(self.text_color)
                ax.yaxis.label.set_color(self.text_color)
                ax.title.set_color(self.text_color)
                for spine in ax.spines.values():
                    spine.set_edgecolor(self.grid_color) # Use grid_color for spines
        
        # Update 'no_data_label' style
        if self.no_data_label:
            self.no_data_label.configure(
                foreground=self.text_color,
                background=self.figure_bg_color # Match figure background
            )
            # Ensure the container frame also matches the theme
            self.charts_container_frame.configure(style='TFrame')


        if self.canvas:
            self.canvas.draw_idle() # Redraw with new styles

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
            # Apply theme settings to the canvas widget's parent as well for consistency
            if self.app_instance and hasattr(self.app_instance, 'get_current_theme_settings'):
                is_dark = self.app_instance.is_dark_theme()
                # Set canvas background to match figure background
                self.canvas_widget.configure(bg=self._get_matplotlib_style(is_dark)["figure.facecolor"])
            
            self.canvas_widget.pack(fill='both', expand=True)

        # Apply current theme styles before drawing new data
        if self.app_instance and hasattr(self.app_instance, 'is_dark_theme'):
             current_style = self._get_matplotlib_style(self.app_instance.is_dark_theme())
             plt.rcParams.update(current_style)
             self.fig.patch.set_facecolor(current_style["figure.facecolor"])
             for ax_obj in [self.ax_priority, self.ax_category, self.ax_difficulty, self.ax_timeline]:
                if ax_obj:
                    ax_obj.set_facecolor(current_style["axes.facecolor"])
                    ax_obj.tick_params(colors=current_style["xtick.color"], which='both')
                    ax_obj.xaxis.label.set_color(current_style["axes.labelcolor"])
                    ax_obj.yaxis.label.set_color(current_style["axes.labelcolor"])
                    ax_obj.title.set_color(current_style["text.color"])
                    for spine in ax_obj.spines.values():
                        spine.set_edgecolor(current_style["axes.edgecolor"])

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
        colors_map = {'High': '#FF6347', 'Medium': '#FFA500', 'Low': '#32CD32', 'Other': '#778899'} # Tomato, Orange, LimeGreen, LightSlateGray
        pie_colors = [colors_map.get(label, colors_map.get('Other', '#778899')) for label in labels]

        # Determine text color based on theme for autopct and labels
        text_color = plt.rcParams.get('text.color', 'black') # Default to black if not found

        ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            colors=pie_colors,
            textprops={'color': text_color}, # Ensure pie chart text (labels, autopct) uses theme color
            wedgeprops={'edgecolor': plt.rcParams.get('patch.edgecolor', 'black')} # Ensure wedge borders use theme color
        )
        ax.set_title('Assignments by Priority') # Title color is handled by general ax settings
        
    def _create_category_chart(self, ax, assignments):
        """Creates a bar chart of assignment categories (originally by priority)."""

        if not assignments:
            ax.text(0.5, 0.5, "No assignment data for priority bar chart.", ha='center', va='center', fontsize=self.axis_label_font_size, color=self.text_color)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title('Assignments by Priority', color=self.text_color, fontsize=self.chart_font_size)
            return

        # Count assignments by priority
        priority_counts_counter = Counter([asn.get('priority', 'N/A') for asn in assignments])

        # Sort by a defined priority order (High, Medium, Low, N/A)
        priority_order = {'High': 0, 'Medium': 1, 'Low': 2, 'N/A': 3}
        
        sorted_priorities = sorted(
            priority_counts_counter.items(), 
            key=lambda item: priority_order.get(item[0], 99) # Sort by defined order, others last
        )
        
        if not sorted_priorities:
            ax.text(0.5, 0.5, "No priority data to display.", ha='center', va='center', fontsize=self.axis_label_font_size, color=self.text_color)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title('Assignments by Priority', color=self.text_color, fontsize=self.chart_font_size)
            return
            
        labels = [item[0] for item in sorted_priorities]
        values = [item[1] for item in sorted_priorities]

        # Define a color map for priorities using ttkbootstrap theme colors (this was original for this bar chart)
        priority_color_map = {
            'High': self.app_instance.root.style.colors.danger,
            'Medium': self.app_instance.root.style.colors.warning,
            'Low': self.app_instance.root.style.colors.success,
            'N/A': self.app_instance.root.style.colors.secondary
        }
        bar_colors = [priority_color_map.get(label, self.app_instance.root.style.colors.primary) for label in labels]

        ax.bar(labels, values, color=bar_colors)
        
        ax.set_title('Assignments by Priority', color=self.text_color, fontsize=self.chart_font_size)
        ax.set_ylabel('Number of Assignments', color=self.text_color, fontsize=self.axis_label_font_size)
        ax.tick_params(axis='x', colors=self.text_color, labelsize=self.tick_label_font_size, rotation=0)
        ax.tick_params(axis='y', colors=self.text_color, labelsize=self.tick_label_font_size)
        ax.grid(axis='y', linestyle='--', alpha=0.7, color=self.grid_color)

        for i, v in enumerate(values):
            ax.text(i, v + 0.05 * max(values) if values else 0.1, str(v), color=self.text_color, ha='center', va='bottom', fontsize=self.tick_label_font_size)

        if values:
            ax.set_ylim(0, max(values) * 1.1 if max(values) > 0 else 1)
        else:
            ax.set_ylim(0, 1)

    def _create_difficulty_chart(self, ax, assignments):
        """Creates a histogram of assignment difficulties."""
        ax.clear()
        difficulties = [a.get('difficulty') for a in assignments if a.get('difficulty') is not None]
        
        ax.set_facecolor(self.plot_bg_color)
        ax.tick_params(axis='x', colors=self.text_color, labelsize=self.tick_label_font_size)
        ax.tick_params(axis='y', colors=self.text_color, labelsize=self.tick_label_font_size)
        ax.xaxis.label.set_color(self.text_color)
        ax.yaxis.label.set_color(self.text_color)
        ax.title.set_color(self.text_color)
        for spine in ax.spines.values():
            spine.set_edgecolor(self.grid_color) # Or self.text_color

        if not difficulties:
            ax.text(0.5, 0.5, "No difficulty data", ha='center', va='center', transform=ax.transAxes, color=self.text_color, fontsize=self.axis_label_font_size)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            hist_color = self.app_instance.root.style.colors.info
            ax.hist(difficulties, bins=10, range=(0.5, 10.5), edgecolor=self.grid_color, color=hist_color)
        
        ax.set_title('Difficulty Distribution', fontsize=self.chart_font_size)
        ax.set_xlabel('Difficulty Level (1-10)', fontsize=self.axis_label_font_size)
        ax.set_ylabel('Number of Assignments', fontsize=self.axis_label_font_size)
        ax.set_xticks(range(1, 11))
        ax.grid(axis='y', linestyle='--', alpha=0.7, color=self.grid_color)
        
    def _create_timeline_chart(self, ax, assignments):
        """Creates a scatter plot timeline of upcoming assignments."""
        ax.clear()
        
        # Apply theme styles
        ax.set_facecolor(self.plot_bg_color)
        ax.tick_params(axis='x', colors=self.text_color, labelrotation=45, labelsize=self.tick_label_font_size)
        ax.xaxis.label.set_color(self.text_color)
        ax.title.set_color(self.text_color)
        for spine in ax.spines.values():
            spine.set_edgecolor(self.grid_color) # Match other charts

        upcoming_assignments = []
        today = datetime.now().date() # Compare with date part for day-level precision

        for a in assignments:
            if not a.get('completed', False):
                due_date_val = a.get('due_date')
                dt_obj = None
                if isinstance(due_date_val, str):
                    try:
                        dt_obj = datetime.strptime(due_date_val, '%Y-%m-%d %H:%M:%S').date()
                    except ValueError:
                        try:
                            dt_obj = datetime.strptime(due_date_val, '%Y-%m-%d %H:%M').date()
                        except ValueError:
                            try:
                                dt_obj = datetime.strptime(due_date_val, '%Y-%m-%d').date()
                            except ValueError:
                                continue 
                elif isinstance(due_date_val, datetime):
                    dt_obj = due_date_val.date()
                elif isinstance(due_date_val, date): # Handle if it's already a date object
                    dt_obj = due_date_val
                if dt_obj >= today: # Only include today or future dates
                    # Store the original datetime if available for precise sorting, or date for plotting
                    plot_date = datetime.combine(dt_obj, datetime.min.time()) # Use datetime for mpl plotting
                    upcoming_assignments.append({'date': plot_date, 'priority': a.get('priority', 'Other')})

        ax.set_title(
            'Upcoming Assignment Due Dates (Next 30 Days)', 
            fontsize=self.chart_font_size, 
            color=self.text_color, 
            pad=15
        )
        ax.set_xlabel('Due Date', fontsize=self.axis_label_font_size)
        ax.set_yticks([])

        if not upcoming_assignments:
            ax.text(0.5, 0.5, "No upcoming assignments to display.", ha='center', va='center', transform=ax.transAxes, color=self.text_color, fontsize=self.axis_label_font_size)
            ax.set_xticks([])
            return

        upcoming_assignments.sort(key=lambda x: x['date'])
        
        dates_to_plot = [a['date'] for a in upcoming_assignments]
        priorities = [a['priority'] for a in upcoming_assignments]
        color_map = {
            'High': self.app_instance.root.style.colors.danger,
            'Medium': self.app_instance.root.style.colors.warning,
            'Low': self.app_instance.root.style.colors.success,
            'Other': self.app_instance.root.style.colors.secondary
        }
        plot_colors = [color_map.get(p, self.app_instance.root.style.colors.secondary) for p in priorities]
        
        ax.scatter(dates_to_plot, [1] * len(dates_to_plot), c=plot_colors, s=100, alpha=0.7, edgecolor=self.grid_color)
            
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        if dates_to_plot:
            min_date = min(dates_to_plot)
            max_date = max(dates_to_plot)
            # Ensure min_date and max_date are datetime objects for timedelta
            min_dt = min_date if isinstance(min_date, datetime) else datetime.combine(min_date, datetime.min.time())
            max_dt = max_date if isinstance(max_date, datetime) else datetime.combine(max_date, datetime.min.time())
            min_padding = timedelta(days=1)
            max_padding = timedelta(days=1)
            
            if max_dt > min_dt:
                 dynamic_padding = timedelta(days=max(1, (max_dt - min_dt).days * 0.05))
                 min_padding = max(min_padding, dynamic_padding)
                 max_padding = max(max_padding, dynamic_padding)
            
            ax.set_xlim(min_dt - min_padding, max_dt + max_padding)
        else:
            # Fallback if dates_to_plot is empty but upcoming_assignments was not (should not happen)
            ax.set_xticks([])
        
        ax.grid(axis='x', linestyle='--', alpha=0.5, color=self.grid_color) # Only show x-grid lines