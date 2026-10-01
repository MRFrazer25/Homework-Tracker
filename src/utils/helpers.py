"""Helper functions for the Homework Tracker application"""

from datetime import datetime

def format_date(date_obj):
    """
    Format a due date consistently throughout the application.

    Returns:
        str: The date as YYYY-MM-DD, or 'N/A' if date_obj isn't a datetime.
    """
    if not isinstance(date_obj, datetime):
        return "N/A" # Handle None or invalid types gracefully
    return date_obj.strftime('%Y-%m-%d')

# Estimated hours of work per point of difficulty.
HOURS_PER_DIFFICULTY_POINT = 1.5

def get_priority_color(priority):
    """
    Get a theme-friendly color associated with a priority level for a light theme.
    
    Args:
        priority (str): Priority level ('Urgent', 'High', 'Medium', or 'Low').

    Returns:
        str: Hex color code.
    """
    return PRIORITY_COLORS.get(str(priority).capitalize(), '#A9A9A9')  # DarkGray for unknown or default

# Ordered lowest to highest.
ALLOWED_PRIORITIES = ["Low", "Medium", "High", "Urgent"]
# Higher rank = more important. Unknown priorities should default to 0.
PRIORITY_RANK = {p: i + 1 for i, p in enumerate(ALLOWED_PRIORITIES)}
PRIORITY_COLORS = {
    'Urgent': '#C71585',  # MediumVioletRed
    'High': '#FF6347',    # Tomato
    'Medium': '#FFA500',  # Orange
    'Low': '#32CD32',     # LimeGreen
}
ALLOWED_DIFFICULTY = list(range(1, 11))

# Date format for the date pickers and for parsing what they contain
DATE_FORMAT = '%Y-%m-%d'
