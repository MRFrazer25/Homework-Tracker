from datetime import date, datetime

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.core.assignment_manager import AssignmentManager
from src.core.assistant import Assistant
from src.core.data_handler import DataHandler
from src.core.study_tips import StudyTipsGenerator


class ScriptedChatModel(BaseChatModel):
    """Replays canned replies and records what the agent sent, so tests don't need a real LLM."""
    replies: list
    seen: list = []

    @property
    def _llm_type(self):
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=self.replies.pop(0))])


def call(tool_name, **args):
    return {"name": tool_name, "args": args, "id": f"call_{tool_name}", "type": "tool_call"}


@pytest.fixture
def manager(tmp_path):
    manager = AssignmentManager(DataHandler(data_dir=tmp_path))
    for name in ("hw #1", "lab report"):
        manager.add_assignment({'name': name, 'class': "Science", 'due_date': datetime(2030, 1, 1, 23, 59),
                                'priority': "Medium", 'difficulty': 5})
    return manager


def make_assistant(manager, replies):
    model = ScriptedChatModel(replies=replies, seen=[])
    assistant = Assistant(manager, StudyTipsGenerator(), model=model)
    assistant.tools.today_provider = lambda: date(2026, 9, 30)
    return assistant, model


def test_multiple_tool_calls_in_one_request(manager):
    assistant, model = make_assistant(manager, [
        AIMessage("", tool_calls=[call("mark_complete", assignment_name="hw #1"),
                                  call("reschedule", assignment_name="lab report", new_due_date="oct 10")]),
    ])
    reply, changed = assistant.respond("mark hw #1 done and move the lab report to oct 10")
    assert changed
    assert "Marked 'hw #1' as done." in reply and "Moved 'lab report' to Sat Oct 10." in reply
    assert len(model.seen) == 1  # return_direct tools: no second model call
    lab = next(a for a in manager.get_assignments() if a['name'] == "lab report")
    assert lab['due_date'] == datetime(2026, 10, 10, 23, 59)


@pytest.mark.parametrize("first_reply", [
    AIMessage("", tool_calls=[call("list_assignments")]),  # Looked the names up instead of moving it
    AIMessage("I'm not sure which assignment you mean. What's it called?"),  # Asked instead of moving it
])
def test_first_change_request_gets_the_list_and_a_second_try(manager, first_reply):
    # Real miss: "push my essay to next monday" as the first message listed assignments or asked which one
    assistant, model = make_assistant(manager, [
        first_reply,
        AIMessage("", tool_calls=[call("reschedule", assignment_name="lab report", new_due_date="oct 10")]),
    ])
    reply, changed = assistant.respond("push my lab to oct 10")
    assert (reply, changed) == ("Moved 'lab report' to Sat Oct 10.", True)
    second_prompt = model.seen[1]
    assert "Here's what you have" not in reply
    assert any("hw #1" in str(m.content) and "lab report" in str(m.content) for m in second_prompt)


@pytest.mark.parametrize("message", ["what's due oct 10?", "show me what's due oct 10", "list my assignments"])
def test_looking_at_the_list_is_not_retried(manager, message):
    assistant, model = make_assistant(manager, [AIMessage("", tool_calls=[call("list_assignments")])])
    reply, changed = assistant.respond(message)
    assert reply.startswith("Here's what you have") and not changed
    assert len(model.seen) == 1


def test_plain_chat_reply_changes_nothing(manager):
    assistant, _ = make_assistant(manager, [AIMessage("You're welcome!")])
    assert assistant.respond("thanks") == ("You're welcome!", False)


def test_history_is_sent_back_and_trimmed(manager):
    replies = [AIMessage(f"reply {i}") for i in range(4)]
    assistant, model = make_assistant(manager, replies)
    for i in range(4):
        assistant.respond(f"message {i}")
    last_prompt = [m.content for m in model.seen[-1] if isinstance(m, HumanMessage)]
    # Only the 2 previous exchanges plus the new message are sent
    assert last_prompt == ["message 1", "message 2", "message 3"]


@pytest.mark.parametrize("bad_call", [
    call("archive_assignment", assignment_name="hw #1"),  # A tool that doesn't exist
    call("reschedule", assignment_name="hw #1"),  # Missing a required argument
    call("add_assignment", name="Quiz", class_name="Math", due_date="friday", difficulty="hard"),  # Wrong type
])
def test_tool_errors_are_not_shown_to_the_user(manager, bad_call):
    assistant, _ = make_assistant(manager, [AIMessage("", tool_calls=[bad_call])] + [AIMessage("")] * 5)
    reply, changed = assistant.respond("do something")
    assert "Error" not in reply and "kwargs" not in reply
    assert reply.startswith("Sorry")
    assert not changed


def test_partial_success_reports_only_what_worked(manager):
    assistant, _ = make_assistant(manager, [
        AIMessage("", tool_calls=[call("mark_complete", assignment_name="hw #1"), call("reschedule", assignment_name="lab report")]),
    ])
    reply, changed = assistant.respond("finish hw and move the lab")
    assert reply == "Marked 'hw #1' as done."
    assert changed


def test_model_stuck_in_a_loop_is_cut_off(manager):
    # Each reply needs its own tool-call id, as real models produce
    looping = [AIMessage("", tool_calls=[{**call("archive_assignment", assignment_name="hw #1"), "id": f"call_{i}"}])
               for i in range(50)]
    assistant, model = make_assistant(manager, looping)
    reply, changed = assistant.respond("delete hw")
    assert "stuck" in reply
    assert len(model.seen) < 10
    assert assistant.history == []


def test_delete_flow_through_the_agent(manager):
    assistant, model = make_assistant(manager, [AIMessage("", tool_calls=[call("delete_assignment", assignment_name="hw #1")])])
    reply, changed = assistant.respond("delete hw #1")
    assert reply.startswith("Delete 'hw #1'") and not changed
    assert assistant.respond("yes") == ("Deleted 'hw #1'.", True)
    assert len(model.seen) == 1  # The confirmation never went to the model
    assert [a['name'] for a in manager.get_assignments()] == ["lab report"]
