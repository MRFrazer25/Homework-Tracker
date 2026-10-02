import json
import re
import threading
from datetime import datetime
from src.utils.paths import DATA_DIR
from src.utils.helpers import PRIORITY_RANK, ALLOWED_PRIORITIES

# Define the path for the persistent chat log (read by the chat history dialog)
PERSISTENT_CHAT_LOG_FILE = DATA_DIR / "persistent_chat_log.json"

# --- Model Configuration ---
# Emotion detection: RoBERTa fine-tuned on Google's GoEmotions dataset (MIT license). Pinned to the tested commit
# so a changed upstream repo can't alter what the app loads, and loaded from safetensors only (no pickle code).
EMOTION_MODEL_NAME = "SamLowe/roberta-base-go_emotions"
EMOTION_MODEL_REVISION = "d75048347613a25d77de8cf6412eaae9fa7b26be"

# GoEmotions scores 28 emotions independently; these are the ones that change a reply's tone
GO_EMOTION_TONES = {
    "fear": "fear", "nervousness": "fear",
    "sadness": "sadness", "disappointment": "sadness", "grief": "sadness", "remorse": "sadness",
    "anger": "anger", "annoyance": "anger",
    "joy": "joy", "excitement": "joy", "relief": "joy", "pride": "joy",
}
# Minimum score before an emotion changes the tone (tuned on homework-style messages: no false alarms)
EMOTION_MIN_CONFIDENCE = 0.35
# Stress is the most common feeling in homework talk, but the model often misses the word itself
STRESS_WORDS = re.compile(r"\b(stress\w*|overwhelm\w*|anxious|anxiety|panic\w*|freak\w* out)\b", re.IGNORECASE)

# How each tone changes a reply
EMOTION_ADJUSTMENTS = {
    "joy": "That's great to hear! ",
    "sadness": "I'm sorry to hear that. ",
    "anger": "I understand you might be frustrated. ",
    "fear": "No need to worry, I'm here to help. ",
    "neutral": ""
}

# Emotions whose prefix reads naturally in front of an action result ("That's great to hear! Marked ... as done.")
TOOL_REPLY_EMOTIONS = {"sadness", "anger", "fear"}

# A bare request for help always shows the built-in examples
HELP_REQUEST = re.compile(r"\s*(help|\?|commands|what can you do)\s*[.!?]*\s*", re.IGNORECASE)

# Pure small talk gets a friendly reply without involving the agent, which could otherwise act on old context
_SMALL_TALK_PHRASE = (r"(hi|hey|hello|yo|sup|good (morning|afternoon|evening)|how('?s| is) it going|how are (you|u)"
                      r"|what'?s up|thanks?( you)?|thank u|thx|ty|bye|goodbye|see (you|ya)( later)?|cool|ok(ay)?|nice)")
SMALL_TALK = re.compile(rf"(\s*{_SMALL_TALK_PHRASE}\s*(there|so much|a lot|man|bro|dude)?[\s!.,?]*)+", re.IGNORECASE)

# Keyword regex -> command, used for fixed commands while the assistant loads or if it's disabled. Checked in order.
KEYWORD_INTENTS = [
    (r"\btips?\b", "get study tips"),
    (r"\bpriorit", "show priorities"),
    (r"\b(schedule|plan)\b", "check schedule"),
    (r"\b(assignments?|homework|tasks?)\b", "list assignments"),
    (r"\bstatus\b", "bot status"),
    (r"\bthanks?\b|\bthank you\b", "thank you"),
    (r"\b(bye|goodbye)\b", "general farewell"),
    (r"\b(hi|hello|hey)\b", "general greeting"),
]

class Chatbot:
    """
    An LLM agent (see assistant.py) handles free-form requests and changes assignments. Keyword-matched fixed
    commands cover the time before it loads and any failure, and an emotion classifier sets the reply's tone.
    """
    def __init__(self, assignment_manager, study_tips_generator, assistant_model=None):
        self.assignment_manager = assignment_manager
        self.study_tips_generator = study_tips_generator
        self.session_id = datetime.now().isoformat() # Unique ID for this app session

        # Models are loaded in the background by start_loading_models() so the window opens immediately.
        self.emotion_classifier = None
        self.models_ready = threading.Event()

        # LLM agent (None disables it, e.g. on machines without enough memory)
        self.assistant_model = assistant_model
        self.assistant = None
        self.assistant_status = "disabled" if not assistant_model else "waiting to load"

        self.command_handlers = {
            "list assignments": self._handle_list_assignments,
            "show assignments": self._handle_list_assignments, # Alias
            "get study tips": self._handle_get_study_tips,
            "show priorities": self._handle_show_priorities,
            "check schedule": self._handle_check_schedule,
            "bot status": lambda _: "I'm working. Emotion detection is " + \
                                   ("loaded" if self.emotion_classifier else "not loaded") + \
                                   f", and the AI assistant is {self.assistant_status}.",
            "thank you": lambda _: "You're welcome!",
            "general greeting": lambda _: "Hello! How can I help you today?",
            "general farewell": lambda _: "Goodbye! Have a great day!",
            "ask for help": self._handle_ask_for_help,
        }

    def start_loading_models(self):
        """Loads the NLU models on a daemon thread. get_response() works (with limited replies) until they finish."""
        threading.Thread(target=self._load_models, daemon=True).start()

    def _load_models(self):
        try:
            # Imported here because torch/transformers take several seconds to import.
            import torch
            from transformers import pipeline
        except Exception as e:
            print(f"Chatbot: Could not import transformers/torch: {e}")
            self.models_ready.set()
            return

        # Determine device (use GPU if available, otherwise CPU)
        device = 0 if torch.cuda.is_available() else -1
        print(f"Chatbot: Using device: {'cuda' if device == 0 else 'cpu'}")

        try:
            print(f"Chatbot: Loading emotion detection model: {EMOTION_MODEL_NAME}...")
            self.emotion_classifier = pipeline(
                "text-classification",
                model=EMOTION_MODEL_NAME,
                revision=EMOTION_MODEL_REVISION,
                model_kwargs={"use_safetensors": True},
                top_k=None,  # Score every emotion, not just the top one
                device=device
            )
            print("Chatbot: Emotion detection model loaded.")
        except Exception as e:
            print(f"Error loading emotion model {EMOTION_MODEL_NAME}: {e}")
            print("Chatbot: Emotion detection will be unavailable.")

        self.models_ready.set()
        self._load_assistant()

    def _load_assistant(self):
        """Loads the LLM agent after the (much faster) classifiers, so simple commands work sooner."""
        if not self.assistant_model:
            return
        self.assistant_status = "loading"
        try:
            print(f"Chatbot: Loading assistant model: {self.assistant_model}...")
            from src.core.assistant import Assistant  # Imports langchain; kept off the startup path
            assistant = Assistant(self.assignment_manager, self.study_tips_generator, model_id=self.assistant_model)
            assistant.load()
            self.assistant = assistant
            self.assistant_status = "ready"
            print("Chatbot: Assistant model loaded.")
        except Exception as e:
            self.assistant_status = "unavailable"
            print(f"Error loading assistant model {self.assistant_model}: {e}")

    def _detect_emotion(self, text):
        """Returns the reply tone for a message: 'joy', 'sadness', 'anger', 'fear', or 'neutral'."""
        tone = "neutral"
        if self.emotion_classifier:
            try:
                results = self.emotion_classifier(text)
                if results and isinstance(results[0], list):  # One list of scores per input text
                    results = results[0]
                toned = [r for r in results if r['label'] in GO_EMOTION_TONES]
                best = max(toned, key=lambda r: r.get('score', 1.0), default=None)
                # Weak readings are often wrong (e.g. "urgent" read as fear), so only act on clear emotions
                if best and best.get('score', 1.0) >= EMOTION_MIN_CONFIDENCE:
                    tone = GO_EMOTION_TONES[best['label']]
            except Exception as e:
                print(f"Error during emotion detection: {e}")
        if tone == "neutral" and STRESS_WORDS.search(text):
            tone = "fear"
        return tone

    @staticmethod
    def _small_talk_reply(text):
        lowered = text.lower()
        if re.search(r"\b(thanks?|thank u|thx|ty)\b", lowered):
            return "You're welcome!"
        if re.search(r"\b(bye|goodbye|see (you|ya))\b", lowered):
            return "Goodbye! Good luck with your work!"
        if re.search(r"\b(how('?s| is) it going|how are (you|u)|what'?s up)\b", lowered):
            return "I'm doing well, thanks for asking! What can I help you with?"
        if re.search(r"\b(hi|hey|hello|yo|sup|good (morning|afternoon|evening))\b", lowered):
            return "Hey! How can I help with your assignments today?"
        return "Got it! Let me know if you need anything."

    def _match_keyword_intent(self, text):
        """Simple keyword fallback used while the models load, if they failed to load, or when they're unsure."""
        lowered = text.lower()
        for pattern, intent in KEYWORD_INTENTS:
            if re.search(pattern, lowered):
                return intent
        return None

    def get_response(self, user_input):
        """
        Returns:
            tuple: (response_text, data_changed) where data_changed is True if assignments were modified.
        """
        emotion = self._detect_emotion(user_input)
        response_prefix = EMOTION_ADJUSTMENTS.get(emotion, "")

        # A pending delete is answered (or cancelled) by whatever comes next, before anything else runs
        if self.assistant:
            confirmation = self.assistant.confirm_pending(user_input)
            if confirmation:
                self._log_interaction_to_persistent_store(user_input, confirmation[0])
                return confirmation

        if SMALL_TALK.fullmatch(user_input):
            final_response = self._small_talk_reply(user_input)
            self._log_interaction_to_persistent_store(user_input, final_response)
            return final_response, False

        if self.assistant and not HELP_REQUEST.fullmatch(user_input):
            try:
                reply, data_changed = self.assistant.respond(user_input)
                print(f"Chatbot Debug: Input='{user_input}', Assistant used tools={self.assistant.last_used_tools}, Emotion='{emotion}'")
                # Tool results are templated text, so the emotion model adds the tone; the LLM's own replies already have it
                # "That's great to hear!" only fits finishing something; the other emotions fit any action
                use_prefix = self.assistant.last_used_tools and (
                    emotion in TOOL_REPLY_EMOTIONS or (emotion == "joy" and " as done." in reply))
                final_response = (response_prefix + reply) if use_prefix else reply
                self._log_interaction_to_persistent_store(user_input, final_response)
                return final_response, data_changed
            except Exception as e:
                print(f"Assistant error, falling back to classic replies: {e}")

        if HELP_REQUEST.fullmatch(user_input):
            final_response = self._handle_ask_for_help(None)
            self._log_interaction_to_persistent_store(user_input, final_response)
            return final_response, False

        keyword_intent = self._match_keyword_intent(user_input)
        print(f"Chatbot Debug: Input='{user_input}', Command='{keyword_intent}', Emotion='{emotion}'")

        if keyword_intent:
            base_response = self.command_handlers[keyword_intent](None)
        elif "help" in user_input.lower():
            base_response = self._handle_ask_for_help(None)
        elif not self.models_ready.is_set() or self.assistant_status in ("waiting to load", "loading"):
            base_response = ("I'm still loading my language models (the first run downloads them, which can take a few minutes). "
                             "Simple commands like 'list assignments', 'priorities', 'schedule', or 'help' work in the meantime.")
        else:
            base_response = "I'm not sure how to respond to that. Could you try rephrasing, or type 'help' for a list of commands?"


        final_response = response_prefix + base_response

        # Save to persistent log for history viewer
        self._log_interaction_to_persistent_store(user_input, final_response)

        return final_response, False

    def _log_interaction_to_persistent_store(self, user_input, bot_response):
        """Logs the user input and bot response to the persistent JSON log file."""
        log_entry = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "bot_response": bot_response
        }
        
        try:
            log_data = []
            PERSISTENT_CHAT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

            if PERSISTENT_CHAT_LOG_FILE.exists() and PERSISTENT_CHAT_LOG_FILE.stat().st_size > 0:
                with open(PERSISTENT_CHAT_LOG_FILE, 'r', encoding='utf-8') as f:
                    try:
                        log_data = json.load(f)
                        if not isinstance(log_data, list):
                            log_data = [] # Start fresh if format is incorrect
                    except json.JSONDecodeError:
                        log_data = [] # Start fresh if file is corrupted
            
            log_data.append(log_entry)
            
            with open(PERSISTENT_CHAT_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=4)
                
        except Exception as e:
            print(f"Error logging to persistent chat store: {e}")

    # --- Command Handler Methods ---
    def _handle_list_assignments(self, _):
        assignments = self.assignment_manager.get_assignments()
        if not assignments:
            return "You have no assignments. Well done!"
        
        response_lines = ["Here are your current assignments:"]
        for i, assign in enumerate(assignments):
            status = "Completed" if assign.get('completed', False) else "Incomplete"
            due_date_str = assign.get('due_date', 'N/A')
            if isinstance(due_date_str, datetime):
                due_date_str = due_date_str.strftime('%Y-%m-%d')
            
            response_lines.append(f"{i+1}. {assign['name']}:")
            response_lines.append(f"   - Due: {due_date_str}")
            response_lines.append(f"   - Priority: {assign.get('priority', 'N/A')}")
            response_lines.append(f"   - Status: {status}")
        return "\n".join(response_lines)

    def _handle_get_study_tips(self, _):
        active_assignments = [
            a for a in self.assignment_manager.get_assignments() if not a.get('completed')
        ]
        if not active_assignments:
            return "You have no active assignments! Great job. Enjoy your free time!"

        # Use get_workload_warning as it exists and is suitable
        workload_warnings = self.study_tips_generator.get_workload_warning(active_assignments)
        
        response_parts = []
        if workload_warnings:
            response_parts.append("Workload Assessment:\n" + "\n".join(workload_warnings))
        else:
            response_parts.append("Your workload seems manageable right now.")

        # Tailor tips to the most pressing assignment: highest priority first, then earliest due date.
        focus = min(
            active_assignments,
            key=lambda a: (-PRIORITY_RANK.get(a.get('priority'), 0),
                           a['due_date'] if isinstance(a.get('due_date'), datetime) else datetime.max)
        )
        tips = self.study_tips_generator.get_enhanced_study_tips(active_assignments, focus)
        response_parts.append(f"Tips for '{focus.get('name', 'your next assignment')}':\n" +
                              "\n".join(f"- {tip}" for tip in tips[:4]))

        return "\n\n".join(response_parts)

    def _handle_show_priorities(self, _):
        assignments = self.assignment_manager.get_assignments()
        active_assignments = [a for a in assignments if not a.get('completed', False)]

        if not active_assignments:
            return "No active assignments to prioritize!"

        response_lines = ["Here's a breakdown of your assignment priorities:"]
        # Most urgent first
        for priority in reversed(ALLOWED_PRIORITIES):
            names = [a['name'] for a in active_assignments if a.get('priority') == priority]
            if names:
                response_lines.append(f"- {priority} priority:")
                response_lines.extend(f"  - {name}" for name in names)

        other = [a['name'] for a in active_assignments if a.get('priority') not in ALLOWED_PRIORITIES]
        if other:
            response_lines.append("- Other/Uncategorized:")
            response_lines.extend(f"  - {name}" for name in other)

        return "\n".join(response_lines)

    def _handle_check_schedule(self, _):
        active_assignments = [
            a for a in self.assignment_manager.get_assignments() if not a.get('completed')
        ]
        if not active_assignments:
            return "Your schedule looks clear! No upcoming assignments."
        
        suggestion_list = self.study_tips_generator.generate_schedule_suggestion(active_assignments)
        if isinstance(suggestion_list, list):
            return "\n".join(suggestion_list)
        return str(suggestion_list) # Fallback if it's not a list for some reason

    def _handle_ask_for_help(self, _):
        if self.assistant:
            return ("Just tell me what you need in plain English, for example:\n"
                    "- \"Add a math quiz due Friday, high priority\"\n"
                    "- \"I finished the lab report\"\n"
                    "- \"Push my essay to next Monday\"\n"
                    "- \"What's due this week?\" or \"Anything for chemistry?\"\n"
                    "- \"Rename the essay to essay draft\" or \"Move the lab to my biology class\"\n"
                    "- \"Delete the art sketches\" (I'll ask you to confirm first)\n"
                    "- \"Make me a study plan\"\n"
                    "(The 'History' button shows past conversations.)")
        help_text = (
            "I can help you with the following:\n"
            "- List assignments\n"
            "- Get study tips: for workload assessment and general advice\n"
            "- Show priorities: to see a breakdown by priority\n"
            "- Check schedule: for a suggested study plan\n"
            "- Bot status: to check my system status\n"
            "(You can also use the 'History' button in the Chatbot tab to view past conversations.)\n\n"
            "You can also use the buttons and tabs in the application for detailed actions!"
        )
        return help_text
