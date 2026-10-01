"""A LangChain chat model that runs a Hugging Face model locally with tool calling.

langchain-huggingface's ChatHuggingFace doesn't pass tools to local models, doesn't parse
their tool calls, and rejects tool-result messages, so it can't drive an agent. This class
fills that gap: it renders the conversation and tool schemas with the model's own chat
template, parses the model's tool-call syntax back into LangChain tool calls, and reuses
the KV cache for the fixed system prompt so each request only processes the new text.
"""

import copy
import json
import re
import threading
import uuid
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import PrivateAttr


# --- Tool-call parsing ---

# End-of-turn markers the templates leave in the decoded text
_END_MARKERS = re.compile(r"<\|end_of_text\|>|<\|im_end\|>|<\|endoftext\|>")


def parse_tool_calls(text):
    """
    Parses tool calls in the JSON-in-tags format used by Granite and Qwen:
    <tool_call>{"name": ..., "arguments": {...}}</tool_call> (arguments may also be a JSON string).

    Returns:
        tuple: (visible_text, [(name, args), ...]); no calls are returned if any of them is malformed.
    """
    calls = []
    try:
        for blob in re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.S):
            data = json.loads(blob)
            for item in data if isinstance(data, list) else [data]:
                args = item.get("arguments", item.get("parameters", {}))
                calls.append((item["name"], json.loads(args) if isinstance(args, str) else args))
    except (ValueError, KeyError, AttributeError, TypeError):
        calls = []
    visible = text.split("<tool_call>", 1)[0] if calls else text
    return _END_MARKERS.sub("", visible).strip(), calls


class LocalChatModel(BaseChatModel):
    """Runs a Hugging Face causal LM on this machine. Load with load(), then use like any chat model."""

    model_id: str
    max_new_tokens: int = 200

    _tokenizer: Any = PrivateAttr(default=None)
    _model: Any = PrivateAttr(default=None)
    _prefix_cache: Any = PrivateAttr(default=None)  # (prompt_prefix_text, past_key_values)
    _lock: Any = PrivateAttr(default_factory=threading.Lock)

    @property
    def _llm_type(self) -> str:
        return "local-huggingface"

    def load(self):
        """Downloads (first run only) and loads the model. Slow; call from a background thread."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForCausalLM.from_pretrained(self.model_id, dtype=torch.float32).eval()
        return self

    @property
    def loaded(self):
        return self._model is not None

    def warm_up(self, system_prompt, tools):
        """Builds the prompt-prefix cache ahead of time so the user's first message doesn't pay for it."""
        formatted_tools = [convert_to_openai_tool(t) for t in tools]
        with self._lock:
            self._cached_prefix([{"role": "system", "content": system_prompt}], formatted_tools)

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=[convert_to_openai_tool(t) for t in tools], **kwargs)

    # --- Message conversion ---
    @staticmethod
    def _to_template_messages(messages):
        converted = []
        for m in messages:
            if isinstance(m, SystemMessage):
                converted.append({"role": "system", "content": m.content})
            elif isinstance(m, HumanMessage):
                converted.append({"role": "user", "content": m.content})
            elif isinstance(m, AIMessage):
                entry = {"role": "assistant", "content": m.content or ""}
                if m.tool_calls:
                    entry["tool_calls"] = [{"type": "function", "id": tc["id"],
                                            "function": {"name": tc["name"], "arguments": tc["args"]}}
                                           for tc in m.tool_calls]
                converted.append(entry)
            elif isinstance(m, ToolMessage):
                converted.append({"role": "tool", "name": m.name, "tool_call_id": m.tool_call_id,
                                  "content": m.content})
            else:
                raise ValueError(f"Unsupported message type: {type(m).__name__}")
        return converted

    def _render(self, template_messages, tools):
        return self._tokenizer.apply_chat_template(
            template_messages, tools=tools or None, tokenize=False,
            add_generation_prompt=True, enable_thinking=False)

    def _cached_prefix(self, template_messages, tools):
        """
        Returns (prefix_ids, kv_cache) for the part of the prompt that never changes (system prompt
        and tool schemas). Found by rendering two different user turns and taking the common start.
        """
        system = [m for m in template_messages if m["role"] == "system"][:1]
        probe_a = self._render(system + [{"role": "user", "content": "a"}], tools)
        probe_b = self._render(system + [{"role": "user", "content": "b"}], tools)
        length = next((i for i, (x, y) in enumerate(zip(probe_a, probe_b)) if x != y), 0)
        # Back off to a line boundary so the prefix tokenizes the same way inside the full prompt
        prefix_text = probe_a[:probe_a.rfind("\n", 0, length) + 1]

        if self._prefix_cache and self._prefix_cache[0] == prefix_text:
            return self._prefix_cache[1:]
        import torch
        from transformers import DynamicCache
        prefix_ids = self._tokenizer(prefix_text, return_tensors="pt", add_special_tokens=False)["input_ids"]
        cache = DynamicCache(config=self._model.config)
        if prefix_ids.shape[1]:
            with torch.inference_mode():
                self._model(input_ids=prefix_ids, past_key_values=cache, use_cache=True)
        self._prefix_cache = (prefix_text, prefix_ids[0], cache)
        return self._prefix_cache[1:]

    def _generate(self, messages: list[BaseMessage], stop: Optional[list[str]] = None,
                  run_manager=None, tools: Optional[list] = None, **kwargs: Any) -> ChatResult:
        if not self.loaded:
            raise RuntimeError("Model not loaded yet; call load() first.")
        import torch

        template_messages = self._to_template_messages(messages)
        prompt = self._render(template_messages, tools)
        with self._lock:  # One generation at a time; the KV cache isn't thread-safe
            prefix_ids, prefix_cache = self._cached_prefix(template_messages, tools)
            inputs = self._tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
            generate_kwargs = {}
            n = len(prefix_ids)
            # Reuse the cache only if the prompt really starts with the cached tokens (and has more after them)
            if 0 < n < inputs["input_ids"].shape[1] and torch.equal(inputs["input_ids"][0, :n], prefix_ids):
                generate_kwargs["past_key_values"] = copy.deepcopy(prefix_cache)
            with torch.inference_mode():
                output = self._model.generate(**inputs, max_new_tokens=self.max_new_tokens,
                                              do_sample=False, **generate_kwargs)
        new_tokens = output[0][inputs["input_ids"].shape[1]:]
        raw = self._tokenizer.decode(new_tokens, skip_special_tokens=False)
        text, calls = parse_tool_calls(raw)
        if not calls:
            text = self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        tool_calls = [{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:12]}", "type": "tool_call"}
                      for name, args in calls]
        message = AIMessage(content=text, tool_calls=tool_calls,
                            response_metadata={"raw_output": raw, "new_tokens": len(new_tokens)})
        return ChatResult(generations=[ChatGeneration(message=message)])
