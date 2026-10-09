"""LLM assistant: a LangChain agent backed by a local Hugging Face model that can change assignments."""

import re
import uuid

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from src.core.assistant_tools import ACTION_WORDS, UNDO_WORDS, AssistantTools
from src.core.local_chat_model import LocalChatModel
from src.utils.settings_manager import DEFAULT_ASSISTANT_MODEL, DEFAULT_ASSISTANT_REVISION

# Kept constant so the model's KV cache for it can be reused on every request.
SYSTEM_PROMPT = (
    "You are a helpful assistant inside a homework tracker app. "
    "Use the tools to look up or change the user's assignments whenever they ask about them; "
    "never invent assignments or dates. Pass dates exactly as the user said them (e.g. 'friday', 'oct 10'). "
    "When the user mentions an assignment they have with a due date (e.g. 'I have a book report due in 2 weeks'), "
    "add it with add_assignment. "
    "If the user just chats, reply briefly and warmly without using tools."
)

# How many past exchanges (user message plus everything after it) to send back to the model
HISTORY_EXCHANGES = 2
# Cap on agent graph steps per request (each model call and tool round is a couple of steps)
MAX_AGENT_STEPS = 8
# Requests to see the list rather than change it ("show me what's due friday")
LISTING_REQUEST = re.compile(r"^\s*(show|list|see|view|display|tell me|give me)\b", re.IGNORECASE)


class Assistant:
    def __init__(self, assignment_manager, study_tips_generator, model_id=DEFAULT_ASSISTANT_MODEL, model=None):
        self.tools = AssistantTools(assignment_manager, study_tips_generator)
        revision = DEFAULT_ASSISTANT_REVISION if model_id == DEFAULT_ASSISTANT_MODEL else None
        self.model = model or LocalChatModel(model_id=model_id, revision=revision)
        self.tool_list = self.tools.build()
        self.agent = create_agent(self.model, tools=self.tool_list, system_prompt=SYSTEM_PROMPT)
        self.history = []
        self.last_used_tools = False

    def load(self):
        """Loads the model weights (slow; run on a background thread)."""
        if hasattr(self.model, "load") and not getattr(self.model, "loaded", True):
            self.model.load()
        if hasattr(self.model, "warm_up"):
            self.model.warm_up(SYSTEM_PROMPT, self.tool_list)
        return self

    def confirm_pending(self, user_input):
        """Resolves a delete waiting for confirmation (handled in code, never by the model). See AssistantTools."""
        result = self.tools.confirm_pending(user_input)
        if result:
            self.last_used_tools = False
        return result

    def _recent_history(self):
        """The last few exchanges, cut at a user message so tool calls stay paired with their results."""
        starts = [i for i, m in enumerate(self.history) if isinstance(m, HumanMessage)]
        if len(starts) <= HISTORY_EXCHANGES:
            return list(self.history)
        return self.history[starts[-HISTORY_EXCHANGES]:]

    def _asks_for_change(self):
        """Whether the message clearly asks to change an existing assignment (not a question or a request to look)."""
        said = self.tools.user_message
        if self.tools._refuse_change() or LISTING_REQUEST.match(said):
            return False
        return bool(UNDO_WORDS.search(said)) or any(
            ACTION_WORDS[kind].search(said) for kind in ("complete", "reschedule", "rename", "delete"))

    @staticmethod
    def _tried_a_change(new_messages):
        """Whether the model called any tool other than listing the assignments."""
        return any(isinstance(m, ToolMessage) and m.name != "list_assignments" for m in new_messages)

    def _listing_messages(self):
        """A list_assignments call and its result, as if the model had looked the assignments up itself."""
        list_tool = next(t for t in self.tool_list if t.name == "list_assignments")
        args = {"only_incomplete": False}
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        return [AIMessage("", tool_calls=[{"name": list_tool.name, "args": args, "id": call_id, "type": "tool_call"}]),
                ToolMessage(list_tool.invoke(args), tool_call_id=call_id, name=list_tool.name)]

    def respond(self, user_input):
        """
        Runs one request through the agent.

        Returns:
            tuple: (reply_text, data_changed) where data_changed says whether any assignment was modified.
        """
        confirmation = self.confirm_pending(user_input)
        if confirmation:
            return confirmation
        self.tools.data_changed = False
        self.tools.user_message = user_input
        messages = self._recent_history() + [HumanMessage(user_input)]
        try:
            result = self.agent.invoke({"messages": messages}, {"recursion_limit": MAX_AGENT_STEPS})
            new_messages = result["messages"][len(messages):]
            if self._asks_for_change() and not self._tried_a_change(new_messages):
                # With no earlier messages the model doesn't know the assignment names, so it sometimes lists them
                # or asks which one instead of making the change. Show it the list and let it try once more.
                messages = messages + self._listing_messages()
                result = self.agent.invoke({"messages": messages}, {"recursion_limit": MAX_AGENT_STEPS})
                new_messages = result["messages"][len(messages):]
        except GraphRecursionError:
            # The model kept calling tools without finishing; keep the history as it was
            self.last_used_tools = False
            return "Sorry, I got stuck on that one. Could you try rephrasing it?", self.tools.data_changed

        # Tools return their result directly; join the successful ones in order. Tool errors (an unknown tool or
        # bad arguments) are for the model, not the user, so fall back to the model's text or a plain apology.
        tool_messages = [m for m in new_messages if isinstance(m, ToolMessage)]
        tool_replies = [m.content for m in tool_messages if m.status != "error"]
        self.last_used_tools = bool(tool_replies)
        if tool_replies:
            reply = "\n".join(tool_replies)
        else:
            reply = next((m.content for m in reversed(new_messages) if isinstance(m, AIMessage) and m.content), "")
            if tool_messages and not reply:
                reply = "Sorry, I couldn't do that. Type 'help' to see what I can do."
        reply = reply or "Sorry, I didn't catch that. Could you rephrase?"

        self.history = messages + new_messages
        return reply, self.tools.data_changed
