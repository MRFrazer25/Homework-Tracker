"""Helper functions for the Homework Tracker application"""

from datetime import datetime, timedelta

def format_time_remaining(due_date):
    """
    Format the time remaining until an assignment is due
    
    Args:
        due_date (datetime): The assignment's due date
    
    Returns:
        str: Formatted string showing time remaining
    """
    if not isinstance(due_date, datetime):
        return "Invalid date"

    now = datetime.now()
    time_delta = due_date - now
    
    total_seconds = time_delta.total_seconds()

    if total_seconds <= 0:
        return "Overdue!"
    
    if total_seconds < 60:
        return "Less than a minute remaining"

    days = time_delta.days
    hours = time_delta.seconds // 3600
    minutes = (time_delta.seconds % 3600) // 60
    
    time_parts = []
    if days > 0:
        time_parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0: # Only show minutes if it's the most significant or with hours/days
        time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    
    if not time_parts: # Should be caught by total_seconds < 60, but as a fallback
        return "Due very soon"

    return ", ".join(time_parts) + " remaining"

def format_date(date_obj, include_time=True):
    """
    Format a date(time) consistently throughout the application.
    
    Args:
        date_obj (datetime): The date object to format.
        include_time (bool): Whether to include the time in the output.
    
    Returns:
        str: Formatted date string, or 'N/A' if date_obj is invalid.
    """
    if not isinstance(date_obj, datetime):
        return "N/A" # Handle None or invalid types gracefully
    
    if include_time:
        return date_obj.strftime('%Y-%m-%d %H:%M')
    return date_obj.strftime('%Y-%m-%d')

# Estimated hours of work per point of difficulty.
HOURS_PER_DIFFICULTY_POINT = 1.5

def calculate_workload_hours(assignments, start_date=None, end_date=None):
    """
    Calculate estimated workload hours for a given time period.
    
    Args:
        assignments (list): List of assignment dictionaries.
        start_date (datetime, optional): Start of period to calculate. Defaults to now.
        end_date (datetime, optional): End of period to calculate. Defaults to 7 days from start_date.
    
    Returns:
        dict: Dictionary containing total hours, breakdown by class, and count of assignments.
    """
    if start_date is None:
        start_date = datetime.now()
    if end_date is None:
        end_date = start_date + timedelta(days=7) # Ensure end_date is relative to actual start_date
    
    # Ensure start_date and end_date are datetime objects for comparison
    if not (isinstance(start_date, datetime) and isinstance(end_date, datetime)):
        return {'total': 0, 'by_class': {}, 'assignments_count': 0}


    filtered_assignments = []
    for a in assignments:
        due_date = a.get('due_date')
        if not a.get('completed', False) and due_date and isinstance(due_date, datetime):
            # Compare date part if start/end are dates, or full datetime if they are datetimes
            # For simplicity, assuming due_date is comparable directly if start/end are datetimes
            if start_date <= due_date <= end_date:
                filtered_assignments.append(a)
    
    total_hours = sum(a.get('difficulty', 0) * HOURS_PER_DIFFICULTY_POINT for a in filtered_assignments)
    
    class_hours = {}
    for assignment in filtered_assignments:
        class_name = assignment.get('class', 'Uncategorized')
        hours = assignment.get('difficulty', 0) * HOURS_PER_DIFFICULTY_POINT
        class_hours[class_name] = class_hours.get(class_name, 0) + hours
    
    return {
        'total': total_hours,
        'by_class': class_hours,
        'assignments_count': len(filtered_assignments)
    }

def get_priority_color(priority):
    """
    Get a theme-friendly color associated with a priority level for a light theme.
    
    Args:
        priority (str): Priority level ('High', 'Medium', or 'Low').
    
    Returns:
        str: Hex color code.
    """
    return {
        'High': '#FF6347',    # Tomato
        'Medium': '#FFA500',  # Orange
        'Low': '#32CD32',     # LimeGreen
    }.get(str(priority).capitalize(), '#A9A9A9')  # DarkGray for unknown or default

ALLOWED_PRIORITIES = ["Low", "Medium", "High"]
ALLOWED_DIFFICULTY = list(range(1, 11))

# Date formats for use with ttkbootstrap.DateEntry and strptime/strftime
# These keys should match what's stored in settings (date_format_template_name)
DATE_FORMATS = {
    'default': '%Y-%m-%d', 
    'iso8601': '%Y-%m-%d',
    'us_short': '%m/%d/%y',
    'us_long': '%m/%d/%Y',
    'eur_short': '%d/%m/%y',
    'eur_long': '%d/%m/%Y',
    'verbose': '%B %d, %Y', # e.g., July 04, 2024
    'verbose_with_day': '%A, %B %d, %Y' # e.g., Thursday, July 04, 2024
}

def get_class_emoji(class_name):
    """Get an emoji representing a class."""
    if not isinstance(class_name, str):
        return '📓' # Default for non-string input
    
    class_name_lower = class_name.lower()
    # Simple mapping for common classes
    emoji_map = {
        'math': '🧮',
        'mathematics': '🧮',
        'science': '🔬',
        'physics': '⚛️',
        'chemistry': '🧪',
        'biology': '🧬',
        'history': '📜',
        'english': '📚',
        'literature': '📖',
        'language': '🗣️',
        'art': '🎨',
        'music': '🎵',
        'computer science': '💻',
        'programming': '💻',
        'geography': '🗺️',
        'philosophy': '🤔',
        # Add more mappings as desired
    }
    # Try to find a match for parts of the class_name as well
    for keyword, emoji in emoji_map.items():
        if keyword in class_name_lower:
            return emoji
    return '📓'  # Default emoji for unknown classes
