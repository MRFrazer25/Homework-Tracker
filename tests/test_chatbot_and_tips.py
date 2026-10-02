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
    response, changed = bot.get_response("show my priorities")
    assert not changed
    assert "Urgent priority" in response
    # Most urgent group comes first
    assert response.index("Urgent") < response.index("Medium") < response.index("Low")
    assert bot.get_response("blah blah")[0].startswith("I'm still loading")


def test_study_tips_focus_on_most_urgent(bot):
    response, _ = bot.get_response("tips please")
    assert "Tips for 'Urgent thing'" in response


def test_class_tips_match_case_insensitively(assignments):
    tips = StudyTipsGenerator.get_enhanced_study_tips(assignments, assignments[1])
    assert any("formulas" in tip for tip in tips)  # Math tip for "MATH 201"


def test_schedule_includes_assignment_due_today(assignments):
    schedule = "\n".join(StudyTipsGenerator.generate_schedule_suggestion(assignments))
    assert "DUE TODAY" in schedule
    # Urgent sorts first
    assert schedule.index("Urgent thing") < schedule.index("Due today")


class FakeAssistant:
    def __init__(self, reply, used_tools=True, changed=True, fail=False):
        self.reply, self.last_used_tools, self.changed, self.fail = reply, used_tools, changed, fail

    def respond(self, text):
        if self.fail:
            raise RuntimeError("model crashed")
        return self.reply, self.changed


def test_assistant_handles_requests_when_loaded(bot):
    bot.assistant = FakeAssistant("Moved 'essay' to Mon Oct 5.")
    assert bot.get_response("push my essay to monday") == ("Moved 'essay' to Mon Oct 5.", True)


def test_help_shows_examples_even_with_assistant(bot):
    bot.assistant = FakeAssistant("should not be used")
    response, changed = bot.get_response("help")
    assert "plain English" in response and not changed


def test_falls_back_to_classic_replies_if_assistant_errors(bot):
    bot.assistant = FakeAssistant("", fail=True)
    response, changed = bot.get_response("show my priorities")
    assert "Urgent priority" in response and not changed


@pytest.mark.parametrize("message, expected", [
    ("hey how's it going", "doing well"),
    ("thanks!", "welcome"),
    ("ok cool", "Got it"),
    ("bye", "Goodbye"),
])
def test_small_talk_never_reaches_the_assistant(bot, message, expected):
    bot.assistant = FakeAssistant("SHOULD NOT BE USED", fail=True)
    response, changed = bot.get_response(message)
    assert expected in response and not changed


@pytest.mark.parametrize("message", ["hey can you move my essay to friday", "thanks, now mark hw done"])
def test_requests_with_small_talk_still_go_to_the_assistant(bot, message):
    bot.assistant = FakeAssistant("Moved it.")
    assert bot.get_response(message) == ("Moved it.", True)


def test_joy_prefix_only_when_finishing_something(bot):
    bot.emotion_classifier = lambda text: [{"label": "joy"}]
    bot.assistant = FakeAssistant("Added 'Book report' (English), due Wed Oct 14, Medium priority.")
    assert bot.get_response("I have a book report due in 2 weeks")[0].startswith("Added")
    bot.assistant = FakeAssistant("Marked 'Essay' as done.")
    assert bot.get_response("I finished my essay!")[0] == "That's great to hear! Marked 'Essay' as done."


def test_weak_emotion_readings_are_ignored(bot):
    bot.assistant = FakeAssistant("Added 'Map quiz' (Geography), due Tue Oct 20, Urgent priority.")
    bot.emotion_classifier = lambda text: [{"label": "fear", "score": 0.2}]  # "urgent" weakly misread as fear
    assert bot.get_response("add a map quiz due oct 20, urgent")[0].startswith("Added")
    bot.emotion_classifier = lambda text: [{"label": "fear", "score": 0.96}]
    assert bot.get_response("I'm worried, move the quiz to oct 20")[0].startswith("No need to worry")


def test_go_emotions_labels_map_to_tones(bot):
    bot.emotion_classifier = lambda text: [[{"label": "nervousness", "score": 0.6}, {"label": "neutral", "score": 0.3}]]
    assert bot._detect_emotion("worried about the midterm") == "fear"
    bot.emotion_classifier = lambda text: [[{"label": "relief", "score": 0.5}]]
    assert bot._detect_emotion("finally done") == "joy"
    bot.emotion_classifier = lambda text: [[{"label": "curiosity", "score": 0.9}]]  # Not a tone we use
    assert bot._detect_emotion("what's due?") == "neutral"


def test_stress_words_count_when_the_model_misses_them(bot):
    bot.emotion_classifier = lambda text: [[{"label": "neutral", "score": 0.9}]]
    assert bot._detect_emotion("I'm so stressed, any tips?") == "fear"
    bot.emotion_classifier = None  # Also works before the model loads
    assert bot._detect_emotion("feeling overwhelmed") == "fear"
