from datetime import datetime, timedelta

import pytest

import src.core.chatbot as chatbot_module
from src.core.chatbot import Chatbot
from src.core.study_tips import StudyTipsGenerator
from src.utils.helpers import PRIORITY_RANK, get_priority_color


class FakeAssignmentManager:
    def __init__(self, assignments):
        self.assignments = assignments

    def get_assignments(self):
        return self.assignments


def due_in(days):
    return datetime.combine((datetime.now() + timedelta(days=days)).date(), datetime.max.time().replace(microsecond=0))


@pytest.fixture
def assignments():
    return [
        {'id': 1, 'name': "Low thing", 'class': "Art", 'due_date': due_in(3), 'priority': "Low", 'difficulty': 2, 'completed': False},
        {'id': 2, 'name': "Urgent thing", 'class': "MATH 201", 'due_date': due_in(5), 'priority': "Urgent", 'difficulty': 8, 'completed': False},
        {'id': 3, 'name': "Due today", 'class': "History", 'due_date': due_in(0), 'priority': "Medium", 'difficulty': 4, 'completed': False},
    ]


@pytest.fixture
def bot(assignments, tmp_path, monkeypatch):
    # Keep the test from writing to the real chat log
    monkeypatch.setattr(chatbot_module, "PERSISTENT_CHAT_LOG_FILE", tmp_path / "log.json")
    return Chatbot(FakeAssignmentManager(assignments), StudyTipsGenerator())


def test_urgent_ranks_above_high():
    assert PRIORITY_RANK["Urgent"] > PRIORITY_RANK["High"] > PRIORITY_RANK["Medium"] > PRIORITY_RANK["Low"]
    assert get_priority_color("Urgent") != get_priority_color("unknown")


@pytest.mark.parametrize("text, expected", [
    ("show my priorities", "show priorities"),
    ("what's my schedule", "check schedule"),
    ("list my assignments", "list assignments"),
    ("give me some tips", "get study tips"),
    ("I have multiple things to do", None),  # "multiple" must not match "tip"
    ("this is weird", None),  # "this" must not match "hi"
])
def test_keyword_fallback(bot, text, expected):
    assert bot._match_keyword_intent(text) == expected


def test_responds_before_models_load(bot):
    assert not bot.models_ready.is_set()
    response = bot.get_response("show my priorities")
    assert "Urgent priority" in response
    # Most urgent group comes first
    assert response.index("Urgent") < response.index("Medium") < response.index("Low")
    assert (bot.get_response("blah blah")).startswith("I'm still loading")


def test_study_tips_focus_on_most_urgent(bot):
    response = bot.get_response("tips please")
    assert "Tips for 'Urgent thing'" in response


def test_class_tips_match_case_insensitively(assignments):
    tips = StudyTipsGenerator.get_enhanced_study_tips(assignments, assignments[1])
    assert any("formulas" in tip for tip in tips)  # Math tip for "MATH 201"


def test_schedule_includes_assignment_due_today(assignments):
    schedule = "\n".join(StudyTipsGenerator.generate_schedule_suggestion(assignments))
    assert "DUE TODAY" in schedule
    # Urgent sorts first
    assert schedule.index("Urgent thing") < schedule.index("Due today")
