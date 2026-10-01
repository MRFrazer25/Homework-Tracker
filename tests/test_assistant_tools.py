from datetime import date, datetime

import pytest

from src.core.assignment_manager import AssignmentManager
from src.core.assistant_tools import AssistantTools
from src.core.data_handler import DataHandler
from src.core.study_tips import StudyTipsGenerator

WEDNESDAY = date(2026, 9, 30)


@pytest.fixture
def manager(tmp_path):
    manager = AssignmentManager(DataHandler(data_dir=tmp_path))
    for name, klass, day in [("Science project", "Science", 2), ("hw #1", "Math", 1),
                             ("Essay draft", "English", 5), ("Essay final", "English", 9)]:
        manager.add_assignment({'name': name, 'class': klass, 'due_date': datetime(2026, 10, day, 23, 59),
                                'priority': "Medium", 'difficulty': 5})
    return manager


@pytest.fixture
def helper(manager):
    return AssistantTools(manager, StudyTipsGenerator(), today_provider=lambda: WEDNESDAY)


@pytest.fixture
def tools(helper):
    return {t.name: t for t in helper.build()}


def by_name(manager, name):
    return next(a for a in manager.get_assignments() if a['name'] == name)


def test_tools_are_return_direct_with_descriptions(tools):
    for t in tools.values():
        assert t.return_direct
        assert t.description
    assert "due_date" in tools["add_assignment"].args


def test_add_resolves_natural_date(tools, manager, helper):
    reply = tools["add_assignment"].invoke({"name": "Math quiz", "class_name": "Math",
                                            "due_date": "friday", "priority": "high"})
    assert "Fri Oct 2" in reply
    quiz = by_name(manager, "Math quiz")
    assert quiz['due_date'] == datetime(2026, 10, 2, 23, 59)
    assert quiz['priority'] == "High"
    assert helper.data_changed


def test_add_rejects_bad_date(tools, manager, helper):
    reply = tools["add_assignment"].invoke({"name": "X", "class_name": "Y", "due_date": "someday"})
    assert "couldn't understand" in reply
    assert len(manager.get_assignments()) == 4
    assert not helper.data_changed


def test_fuzzy_name_matching(tools, manager):
    tools["mark_complete"].invoke({"assignment_name": "the science projct"})
    assert by_name(manager, "Science project")['completed']
    tools["mark_complete"].invoke({"assignment_name": "HW #1"})
    assert by_name(manager, "hw #1")['completed']


def test_ambiguous_name_asks_which(tools, manager):
    reply = tools["mark_complete"].invoke({"assignment_name": "essay"})
    assert "more than one" in reply and "Essay draft" in reply and "Essay final" in reply
    assert not any(a['completed'] for a in manager.get_assignments())


def test_user_words_override_wrong_model_choice(tools, helper, manager):
    # Seen in real use: after adding "Chem Lab", the model marked it done when the user named another assignment
    helper.user_message = "I finished the science project"
    reply = tools["mark_complete"].invoke({"assignment_name": "hw #1"})
    assert reply == "Marked 'Science project' as done."
    assert not by_name(manager, "hw #1")['completed']


def test_model_choice_kept_when_user_names_several_or_none(tools, helper, manager):
    helper.user_message = "mark hw #1 done and move the science project"
    tools["mark_complete"].invoke({"assignment_name": "hw #1"})
    assert by_name(manager, "hw #1")['completed']
    helper.user_message = "mark it as done"  # Refers back to the conversation, so trust the model
    tools["mark_complete"].invoke({"assignment_name": "Essay draft"})
    assert by_name(manager, "Essay draft")['completed']


def test_keyword_match_on_name_or_class(tools, manager):
    # Seen in real use: the model called "the spanish one" "Spanish assignment"
    tools["set_priority"].invoke({"assignment_name": "Science assignment", "priority": "High"})
    assert by_name(manager, "Science project")['priority'] == "High"
    reply = tools["set_priority"].invoke({"assignment_name": "English one", "priority": "High"})
    assert "more than one" in reply  # Two English assignments


def test_unknown_name(tools):
    assert "couldn't find" in tools["mark_complete"].invoke({"assignment_name": "basket weaving"})


def test_reschedule_and_priority(tools, manager):
    assert "Mon Oct 5" in tools["reschedule"].invoke({"assignment_name": "hw #1", "new_due_date": "next monday"})
    assert by_name(manager, "hw #1")['due_date'] == datetime(2026, 10, 5, 23, 59)
    tools["set_priority"].invoke({"assignment_name": "hw #1", "priority": "urgent"})
    assert by_name(manager, "hw #1")['priority'] == "Urgent"
    assert "must be one of" in tools["set_priority"].invoke({"assignment_name": "hw #1", "priority": "meh"})


def test_list_is_sorted_and_hides_done(tools):
    tools["mark_complete"].invoke({"assignment_name": "Essay final"})
    listing = tools["list_assignments"].invoke({})
    assert "Essay final" not in listing
    assert listing.index("hw #1") < listing.index("Science project") < listing.index("Essay draft")
    assert "Essay final" in tools["list_assignments"].invoke({"only_incomplete": False})


def test_study_helpers_run(tools):
    assert tools["get_study_plan"].invoke({})
    assert tools["get_study_tips"].invoke({}).startswith("Tips for")
