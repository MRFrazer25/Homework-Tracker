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
    helper.user_message = "add a math quiz due friday, high priority"
    reply = tools["add_assignment"].invoke({"name": "Math quiz", "class_name": "Math",
                                            "due_date": "friday", "priority": "high"})
    assert "Fri Oct 2" in reply
    quiz = by_name(manager, "Math quiz")
    assert quiz['due_date'] == datetime(2026, 10, 2, 23, 59)
    assert quiz['priority'] == "High"
    assert helper.data_changed


def test_add_rejects_bad_date(tools, manager, helper):
    helper.user_message = "add X for Y due someday"
    reply = tools["add_assignment"].invoke({"name": "X", "class_name": "Y", "due_date": "someday"})
    assert "couldn't understand" in reply
    assert len(manager.get_assignments()) == 4
    assert not helper.data_changed


def test_fuzzy_name_matching(tools, manager, helper):
    helper.user_message = "finished the science projct and hw 1"
    tools["mark_complete"].invoke({"assignment_name": "the science projct"})
    assert by_name(manager, "Science project")['completed']
    tools["mark_complete"].invoke({"assignment_name": "HW #1"})
    assert by_name(manager, "hw #1")['completed']


def test_ambiguous_name_asks_which(tools, manager, helper):
    helper.user_message = "mark the essay done"
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


def test_keyword_match_on_name_or_class(tools, manager, helper):
    # Seen in real use: the model called "the spanish one" "Spanish assignment"
    helper.user_message = "make the science one and the english one high priority"
    tools["set_priority"].invoke({"assignment_name": "Science assignment", "priority": "High"})
    assert by_name(manager, "Science project")['priority'] == "High"
    reply = tools["set_priority"].invoke({"assignment_name": "English one", "priority": "High"})
    assert "more than one" in reply  # Two English assignments


def test_unknown_name(tools, helper):
    helper.user_message = "I finished basket weaving"
    assert "couldn't find" in tools["mark_complete"].invoke({"assignment_name": "basket weaving"})


def test_reschedule_and_priority(tools, manager, helper):
    helper.user_message = "move hw #1 to next monday and make it urgent"
    assert "Mon Oct 5" in tools["reschedule"].invoke({"assignment_name": "hw #1", "new_due_date": "next monday"})
    assert by_name(manager, "hw #1")['due_date'] == datetime(2026, 10, 5, 23, 59)
    tools["set_priority"].invoke({"assignment_name": "hw #1", "priority": "urgent"})
    assert by_name(manager, "hw #1")['priority'] == "Urgent"
    assert "must be one of" in tools["set_priority"].invoke({"assignment_name": "hw #1", "priority": "meh"})


def test_list_is_sorted_and_hides_done(tools, helper):
    helper.user_message = "essay final is done"
    tools["mark_complete"].invoke({"assignment_name": "Essay final"})
    listing = tools["list_assignments"].invoke({})
    assert "Essay final" not in listing
    assert listing.index("hw #1") < listing.index("Science project") < listing.index("Essay draft")
    assert "Essay final" in tools["list_assignments"].invoke({"only_incomplete": False})


def test_study_helpers_run(tools):
    assert tools["get_study_plan"].invoke({})
    assert tools["get_study_tips"].invoke({}).startswith("Tips for")


def test_mention_check_uses_whole_words(manager, helper, tools):
    manager.add_assignment({'name': "Art", 'class': "Art", 'due_date': datetime(2026, 10, 3, 23, 59),
                            'priority': "Medium", 'difficulty': 3})
    helper.user_message = "I finished the chart for the science project"  # "art" inside "chart" isn't a mention
    tools["mark_complete"].invoke({"assignment_name": "Science project"})
    assert by_name(manager, "Science project")['completed']
    assert not by_name(manager, "Art")['completed']


@pytest.mark.parametrize("message, tool, args", [
    # Seen in real use: "rename X" was turned into "mark X done"
    ("rename the science project to science fair", "mark_complete", {"assignment_name": "Science project"}),
    ("what's the science project about?", "reschedule", {"assignment_name": "Science project", "new_due_date": "friday"}),
    ("tell me about the science project", "set_priority", {"assignment_name": "Science project", "priority": "Low"}),
    ("hey how's it going", "add_assignment", {"name": "Hi", "class_name": "X", "due_date": "friday"}),
])
def test_actions_need_the_user_to_ask_for_them(tools, helper, manager, message, tool, args):
    before = [dict(a) for a in manager.get_assignments()]
    helper.user_message = message
    reply = tools[tool].invoke(args)
    assert manager.get_assignments() == before
    assert not helper.data_changed
    assert "?" in reply or "not sure" in reply or "Assignments tab" in reply


def test_undo_is_allowed_when_asked(tools, helper, manager):
    helper.user_message = "I finished the science project"
    tools["mark_complete"].invoke({"assignment_name": "Science project"})
    helper.user_message = "oops, the science project isn't done yet"
    assert tools["mark_incomplete"].invoke({"assignment_name": "Science project"}) == "Marked 'Science project' as not done."


@pytest.mark.parametrize("message, model_date, expected", [
    # Seen in real use: the model dropped "next" and moved it to this Friday
    ("push hw #1 to next friday", "friday", datetime(2026, 10, 9, 23, 59)),
    ("push hw #1 to friday", "friday", datetime(2026, 10, 2, 23, 59)),
    ("move hw #1 back two weeks, so in 2 weeks", "2 weeks", datetime(2026, 10, 14, 23, 59)),
    ("move hw #1 to oct 10", "the tenth", datetime(2026, 10, 10, 23, 59)),  # Unreadable model date, one phrase said
])
def test_users_date_phrase_wins(tools, helper, manager, message, model_date, expected):
    helper.user_message = message
    tools["reschedule"].invoke({"assignment_name": "hw #1", "new_due_date": model_date})
    assert by_name(manager, "hw #1")['due_date'] == expected


def test_add_uses_users_only_date_and_default_priority(tools, helper, manager):
    # Seen in real use: "due in 2 weeks" became next week, and a priority was invented
    helper.user_message = "I have a book report for English due in 2 weeks"
    tools["add_assignment"].invoke({"name": "Book report", "class_name": "English", "due_date": "next friday",
                                    "priority": "High"})
    report = by_name(manager, "Book report")
    assert report['due_date'] == datetime(2026, 10, 14, 23, 59)
    assert report['priority'] == "Medium"


@pytest.mark.parametrize("message", ["rename the essay draft to essay v1", "delete the essay draft"])
def test_rename_and_delete_point_to_the_assignments_tab(tools, helper, manager, message):
    helper.user_message = message
    for tool, args in [("mark_complete", {"assignment_name": "Essay draft"}),
                       ("add_assignment", {"name": "essay v1", "class_name": "English", "due_date": "friday"})]:
        assert "Assignments tab" in tools[tool].invoke(args)
    assert len(manager.get_assignments()) == 4 and not helper.data_changed


def test_didnt_finish_counts_as_undo(tools, helper, manager):
    helper.user_message = "I finished the science project"
    tools["mark_complete"].invoke({"assignment_name": "Science project"})
    helper.user_message = "wait i didn't actually finish the science project"
    # Even if the model picks "mark done", the user's "didn't finish" wins
    assert tools["mark_complete"].invoke({"assignment_name": "Science project"}) == "Marked 'Science project' as not done."


@pytest.mark.parametrize("message, model_choice", [
    # Seen in real use: the model silently picked one of several matches
    ("mark the essay as done", "Essay draft"),
    ("move my english assignment to friday", "Essay final"),
])
def test_asks_when_users_words_fit_several(tools, helper, manager, message, model_choice):
    helper.user_message = message
    tool = "mark_complete" if "done" in message else "reschedule"
    args = {"assignment_name": model_choice} | ({} if tool == "mark_complete" else {"new_due_date": "friday"})
    reply = tools[tool].invoke(args)
    assert "more than one" in reply and "Essay draft" in reply and "Essay final" in reply
    assert not helper.data_changed


def test_follow_up_without_names_trusts_the_model(tools, helper, manager):
    helper.user_message = "actually make it friday"
    assert tools["reschedule"].invoke({"assignment_name": "Essay final", "new_due_date": "friday"}).startswith("Moved")


def test_changing_class_is_not_a_move(tools, helper, manager):
    # Seen in real use: "change the class of X to Y" moved X to a made-up date
    helper.user_message = "change the class of the essay draft to writing"
    assert "Assignments tab" in tools["reschedule"].invoke({"assignment_name": "Essay draft", "new_due_date": "monday"})
    assert not helper.data_changed


@pytest.mark.parametrize("message, shown, hidden", [
    ("what's due today?", [], ["hw #1", "Science project"]),  # Nothing due Wednesday Sep 30
    ("what's due tomorrow", ["hw #1"], ["Science project"]),
    ("what do I have this week", ["hw #1", "Science project", "Essay draft"], ["Essay final"]),
    ("do I have anything for english?", ["Essay draft", "Essay final"], ["hw #1"]),
    ("any engl stuff", ["Essay draft", "Essay final"], ["hw #1"]),  # Prefixes need 4+ letters
])
def test_listing_filters_by_users_words(tools, helper, message, shown, hidden):
    helper.user_message = message
    listing = tools["list_assignments"].invoke({})
    for name in shown:
        assert name in listing
    for name in hidden:
        assert name not in listing
    if not shown:
        assert listing == "Nothing due today!"


def test_overdue_listing(tools, helper):
    helper.today_provider = lambda: date(2026, 10, 6)
    helper.user_message = "what's overdue?"
    listing = tools["list_assignments"].invoke({})
    assert "overdue" in listing and "hw #1" in listing and "Science project" in listing and "Essay final" not in listing


@pytest.mark.parametrize("message, tool, args", [
    ("is the science project done?", "mark_complete", {"assignment_name": "Science project"}),
    ("did I finish hw #1?", "mark_complete", {"assignment_name": "hw #1"}),
    ("when is hw #1 due?", "reschedule", {"assignment_name": "hw #1", "new_due_date": "friday"}),
    ("have I added a math quiz due friday?", "add_assignment", {"name": "Math quiz", "class_name": "Math", "due_date": "friday"}),
])
def test_questions_never_change_data(tools, helper, manager, message, tool, args):
    before = [dict(a) for a in manager.get_assignments()]
    helper.user_message = message
    reply = tools[tool].invoke(args)
    assert manager.get_assignments() == before and not helper.data_changed
    assert "asking" in reply


def test_polite_requests_still_work(tools, helper, manager):
    helper.user_message = "can you mark hw #1 as done?"
    assert tools["mark_complete"].invoke({"assignment_name": "hw #1"}) == "Marked 'hw #1' as done."


@pytest.mark.parametrize("message", ["mark everything as done", "move all my english stuff to friday", "set all of them to urgent"])
def test_bulk_changes_are_refused(tools, helper, manager, message):
    helper.user_message = message
    for tool, args in [("mark_complete", {"assignment_name": "Essay draft"}),
                       ("reschedule", {"assignment_name": "Essay final", "new_due_date": "friday"}),
                       ("set_priority", {"assignment_name": "hw #1", "priority": "Urgent"})]:
        assert tools[tool].invoke(args) == "I can only change specific assignments, one or two at a time. Which ones did you mean?"
    assert not helper.data_changed


def test_still_need_to_counts_as_undo(tools, helper, manager):
    helper.user_message = "finished the science project"
    tools["mark_complete"].invoke({"assignment_name": "Science project"})
    helper.user_message = "actually I still need to do the science project"
    assert tools["mark_incomplete"].invoke({"assignment_name": "Science project"}).endswith("as not done.")


@pytest.mark.parametrize("message, wrong_tool, completed_after", [
    # Seen in real use: the model picked the opposite tool
    ("unmark the science project", "mark_complete", False),
    ("I finished the science project", "mark_incomplete", True),
])
def test_opposite_completion_tool_follows_users_words(tools, helper, manager, message, wrong_tool, completed_after):
    manager.set_completion(by_name(manager, "Science project")['id'], not completed_after)
    helper.user_message = message
    tools[wrong_tool].invoke({"assignment_name": "Science project"})
    assert by_name(manager, "Science project")['completed'] is completed_after


@pytest.mark.parametrize("message", ["i finshed the science project", "complted the science project", "sumbitted the science project"])
def test_completion_words_tolerate_typos(tools, helper, manager, message):
    helper.user_message = message
    assert tools["mark_complete"].invoke({"assignment_name": "Science project"}) == "Marked 'Science project' as done."


@pytest.mark.parametrize("message, name", [
    # Seen in real use: casual phrasings were refused
    ("throw a french essay on there for next thursday", "French essay"),
    ("I need to read chapters 4 through 6 for history by sunday", "Read chapters 4-6"),
])
def test_casual_adds_work(tools, helper, manager, message, name):
    helper.user_message = message
    assert tools["add_assignment"].invoke({"name": name, "class_name": "X", "due_date": "thursday"}).startswith("Added")


@pytest.mark.parametrize("name", ["Essay draft", "essay draft", "Essay drafts"])
def test_adding_an_existing_assignment_is_refused(tools, helper, manager, name):
    # Mentioning an assignment you already have must not create a duplicate
    helper.user_message = "I have the essay draft due friday"
    reply = tools["add_assignment"].invoke({"name": name, "class_name": "English", "due_date": "friday"})
    assert "already have 'Essay draft'" in reply
    assert len(manager.get_assignments()) == 4


def test_similar_but_different_names_can_be_added(tools, helper, manager):
    helper.user_message = "add an essay outline due friday"
    assert tools["add_assignment"].invoke({"name": "Essay outline", "class_name": "English", "due_date": "friday"}).startswith("Added")


def test_move_request_never_adds(tools, helper, manager):
    helper.user_message = "push the essay to friday"
    reply = tools["add_assignment"].invoke({"name": "essay", "class_name": "English", "due_date": "friday"})
    assert "move an existing assignment" in reply
    assert len(manager.get_assignments()) == 4
    helper.user_message = "add a new essay and push it to friday"  # Explicit "add" still works
    assert tools["add_assignment"].invoke({"name": "New essay", "class_name": "English", "due_date": "friday"}).startswith("Added")
