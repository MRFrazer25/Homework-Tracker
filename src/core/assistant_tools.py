"""LangChain tools that let the assistant read and change assignments."""

import difflib
import re
from datetime import date, datetime

from langchain_core.tools import tool

from src.core.data_handler import DUE_TIME
from src.utils.date_parsing import parse_date
from src.utils.helpers import ALLOWED_PRIORITIES, PRIORITY_RANK


# Words that say nothing about which assignment is meant
GENERIC_WORDS = {"the", "my", "a", "an", "one", "that", "this", "assignment", "assignments", "task", "thing", "for", "class"}


def _format_due(due):
    if not isinstance(due, datetime):
        return "no due date"
    return due.strftime("%a %b %d").replace(" 0", " ")


class AssistantTools:
    """Builds the tool list for the agent and records whether any tool changed data."""

    def __init__(self, assignment_manager, study_tips_generator, today_provider=date.today):
        self.assignment_manager = assignment_manager
        self.study_tips_generator = study_tips_generator
        self.today_provider = today_provider
        self.data_changed = False
        self.user_message = ""  # The request being handled; used to sanity-check the model's choices

    # --- Helpers ---
    def find_assignment(self, name):
        """Returns (assignment, None) on a unique match, else (None, error_message)."""
        assignments = self.assignment_manager.get_assignments()
        if not assignments:
            return None, "You don't have any assignments yet."
        query = (name or "").strip().lower()
        names = {a.get('name', ''): a for a in assignments}

        # Small models sometimes pick an assignment from earlier in the conversation instead of the one
        # the user just named. If the message names exactly one assignment and the model chose something
        # the user didn't say, trust the user's words.
        said = self.user_message.lower()
        mentioned = [a for n, a in names.items() if n and re.search(rf"(?<!\w){re.escape(n.lower())}(?!\w)", said)]
        if len(mentioned) == 1 and query not in said:
            return mentioned[0], None

        exact = [a for n, a in names.items() if n.lower() == query]
        if len(exact) == 1:
            return exact[0], None
        partial = [a for n, a in names.items() if query and (query in n.lower() or n.lower() in query)]
        if len(partial) == 1:
            return partial[0], None
        if len(partial) > 1:
            options = ", ".join(f"'{a['name']}'" for a in partial)
            return None, f"'{name}' matches more than one assignment ({options}). Which one did you mean?"
        close = difflib.get_close_matches(query, [n.lower() for n in names], n=1, cutoff=0.6)
        if close:
            return next(a for n, a in names.items() if n.lower() == close[0]), None

        # Last resort: shared keywords with the name or class ("the spanish one" -> "Spanish vocab quiz")
        keywords = set(re.findall(r"\w+", query)) - GENERIC_WORDS
        by_keyword = [a for a in assignments
                      if keywords & set(re.findall(r"\w+", f"{a.get('name', '')} {a.get('class', '')}".lower()))]
        if len(by_keyword) == 1:
            return by_keyword[0], None
        if len(by_keyword) > 1:
            options = ", ".join(f"'{a['name']}'" for a in by_keyword)
            return None, f"'{name}' could be more than one assignment ({options}). Which one did you mean?"
        return None, f"I couldn't find an assignment called '{name}'."

    def _resolve_due(self, text):
        parsed = parse_date(text, today=self.today_provider())
        return datetime.combine(parsed, DUE_TIME) if parsed else None

    # --- Tools ---
    def build(self):
        """Returns the LangChain tools. All are return_direct so a request needs only one model call."""

        @tool(return_direct=True, parse_docstring=True)
        def list_assignments(only_incomplete: bool = True) -> str:
            """List the user's assignments, soonest due first.

            Args:
                only_incomplete: Only show assignments that are not done yet.
            """
            assignments = [a for a in self.assignment_manager.get_assignments()
                           if not (only_incomplete and a.get('completed'))]
            if not assignments:
                return "Nothing left to do!" if only_incomplete else "You don't have any assignments yet."
            assignments.sort(key=lambda a: a['due_date'] if isinstance(a.get('due_date'), datetime) else datetime.max)
            lines = ["Here's what you have:" if only_incomplete else "All of your assignments:"]
            for a in assignments:
                status = " (done)" if a.get('completed') else ""
                lines.append(f"- {a['name']} ({a.get('class', 'N/A')}) - due {_format_due(a.get('due_date'))}, "
                             f"{a.get('priority', 'N/A')} priority{status}")
            return "\n".join(lines)

        @tool(return_direct=True, parse_docstring=True)
        def add_assignment(name: str, class_name: str, due_date: str,
                           priority: str = "Medium", difficulty: int = 5) -> str:
            """Add a new assignment.

            Args:
                name: Assignment name.
                class_name: The class or project it belongs to.
                due_date: The due date exactly as the user said it, e.g. "friday", "next monday", "oct 10".
                priority: One of Low, Medium, High, Urgent.
                difficulty: How hard it is, from 1 to 10.
            """
            due = self._resolve_due(due_date)
            if not due:
                return f"I couldn't understand the date '{due_date}'. Try something like 'friday' or 'oct 10'."
            priority = priority.capitalize() if priority and priority.capitalize() in ALLOWED_PRIORITIES else "Medium"
            ok, result = self.assignment_manager.add_assignment({
                'name': name, 'class': class_name or "General", 'due_date': due,
                'priority': priority, 'difficulty': difficulty,
            })
            if not ok:
                return result
            self.data_changed = True
            return f"Added '{name}' ({class_name or 'General'}), due {_format_due(due)}, {priority} priority."

        @tool(return_direct=True, parse_docstring=True)
        def mark_complete(assignment_name: str) -> str:
            """Mark an assignment as done, when the user says they finished it.

            Args:
                assignment_name: Name of the assignment.
            """
            return self._set_completion(assignment_name, True)

        @tool(return_direct=True, parse_docstring=True)
        def mark_incomplete(assignment_name: str) -> str:
            """Mark an assignment as NOT done, when the user says it isn't finished yet or wants to undo marking it done.

            Args:
                assignment_name: Name of the assignment.
            """
            return self._set_completion(assignment_name, False)

        @tool(return_direct=True, parse_docstring=True)
        def reschedule(assignment_name: str, new_due_date: str) -> str:
            """Change an assignment's due date.

            Args:
                assignment_name: Name of the assignment.
                new_due_date: The new date exactly as the user said it, e.g. "friday", "next monday", "oct 10".
            """
            assignment, error = self.find_assignment(assignment_name)
            if error:
                return error
            due = self._resolve_due(new_due_date)
            if not due:
                return f"I couldn't understand the date '{new_due_date}'. Try something like 'friday' or 'oct 10'."
            ok, message = self.assignment_manager.update_assignment({'id': assignment['id'], 'due_date': due})
            if not ok:
                return message
            self.data_changed = True
            return f"Moved '{assignment['name']}' to {_format_due(due)}."

        @tool(return_direct=True, parse_docstring=True)
        def set_priority(assignment_name: str, priority: str) -> str:
            """Change an assignment's priority.

            Args:
                assignment_name: Name of the assignment.
                priority: One of Low, Medium, High, Urgent.
            """
            assignment, error = self.find_assignment(assignment_name)
            if error:
                return error
            priority = (priority or "").capitalize()
            if priority not in ALLOWED_PRIORITIES:
                return f"Priority must be one of: {', '.join(ALLOWED_PRIORITIES)}."
            ok, message = self.assignment_manager.update_assignment({'id': assignment['id'], 'priority': priority})
            if not ok:
                return message
            self.data_changed = True
            return f"Set '{assignment['name']}' to {priority} priority."

        @tool(return_direct=True)
        def get_study_plan() -> str:
            """Suggest what to work on and how to split the time, plus any workload warnings."""
            active = [a for a in self.assignment_manager.get_assignments() if not a.get('completed')]
            if not active:
                return "You're all caught up, nothing to plan!"
            parts = self.study_tips_generator.get_workload_warning(active)
            parts += self.study_tips_generator.generate_schedule_suggestion(active)
            return "\n".join(parts)

        @tool(return_direct=True)
        def get_study_tips() -> str:
            """Give study tips for the user's most pressing assignment."""
            active = [a for a in self.assignment_manager.get_assignments() if not a.get('completed')]
            if not active:
                return "You're all caught up, enjoy the free time!"
            focus = min(active, key=lambda a: (-PRIORITY_RANK.get(a.get('priority'), 0),
                                               a['due_date'] if isinstance(a.get('due_date'), datetime) else datetime.max))
            tips = self.study_tips_generator.get_enhanced_study_tips(active, focus)
            return f"Tips for '{focus['name']}':\n" + "\n".join(f"- {t}" for t in tips[:5])

        return [list_assignments, add_assignment, mark_complete, mark_incomplete,
                reschedule, set_priority, get_study_plan, get_study_tips]

    def _set_completion(self, assignment_name, completed):
        assignment, error = self.find_assignment(assignment_name)
        if error:
            return error
        ok, message = self.assignment_manager.set_completion(assignment['id'], completed)
        if not ok:
            return message
        self.data_changed = True
        return f"Marked '{assignment['name']}' as {'done' if completed else 'not done'}."
