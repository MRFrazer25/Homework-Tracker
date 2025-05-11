from datetime import datetime, timedelta
from .study_tips import StudyTipsGenerator

class HomeworkChatbot:
    """AI assistant for homework management and study advice"""
    
    def __init__(self, data_handler):
        self.data_handler = data_handler
        self.study_tips = StudyTipsGenerator()
        self.commands = {
            'help': self.get_help_message, 
            'tips': self.get_study_tips,
            'schedule': self.suggest_schedule,
            'workload': self.analyze_workload,
            'upcoming': self.show_upcoming,
            'subjects': self.analyze_subjects,
            'priorities': self.show_priorities
        }
    
    def process_message(self, message, assignments=None):
        """
        Process user message and return appropriate response.
        
        Args:
            message (str): The user's input message.
            assignments (list, optional): Current list of assignments for context.

        Returns:
            str: The chatbot's response.
        """
        # Basic input normalization.
        # If this chatbot were to interact with powerful LLMs or external APIs,
        # more thorough input sanitization and validation would be crucial
        # to prevent prompt injection or other vulnerabilities.
        message = message.strip().lower()
        
        # Check for direct commands
        if message.startswith('/'):
            command = message[1:].split()[0]
            if command in self.commands:
                # Pass assignments only if the command function expects it (most do)
                # Help command does not need assignments.
                if command == 'help':
                    return self.commands[command]()
                return self.commands[command](assignments)
            return self.get_help_message() # Default for unknown slash command
        
        # Process natural language queries (simplified for clarity)
        if 'tip' in message or 'study' in message and ('how' in message or 'advice' in message):
            return self.get_study_tips(assignments)
        if 'schedule' in message:
            return self.suggest_schedule(assignments)
        if 'workload' in message:
            return self.analyze_workload(assignments)
        if 'due' in message or 'upcoming' in message:
            return self.show_upcoming(assignments)
        if 'subject' in message or 'class' in message and ('analyze' in message or 'show' in message):
            return self.analyze_subjects(assignments)
        if 'priority' in message or 'important' in message and ('show' in message or 'list' in message):
            return self.show_priorities(assignments)
        
        # Default response with help message if no specific query matched
        return self.get_help_message()

    def _get_active_upcoming_assignments(self, assignments):
        """Helper to filter for active (not completed, future due date) assignments."""
        if not assignments:
            return []
        return [
            a for a in assignments
            if not a.get('completed', False) and
               a.get('due_date') and isinstance(a.get('due_date'), datetime) and
               a.get('due_date') > datetime.now()
        ]
    
    def get_help_message(self, assignments=None): # Accept assignments=None for consistent command signature
        """Return help message with available commands."""
        # assignments argument is not used here but included for signature consistency with other commands.
        return (
            "🤖 I'm your homework assistant! Here's what I can help you with:\n\n"
            "Commands:\n"
            "/help - Show this help message\n"
            "/tips - Get study tips for your assignments\n"
            "/schedule - Get a suggested study schedule\n"
            "/workload - Analyze your current workload\n"
            "/upcoming - Show upcoming assignments\n"
            "/subjects - Analyze assignments by subject\n"
            "/priorities - Show assignment priorities\n\n"
            "You can also ask me questions in natural language about:\n"
            "- Study tips and strategies\n"
            "- Schedule management\n"
            "- Workload analysis\n"
            "- Assignment tracking\n\n"
            "Example: 'How should I manage my workload?'"
        )
    
    def get_study_tips(self, assignments):
        """Get study tips based on current assignments"""
        if not assignments:
            return "You don't have any assignments yet. Add some assignments and I'll provide personalized study tips!"
        
        active_upcoming = self._get_active_upcoming_assignments(assignments)
        
        if not active_upcoming:
            return "All your assignments are completed or have passed their due dates! Great job! 🎉"
        
        # Get most urgent assignment
        urgent = min(active_upcoming, key=lambda x: x['due_date']) # due_date is confirmed datetime here
        tips = self.study_tips.get_enhanced_study_tips(assignments, urgent) # Pass all assignments for broader context
        
        response = [
            f"📚 Study Tips for {urgent.get('name', 'N/A')} ({urgent.get('class', 'N/A')}):\n"
        ]
        response.extend(f"• {tip}" for tip in tips[:5])  # Show top 5 tips
        
        return "\n".join(response)
    
    def suggest_schedule(self, assignments):
        """Suggest a study schedule based on current assignments."""
        if not assignments:
            return "Add some assignments first, and I'll help you create a study schedule!"
        
        active_upcoming = self._get_active_upcoming_assignments(assignments)
        if not active_upcoming:
            return "No active assignments to schedule. Add some or check if they are all past due/completed!"

        schedule = self.study_tips.generate_schedule_suggestion(active_upcoming)
        return "\n".join(schedule)
    
    def analyze_workload(self, assignments):
        """Analyze current workload based on active assignments."""
        if not assignments:
            return "No assignments to analyze. Add some assignments to get workload insights!"
        
        active_upcoming = self._get_active_upcoming_assignments(assignments)
        if not active_upcoming:
             return "No active assignments to analyze for workload."

        warnings = self.study_tips.get_workload_warning(active_upcoming)
        
        if not warnings:
            return "👍 Your current workload for upcoming assignments looks manageable. Keep up the good work!"
        
        response = ["⚠️ Workload Analysis for Upcoming Assignments:"]
        response.extend(warnings)
        return "\n".join(response)
    
    def show_upcoming(self, assignments):
        """Show upcoming (not completed, future due date) assignments."""
        if not assignments:
            return "No assignments found. Add some assignments to track!"
        
        active_upcoming = self._get_active_upcoming_assignments(assignments)
        
        if not active_upcoming:
            return "No upcoming assignments! You're all caught up! 🎉"
        
        active_upcoming.sort(key=lambda x: x['due_date']) # Sort by due date
        
        response = ["📅 Upcoming Assignments:"]
        for a in active_upcoming[:5]:  # Show top 5 upcoming
            # Ensure due_date is datetime before calculating days_until
            days_until = (a['due_date'] - datetime.now()).days
            response.append(
                f"• {a.get('name', 'N/A')} ({a.get('class', 'N/A')})\n"
                f"  Due in {days_until} days - Priority: {a.get('priority', 'N/A')}"
            )
        
        if len(active_upcoming) > 5:
            response.append(f"\n...and {len(active_upcoming) - 5} more assignments.")
        
        return "\n".join(response)
    
    def analyze_subjects(self, assignments):
        """Analyze active assignments by subject/class."""
        if not assignments:
            return "No assignments to analyze. Add some assignments first!"
        
        subjects = {}
        active_assignments_count = 0
        for a in assignments:
            if not a.get('completed', False):
                active_assignments_count +=1
                subject = a.get('class', 'Uncategorized')
                subjects[subject] = subjects.get(subject, 0) + 1
        
        if not active_assignments_count: # Check if there were any non-completed assignments
            return "All assignments are completed! Great job! 🎉"
        if not subjects: # Should not happen if active_assignments_count > 0
             return "No subjects found in active assignments."

        response = ["📚 Active Assignments by Subject:"]
        for subject, count in sorted(subjects.items(), key=lambda x: x[1], reverse=True):
            response.append(f"• {subject}: {count} assignment(s)")
        
        return "\n".join(response)
    
    def show_priorities(self, assignments):
        """Show active assignments grouped by priority."""
        if not assignments:
            return "No assignments to analyze. Add some assignments first!"
        
        priorities = {'High': [], 'Medium': [], 'Low': [], 'Other': []}
        active_assignments_count = 0
        for a in assignments:
            if not a.get('completed', False) and a.get('due_date') and isinstance(a.get('due_date'), datetime): # Consider only those with valid due dates
                active_assignments_count +=1
                priority_key = a.get('priority', 'Other')
                if priority_key not in priorities: # Handle unexpected priority values
                    priority_key = 'Other'
                priorities[priority_key].append(a)
        
        if not active_assignments_count:
            return "All assignments are completed or lack valid due dates! Great work! 🎉"
        
        response = ["🎯 Active Assignments by Priority:"]
        
        for priority_level in ['High', 'Medium', 'Low', 'Other']: # Iterate in specific order
            if priorities[priority_level]:
                response.append(f"\n{priority_level} Priority:")
                # Sort by due date before slicing
                sorted_assignments = sorted(priorities[priority_level], key=lambda x: x['due_date'])
                for a in sorted_assignments[:3]: # Show top 3 for brevity
                    days = (a['due_date'] - datetime.now()).days
                    response.append(
                        f"• {a.get('name', 'N/A')} ({a.get('class', 'N/A')}) - Due in {days} days"
                    )
                if len(sorted_assignments) > 3:
                    response.append(f"  ...and {len(sorted_assignments) - 3} more.")
        
        return "\n".join(response)
