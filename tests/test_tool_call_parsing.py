import json

import pytest

from src.core.local_chat_model import parse_tool_calls


def tool_call(name, arguments):
    return "<tool_call>\n" + json.dumps({"name": name, "arguments": arguments}) + "\n</tool_call>"


@pytest.mark.parametrize("raw, expected_calls", [
    (tool_call("mark_complete", {"assignment_name": "essay"}) + "<|end_of_text|>",
     [("mark_complete", {"assignment_name": "essay"})]),
    # Granite sometimes encodes the arguments as a JSON string
    (tool_call("add_assignment", json.dumps({"name": "Chem Lab", "due_date": "tomorrow"}, indent=2)),
     [("add_assignment", {"name": "Chem Lab", "due_date": "tomorrow"})]),
    (tool_call("mark_complete", {"assignment_name": "hw #1"}) + "\n"
     + tool_call("reschedule", {"assignment_name": 'lab, "final"', "new_due_date": "oct 10"}) + "<|im_end|>",
     [("mark_complete", {"assignment_name": "hw #1"}),
      ("reschedule", {"assignment_name": 'lab, "final"', "new_due_date": "oct 10"})]),
    ('<tool_call>[{"name": "list_assignments", "arguments": {}}]</tool_call>', [("list_assignments", {})]),
])
def test_parses_tool_calls(raw, expected_calls):
    text, calls = parse_tool_calls(raw)
    assert calls == expected_calls
    assert text == ""


def test_plain_text_reply():
    text, calls = parse_tool_calls("You're welcome! Let me know if you need anything.<|end_of_text|>")
    assert calls == []
    assert text == "You're welcome! Let me know if you need anything."


def test_malformed_tool_call_is_not_executed():
    _, calls = parse_tool_calls('<tool_call>{"name": broken json</tool_call>')
    assert calls == []
