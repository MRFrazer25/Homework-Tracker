"""Utilities package for the Homework Tracker application"""

from .helpers import (
    format_time_remaining, 
    format_date, 
    calculate_workload_hours,
    get_priority_color,
    get_class_emoji
)

__all__ = [
    'format_time_remaining', 
    'format_date', 
    'calculate_workload_hours',
    'get_priority_color',
    'get_class_emoji'
]
