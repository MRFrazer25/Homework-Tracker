"""LLM assistant: a LangChain agent backed by a local Hugging Face model that can change assignments."""

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.core.assistant_tools import AssistantTools
from src.core.local_chat_model import LocalChatModel
from src.utils.settings_manager import DEFAULT_ASSISTANT_MODEL

# Kept constant so the model's KV cache for it can be reused on every request.
SYSTEM_PROMPT = (
    "You are a helpful assistant inside a homework tracker app. "
    "Use the tools to look up or change the user's assignments whenever they ask about them; "
    "never invent assignments or dates. Pass dates exactly as the user said them (e.g. 'friday', 'oct 10'). "
    "If the user just chats, reply briefly and warmly without using tools."
)

# How many past exchanges (user message plus everything after it) to send back to the model
HISTORY_EXCHANGES = 2


class Assistant:
    def __init__(self, assignment_manager, study_tips_generator, model_id=DEFAULT_ASSISTANT_MODEL, model=None):
        self.tools = AssistantTools(assignment_manager, study_tips_generator)
        self.model = model or LocalChatModel(model_id=model_id)
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

    @property
    def ready(self):
        return getattr(self.model, "loaded", True)

    def _recent_history(self):
        """The last few exchanges, cut at a user message so tool calls stay paired with their results."""
        starts = [i for i, m in enumerate(self.history) if isinstance(m, HumanMessage)]
        if len(starts) <= HISTORY_EXCHANGES:
            return list(self.history)
        return self.history[starts[-HISTORY_EXCHANGES]:]

    def respond(self, user_input):
        """
        Runs one request through the agent.

        Returns:
            tuple: (reply_text, data_changed) where data_changed says whether any assignment was modified.
        """
        self.tools.data_changed = False
        self.tools.user_message = user_input
        messages = self._recent_history() + [HumanMessage(user_input)]
        result = self.agent.invoke({"messages": messages})
        new_messages = result["messages"][len(messages):]

        # Tools return their result directly; join them in order. Otherwise use the model's text.
        tool_replies = [m.content for m in new_messages if isinstance(m, ToolMessage)]
        self.last_used_tools = bool(tool_replies)
        if tool_replies:
            reply = "\n".join(tool_replies)
        else:
            reply = next((m.content for m in reversed(new_messages) if isinstance(m, AIMessage) and m.content), "")
        reply = reply or "Sorry, I didn't catch that. Could you rephrase?"

        self.history = messages + new_messages
        return reply, self.tools.data_changed
