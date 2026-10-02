"""LangChain tools that let the assistant read and change assignments."""

import difflib
import re
from datetime import date, datetime, timedelta

from langchain_core.tools import tool

from src.core.data_handler import DUE_TIME
from src.utils.date_parsing import find_date_phrases, parse_date
from src.utils.helpers import ALLOWED_PRIORITIES, PRIORITY_RANK


# Words that say nothing about which assignment is meant
GENERIC_WORDS = {"the", "my", "a", "an", "one", "that", "this", "assignment", "assignments", "task", "thing", "for", "class"}

# A small model sometimes maps a request onto the wrong action (e.g. "rename X" became "mark X done"),
# so each change only runs if the user's message actually asks for that kind of change.
UNDO_WORDS = re.compile(r"\b(not (done|finished|complete)|(isn'?t|aren'?t|wasn'?t) (done|finished|complete)"
                        r"|(didn'?t|haven'?t|hasn'?t|never) (actually |really )?(finish\w*|complet\w*|do|done|submit\w*|start\w*)"
                        r"|still (need|have) to|still working on|undo|unmark|incomplete|reopen|not yet)\b", re.IGNORECASE)
# Yes/no and wh- questions ("is X done?", "when is X due?") ask about data, so they never change it.
# Polite requests ("can you move X to friday?") don't start this way and still work.
QUESTION = re.compile(r"^\s*(is|are|was|were|did|does|do|have|has|when|what|which|where|why|how)\b", re.IGNORECASE)
# Changes are made to specific assignments, never to everything at once
BULK_WORDS = re.compile(r"\b(everything|all (of )?(my|the|them|those|these)\b|every (assignment|one|single))", re.IGNORECASE)
BULK = "I can only change specific assignments, one or two at a time. Which ones did you mean?"
QUESTION_REPLY = ("It sounds like you're asking rather than telling me to change something. Ask \"what do I have left?\" "
                  "to see your list, or tell me what to change, like \"mark the essay done\".")
ACTION_WORDS = {
    # Tolerates common typos ("finshed", "complted", "sumbitted")
    "complete": re.compile(r"\b(done|fini?sh\w*|compl\w*t\w*|su[bm]{2}it\w*|turned in|handed in|wrapped up|check(ed)? off)\b", re.IGNORECASE),
    # Moving also needs a date phrase or one of these verbs ("change" alone isn't enough: "change the class of...")
    "reschedule": re.compile(r"\b(move\w*|push\w*|reschedul\w*|delay\w*|postpone\w*|extend\w*|bump\w*|shift\w*)\b", re.IGNORECASE),
    "priority": re.compile(r"\b(priority|urgent|important|high|low|medium)\b", re.IGNORECASE),
    "add": re.compile(r"\b(add\w*|new|create\w*|have|got|gotta|assigned|due|put|throw|need to|have to|must)\b", re.IGNORECASE),
}
# Moving words win over adding unless the user explicitly says to add ("push X to friday" is never a new X)
EXPLICIT_ADD = re.compile(r"\b(add\w*|new|create\w*)\b", re.IGNORECASE)
CLARIFY = ("I'm not sure what you'd like me to do with '{name}'. I can mark it done or not done, "
           "change its due date, or change its priority.")
UNSUPPORTED_WORDS = re.compile(r"\b(renam\w*|delet\w*|remov\w*|erase|get rid of)\b"
                               r"|\b(chang|set|switch|updat)\w*\b.{0,40}\bclass\b", re.IGNORECASE)
UNSUPPORTED = ("I can't rename, delete, or change the class of assignments from the chat. You can do that in the "
               "Assignments tab (double-click an assignment to edit it, or select it and click Delete Selected).")


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
        assignment, error = self._match_assignment(name)
        if error:
            return None, error
        # The model sometimes silently picks one of several assignments the user's words fit
        # ("the history essay" when there's a draft and a final), so check against what was actually said.
        others = self._also_fits_user_words(assignment)
        if others:
            options = ", ".join(f"'{a['name']}'" for a in [assignment] + others)
            return None, f"That could be more than one assignment ({options}). Which one did you mean?"
        return assignment, None

    def _also_fits_user_words(self, chosen):
        """Other assignments that fit the words the user used for `chosen` just as well."""
        said = self.user_message.lower()
        if re.search(rf"(?<!\w){re.escape(chosen['name'].lower())}(?!\w)", said):
            return []  # They said its full name
        words = lambda a: set(re.findall(r"\w+", f"{a.get('name', '')} {a.get('class', '')}".lower()))
        overlap = (words(chosen) & set(re.findall(r"\w+", said))) - GENERIC_WORDS
        if not overlap:
            return []  # e.g. "make it urgent": refers back to the conversation, so trust the model
        return [a for a in self.assignment_manager.get_assignments() if a is not chosen and overlap <= words(a)]

    def _match_assignment(self, name):
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

    def _filter_by_user_words(self, assignments):
        """
        Filters a listing by time ("today", "tomorrow", "this week", "overdue") and class ("chemistry", "chem")
        when the user's message mentions them. Returns (assignments, description of the filter or "").
        """
        said = self.user_message.lower()
        today = self.today_provider()
        due = lambda a: a['due_date'].date() if isinstance(a.get('due_date'), datetime) else None
        scopes = []

        if re.search(r"\b(overdue|late|past due|missed)\b", said):
            assignments = [a for a in assignments if due(a) and due(a) < today and not a.get('completed')]
            scopes.append("overdue")
        elif re.search(r"\b(today|tonight)\b", said):
            assignments = [a for a in assignments if due(a) == today]
            scopes.append("due today")
        elif re.search(r"\btomorrow\b", said):
            assignments = [a for a in assignments if due(a) == today + timedelta(days=1)]
            scopes.append("due tomorrow")
        elif re.search(r"\b(this|the) week\b|\bnext (7|seven) days\b", said):
            assignments = [a for a in assignments if due(a) and today <= due(a) <= today + timedelta(days=7)]
            scopes.append("due this week")

        said_words = [w for w in re.findall(r"[a-z]+", said) if len(w) >= 4 and w not in GENERIC_WORDS]
        classes = {(a.get('class') or "").lower() for a in self.assignment_manager.get_assignments()} - {""}
        asked_classes = {c for c in classes if re.search(rf"\b{re.escape(c)}\b", said)
                         or any(c.startswith(w) for w in said_words)}  # "chem" -> "chemistry"
        if asked_classes:
            assignments = [a for a in assignments if (a.get('class') or "").lower() in asked_classes]
            scopes.append("for " + " and ".join(sorted(c.title() for c in asked_classes)))
        return assignments, " ".join(scopes)

    def _clarify(self, name):
        return UNSUPPORTED if UNSUPPORTED_WORDS.search(self.user_message) else CLARIFY.format(name=name)

    def _refuse_change(self):
        """A reply refusing any change for this message, or None if changes are allowed."""
        if UNSUPPORTED_WORDS.search(self.user_message):
            return UNSUPPORTED
        if QUESTION.match(self.user_message):
            return QUESTION_REPLY
        if BULK_WORDS.search(self.user_message):
            return BULK
        return None

    def _asked_for(self, action):
        """Whether the user's message asks for this kind of change."""
        said = self.user_message
        if action == "complete":
            return bool(ACTION_WORDS["complete"].search(said)) and not UNDO_WORDS.search(said)
        if action == "undo":
            return bool(UNDO_WORDS.search(said))
        if action in ("reschedule", "add"):
            # A date in the message is a strong sign of either ("throw a french essay on there for thursday")
            return bool(ACTION_WORDS[action].search(said) or find_date_phrases(said))
        return bool(ACTION_WORDS[action].search(said))

    def _existing_assignment_named(self, name):
        """An existing assignment with (nearly) this name, so adding it again would create a duplicate."""
        query = (name or "").strip().lower()
        names = {(a.get('name') or "").lower(): a for a in self.assignment_manager.get_assignments()}
        if query in names:
            return names[query]
        close = difflib.get_close_matches(query, list(names), n=1, cutoff=0.85)
        return names[close[0]] if close else None

    def _resolve_due(self, text):
        """
        Resolves the model's date text. If the message contains a single date phrase, or the model shortened
        one ("friday" when the user said "next friday"), the user's own phrase wins.
        """
        phrases = find_date_phrases(self.user_message)
        model_text = (text or "").strip().lower()
        containing = [p for p in phrases if model_text and model_text in p.lower()]
        if len(phrases) == 1:
            text = phrases[0]  # Only one date in the message, so that's the one they meant
        elif len(containing) == 1:
            text = containing[0]
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
            # Narrow the list by what the user asked about, read from their own words
            assignments, scope = self._filter_by_user_words(assignments)
            if not assignments:
                if scope:
                    return f"Nothing {scope}!"
                return "Nothing left to do!" if only_incomplete else "You don't have any assignments yet."
            assignments.sort(key=lambda a: a['due_date'] if isinstance(a.get('due_date'), datetime) else datetime.max)
            header = f"Here's what you have {scope}:" if scope else "Here's what you have:"
            lines = [header if only_incomplete else "All of your assignments:"]
            for a in assignments:
                status = " (done)" if a.get('completed') else ""
                lines.append(f"- {a['name']} ({a.get('class', 'N/A')}) - due {_format_due(a.get('due_date'))}, "
                             f"{a.get('priority', 'N/A')} priority{status}")
            return "\n".join(lines)

        @tool(return_direct=True, parse_docstring=True)
        def add_assignment(name: str, class_name: str, due_date: str,
                           priority: str = "Medium", difficulty: int = 5) -> str:
            """Add a new assignment. Use this whenever the user mentions an assignment they have, got, or need to do
            that isn't in their list yet, e.g. "I have a quiz due friday".

            Args:
                name: Assignment name.
                class_name: The class or project it belongs to.
                due_date: The due date exactly as the user said it, e.g. "friday", "next monday", "oct 10".
                priority: One of Low, Medium, High, Urgent.
                difficulty: How hard it is, from 1 to 10.
            """
            refusal = self._refuse_change()
            if refusal:
                return refusal
            if not self._asked_for("add"):
                return "Did you want me to add a new assignment? If so, say something like 'add a math quiz due friday'."
            if ACTION_WORDS["reschedule"].search(self.user_message) and not EXPLICIT_ADD.search(self.user_message):
                return ("Did you want to move an existing assignment? Try something like 'move the essay to friday', "
                        "or say 'add' if it's a new one.")
            existing = self._existing_assignment_named(name)
            if existing:
                return (f"You already have '{existing['name']}' (due {_format_due(existing.get('due_date'))}). "
                        f"Did you want to move it instead? Try 'move {existing['name']} to friday'.")
            if not ACTION_WORDS["priority"].search(self.user_message):
                priority = "Medium"  # The model sometimes invents a priority the user never mentioned
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
            refusal = self._refuse_change()
            if refusal:
                return refusal
            if not self._asked_for("reschedule"):
                return self._clarify(assignment_name)
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
            refusal = self._refuse_change()
            if refusal:
                return refusal
            if not self._asked_for("priority"):
                return self._clarify(assignment_name)
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
        refusal = self._refuse_change()
        if refusal:
            return refusal
        if not self._asked_for("complete" if completed else "undo"):
            # The model sometimes picks the opposite tool ("unmark X" -> mark done); follow the user's words instead
            if self._asked_for("undo" if completed else "complete"):
                completed = not completed
            else:
                return self._clarify(assignment_name)
        assignment, error = self.find_assignment(assignment_name)
        if error:
            return error
        ok, message = self.assignment_manager.set_completion(assignment['id'], completed)
        if not ok:
            return message
        self.data_changed = True
        return f"Marked '{assignment['name']}' as {'done' if completed else 'not done'}."
