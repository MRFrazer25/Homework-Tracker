from datetime import datetime
from src.utils.helpers import HOURS_PER_DIFFICULTY_POINT, PRIORITY_RANK
import random

class StudyTipsGenerator:
    """Generates intelligent study tips and suggestions based on assignments and workload."""

    @staticmethod
    def get_enhanced_study_tips(assignments, current_assignment):
        """
        Generate personalized study tips based on the current assignment and overall workload.

        Args:
            assignments (list): List of all assignment dictionaries.
            current_assignment (dict): The specific assignment to get tips for.

        Returns:
            list: A list of unique study tip strings.
        """
        tips = []
        if not current_assignment:
            return ["No specific assignment provided to generate tips for."]

        # Time management based on due date for the current assignment
        current_due_date = current_assignment.get('due_date')
        if current_due_date and isinstance(current_due_date, datetime):
            days_until_due = (current_due_date - datetime.now()).days
            if days_until_due <= 2: # Due in 0, 1, or 2 days
                tips.extend([
                    "This assignment is due very soon! Focus on completing essential parts first.",
                    "Set specific completion milestones for today and tomorrow.",
                    "Minimize all distractions and dedicate focused time for completion."
                ])
            elif days_until_due <= 7:
                tips.extend([
                    "This assignment is due within a week. Create a daily progress plan.",
                    "Break the remaining work into manageable chunks for each day.",
                    "Track your progress daily to stay on schedule."
                ])
        
        # Difficulty-based tips
        difficulty = current_assignment.get('difficulty', 0)
        if difficulty > 7:
            tips.extend([
                "Break this challenging assignment into smaller, manageable tasks.",
                "Schedule dedicated study blocks with breaks for this assignment.",
                "Consider using the Pomodoro Technique (e.g., 25min work / 5min break)."
            ])
        elif difficulty > 0 and difficulty < 4 : # Added condition for low difficulty
             tips.extend([
                "This seems like a lighter task. Plan to complete it efficiently!"
             ])
        
        # General tips applicable to most assignments
        GENERAL_TIPS = [
            "Break down large assignments into smaller, manageable tasks.",
            "Create a study schedule and stick to it.",
            "Minimize distractions: find a quiet study space and turn off notifications.",
            "Take regular short breaks (e.g., 5-10 minutes every hour) to stay fresh.",
            "Review your notes regularly, not just before an exam.",
            "Practice active recall: try to retrieve information without looking at your notes.",
            "Teach the material to someone else to solidify your understanding.",
            "Get enough sleep; it's crucial for memory consolidation.",
            "Stay hydrated and eat nutritious food to keep your brain powered.",
            "Don't be afraid to ask for help from teachers or classmates if you're stuck."
        ]

        # Class-specific tips
        class_tips = {
            "Math": [
                "Practice problems regularly. Understanding concepts is key, but practice builds speed and accuracy.",
                "Don't just memorize formulas; understand how they are derived and when to use them.",
                "Draw diagrams or visualize problems to help understand them better.",
                "Check your answers, and if you made a mistake, try to understand why."
            ],
            "Science": [
                "Understand the scientific method and how it applies to different topics.",
                "Relate concepts to real-world examples.",
                "For lab work, understand the procedures and safety precautions thoroughly before starting.",
                "Use flashcards for terminology and diagrams for processes."
            ],
            "History": [
                "Create timelines to understand the sequence of events.",
                "Focus on cause and effect relationships rather than just memorizing dates.",
                "Read primary sources when possible to get a deeper understanding.",
                "Try to explain historical events in your own words."
            ],
            "English": [
                "Read widely, both assigned texts and for pleasure, to improve vocabulary and comprehension.",
                "When writing essays, create an outline first to organize your thoughts.",
                "Pay attention to grammar, punctuation, and style.",
                "Practice summarizing texts and identifying main arguments."
            ],
            "Programming": [
                "Break down complex problems into smaller, solvable parts.",
                "Write pseudocode before writing actual code.",
                "Test your code frequently as you write it.",
                "Don't be afraid to look up documentation or ask for help on forums (but try to solve it yourself first).",
                "Version control (like Git) is your friend, even for small projects."
            ]
            # Add more classes and tips as needed
        }

        # Add class-specific tips
        # Case-insensitive partial match so e.g. "MATH 201" picks up the Math tips
        assignment_class = str(current_assignment.get('class') or '').lower()
        for class_key, class_specific_tips in class_tips.items():
            if class_key.lower() in assignment_class:
                tips.extend(class_specific_tips)
                break
        
        # Workload management tips based on all assignments
        if assignments: 
            due_this_week_count = sum(
                1 for a in assignments 
                if a.get('due_date') and isinstance(a.get('due_date'), datetime) and
                   (a.get('due_date') - datetime.now()).days <= 7 and
                   not a.get('completed', False)
            )
            if due_this_week_count >= 3:
                tips.extend([
                    "You have multiple assignments due soon. Create a detailed weekly study schedule.",
                    "Use time blocking techniques to allocate specific time slots for each assignment.",
                    "Prioritize your tasks based on due dates, difficulty, and weight."
                ])
        
        # Priority-based tips for the current assignment
        if current_assignment.get('priority') in ('High', 'Urgent'):
            tips.extend([
                "This is a high-priority assignment. Consider starting it before others.",
                "Set specific, achievable daily goals for this assignment.",
                "Minimize distractions during your dedicated work sessions for this task."
            ])
        
        # Generic advice last, so the most specific tips come first
        tips.extend(random.sample(GENERAL_TIPS, min(len(GENERAL_TIPS), 3)))

        # De-duplicate while keeping order
        return list(dict.fromkeys(tips)) if tips else ["Try to break down the work and start early!"]

    @staticmethod
    def get_workload_warning(assignments):
        """Generate warnings about potential workload issues based on active assignments for the upcoming week."""
        if not assignments:
            return []

        today = datetime.now().date()
        
        active_week_assignments = [
            a for a in assignments 
            if not a.get('completed', False) and 
               a.get('due_date') and isinstance(a.get('due_date'), datetime) and
               a.get('due_date').date() >= today and 
               (a.get('due_date').date() - today).days <= 7 
        ]
        
        warnings = []
        if not active_week_assignments:
            return warnings # No active assignments this week to warn about
            
        high_priority_count = sum(1 for a in active_week_assignments if a.get('priority') in ('High', 'Urgent'))
        if high_priority_count >= 3:
            warnings.append(
                f"You have {high_priority_count} high-priority assignments due this week!"
            )
        
        high_difficulty_count = sum(1 for a in active_week_assignments if a.get('difficulty', 0) >= 8)
        if high_difficulty_count >= 2:
            warnings.append(
                f"You have {high_difficulty_count} challenging (difficulty 8+) assignments this week!"
            )
        
        total_estimated_hours = sum(
            a.get('difficulty', 0) * HOURS_PER_DIFFICULTY_POINT
            for a in active_week_assignments
        )
        
        if total_estimated_hours > 30: 
            warnings.append(
                f"Heavy workload this week! Estimated {total_estimated_hours:.1f} hours needed for assignments."
            )
        elif total_estimated_hours > 20:
             warnings.append(
                f"Moderate workload this week: Estimated {total_estimated_hours:.1f} hours. Plan your time well!"
            )
        
        return warnings
    
    @staticmethod
    def generate_schedule_suggestion(assignments):
        """Generate a suggested study schedule based on active, upcoming assignments."""
        if not assignments:
            return ["No assignments to schedule!"]

        upcoming_schedulable = [
            a for a in assignments 
            if not a.get('completed', False) and 
               a.get('due_date') and isinstance(a.get('due_date'), datetime) and
               a.get('due_date') > datetime.now() and # Must be in the future
               a.get('difficulty') is not None and isinstance(a.get('difficulty'), (int, float))
        ]
        
        if not upcoming_schedulable:
            return ["No upcoming assignments that can be scheduled (check due dates, completion status, and difficulty)."]
        
        # Higher priority first, then earlier due date first
        upcoming_schedulable.sort(key=lambda x: (
            -PRIORITY_RANK.get(x.get('priority'), 0),  # Negative for descending priority
            x['due_date']  # Ascending due date for ties
        ))


        schedule = ["Suggested Study Schedule Focus (Top 5):"]
        
        for assignment in upcoming_schedulable[:5]: 
            days_until_due = (assignment['due_date'] - datetime.now()).days
            difficulty = assignment.get('difficulty', 0)
            estimated_hours_total = difficulty * HOURS_PER_DIFFICULTY_POINT
            
            # Ensure days_until_due is positive for daily hour calculation
            if days_until_due > 0:
                daily_hours_suggestion = estimated_hours_total / days_until_due
                schedule.append(
                    f"- {assignment.get('name', 'N/A')} ({assignment.get('class', 'N/A')}):\n"
                    f"  - Priority: {assignment.get('priority', 'N/A')}, Difficulty: {difficulty}/10\n"
                    f"  - Due in {days_until_due} days. Estimated total: {estimated_hours_total:.1f} hrs.\n"
                    f"  - Suggestion: Allocate ~{daily_hours_suggestion:.1f} hours/day."
                )
            elif days_until_due == 0: # Due today
                 schedule.append(
                    f"- {assignment.get('name', 'N/A')} ({assignment.get('class', 'N/A')}):\n"
                    f"  - Priority: {assignment.get('priority', 'N/A')}, Difficulty: {difficulty}/10\n"
                    f"  - URGENT: DUE TODAY! Estimated remaining: {estimated_hours_total:.1f} hrs. Focus on this!"
                )
            # Assignments past due are already filtered out by `a.get('due_date') > datetime.now()`
        
        if len(schedule) == 1: # Only header was added
            return ["No assignments suitable for current schedule suggestion (e.g., all due today or issues with data)."]

        return schedule
