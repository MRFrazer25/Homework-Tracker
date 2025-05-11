from datetime import datetime, timedelta

class StudyTipsGenerator:
    """Generates intelligent study tips and suggestions based on assignments and workload."""

    HOURS_PER_DIFFICULTY_POINT = 1.5  # Heuristic for workload/schedule estimation

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
        
        # Subject-specific tips
        subject_tips = {
            'Math': [
                "Practice similar problems from textbook exercises.",
                "Create a formula sheet for quick reference.",
                "Work through examples step-by-step.",
                "Use online math resources for additional practice if stuck."
            ],
            'Science': [
                "Create visual diagrams or flashcards for key concepts.",
                "Review lab safety guidelines thoroughly before any experiments.",
                "Try to connect theories to real-world applications.",
                "Make use of educational science videos to visualize complex topics."
            ],
            'History': [
                "Create timelines to visualize event sequences and their context.",
                "Use mind maps to connect related historical events, figures, and ideas.",
                "Focus on understanding cause and effect relationships.",
                "Write summaries of chapters or periods in your own words to aid retention."
            ],
            'English': [
                "Create a detailed outline before starting any writing assignment.",
                "Read your written work aloud to check for flow, clarity, and errors.",
                "Consider peer review sessions for constructive feedback.",
                "Utilize writing tools for grammar and style checking."
            ],
            'Computer Science': [
                "Test your code frequently with various input cases, including edge cases.",
                "Document your code with comments as you write, not just at the end.",
                "Break down complex programming problems into smaller, solvable parts.",
                "Learn to use debugging tools effectively to find and fix issues."
            ]
            # Add more subjects and tips as needed
        }
        
        assignment_class = current_assignment.get('class')
        if assignment_class and assignment_class in subject_tips:
            tips.extend(subject_tips[assignment_class])
        
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
                    "📅 You have multiple assignments due soon. Create a detailed weekly study schedule.",
                    "⏰ Use time blocking techniques to allocate specific time slots for each assignment.",
                    "📊 Prioritize your tasks based on due dates, difficulty, and weight."
                ])
        
        # Priority-based tips for the current assignment
        if current_assignment.get('priority') == 'High':
            tips.extend([
                "❗ This is a high-priority assignment. Consider starting it before others.",
                "📋 Set specific, achievable daily goals for this assignment.",
                "⚡ Minimize distractions during your dedicated work sessions for this task."
            ])
        
        # Time management based on due date for the current assignment
        current_due_date = current_assignment.get('due_date')
        if current_due_date and isinstance(current_due_date, datetime):
            days_until_due = (current_due_date - datetime.now()).days
            if days_until_due <= 2: # Due in 0, 1, or 2 days
                tips.extend([
                    "⚠️ This assignment is due very soon! Focus on completing essential parts first.",
                    "🕒 Set specific completion milestones for today and tomorrow.",
                    "📱 Minimize all distractions and dedicate focused time for completion."
                ])
            elif days_until_due <= 7:
                tips.extend([
                    "📆 This assignment is due within a week. Create a daily progress plan.",
                    "✅ Break the remaining work into manageable chunks for each day.",
                    "📈 Track your progress daily to stay on schedule."
                ])
        
        return list(set(tips)) if tips else ["Try to break down the work and start early!"]

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
            
        high_priority_count = sum(1 for a in active_week_assignments if a.get('priority') == 'High')
        if high_priority_count >= 3:
            warnings.append(
                f"⚠️ You have {high_priority_count} high-priority assignments due this week!"
            )
        
        high_difficulty_count = sum(1 for a in active_week_assignments if a.get('difficulty', 0) >= 8)
        if high_difficulty_count >= 2:
            warnings.append(
                f"⚠️ You have {high_difficulty_count} challenging (difficulty 8+) assignments this week!"
            )
        
        total_estimated_hours = sum(
            a.get('difficulty', 0) * StudyTipsGenerator.HOURS_PER_DIFFICULTY_POINT
            for a in active_week_assignments
        )
        
        if total_estimated_hours > 30: 
            warnings.append(
                f"⚠️ Heavy workload this week! Estimated {total_estimated_hours:.1f} hours needed for assignments."
            )
        elif total_estimated_hours > 20:
             warnings.append(
                f"🔎 Moderate workload this week: Estimated {total_estimated_hours:.1f} hours. Plan your time well!"
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
        
        priority_map = {'High': 3, 'Medium': 2, 'Low': 1, 'Other': 0}
        # Correct sorting: Higher priority first, then earlier due date first
        upcoming_schedulable.sort(key=lambda x: x['due_date']) # Sort by due date first (earliest first)
        upcoming_schedulable.sort(key=lambda x: priority_map.get(x.get('priority', 'Other'), 0), reverse=True) # Then sort by priority (highest first)


        schedule = ["📅 Suggested Study Schedule Focus (Top 5):"]
        
        for assignment in upcoming_schedulable[:5]: 
            days_until_due = (assignment['due_date'] - datetime.now()).days
            difficulty = assignment.get('difficulty', 0)
            estimated_hours_total = difficulty * StudyTipsGenerator.HOURS_PER_DIFFICULTY_POINT
            
            # Ensure days_until_due is positive for daily hour calculation
            if days_until_due > 0:
                daily_hours_suggestion = estimated_hours_total / days_until_due
                schedule.append(
                    f"• {assignment.get('name', 'N/A')} ({assignment.get('class', 'N/A')}):\n"
                    f"  - Priority: {assignment.get('priority', 'N/A')}, Difficulty: {difficulty}/10\n"
                    f"  - Due in {days_until_due} days. Estimated total: {estimated_hours_total:.1f} hrs.\n"
                    f"  - Suggestion: Allocate ~{daily_hours_suggestion:.1f} hours/day."
                )
            elif days_until_due == 0: # Due today
                 schedule.append(
                    f"• {assignment.get('name', 'N/A')} ({assignment.get('class', 'N/A')}):\n"
                    f"  - Priority: {assignment.get('priority', 'N/A')}, Difficulty: {difficulty}/10\n"
                    f"  - URGENT: DUE TODAY! Estimated remaining: {estimated_hours_total:.1f} hrs. Focus on this!"
                )
            # Assignments past due are already filtered out by `a.get('due_date') > datetime.now()`
        
        if len(schedule) == 1: # Only header was added
            return ["No assignments suitable for current schedule suggestion (e.g., all due today or issues with data)."]

        return schedule
