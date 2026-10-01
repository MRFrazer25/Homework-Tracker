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


def call(name, **args):
    return {"name": name, "args": args, "id": f"call_{name}", "type": "tool_call"}


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
