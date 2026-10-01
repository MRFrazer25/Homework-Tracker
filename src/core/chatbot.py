import json
import re
import threading
from datetime import datetime
from src.utils.paths import DATA_DIR
from src.utils.helpers import PRIORITY_RANK, ALLOWED_PRIORITIES

# Define the path for the persistent chat log (read by the chat history dialog)
PERSISTENT_CHAT_LOG_FILE = DATA_DIR / "persistent_chat_log.json"

# --- Model Configuration ---
# For intent detection: Using a smaller NLI model for zero-shot classification
# Other options: 'valhalla/distilbart-mnli-12-3', 'facebook/bart-large-mnli' (larger)
INTENT_MODEL_NAME = "cross-encoder/nli-distilroberta-base"
# For emotion detection:
EMOTION_MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"

# Define your application's intents
# These will be used as candidate labels for the zero-shot classifier
INTENT_LABELS = [
    "list assignments",
    "show assignments",
    "get study tips",
    "show priorities",
    "ask for help",
    "general greeting",
    "general farewell",
    "check schedule",
    "thank you",
    "bot status",
    # "show history" will now be handled by a dialog, not an intent for the bot to respond to directly.
    # We might keep a simpler "show current session history" if desired, but problem asks for ChatGPT-like history.
]

# Define how emotions should modify responses (simple approach)
EMOTION_ADJUSTMENTS = {
    "joy": "That's great to hear! ",
    "sadness": "I'm sorry to hear that. ",
    "anger": "I understand you might be frustrated. ",
    "fear": "No need to worry, I'm here to help. ",
    "surprise": "Oh, really? ",
    "disgust": "Hmm, I see. ",
    "neutral": ""
}

# Emotions whose prefix reads naturally in front of an action result ("That's great to hear! Marked ... as done.")
TOOL_REPLY_EMOTIONS = {"joy", "sadness", "anger", "fear"}

# A bare request for help always shows the built-in examples
HELP_REQUEST = re.compile(r"\s*(help|\?|commands|what can you do)\s*[.!?]*\s*", re.IGNORECASE)

# Keyword regex -> intent fallback used when the intent model isn't available. Checked in order.
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
    Two layers: fast Hugging Face classifiers (intent + emotion) that answer fixed commands, and an
    optional LLM agent (see assistant.py) that understands free-form requests and can change assignments.
    The agent handles requests once loaded; the classifiers cover the time before that and any failure.
    """
    def __init__(self, assignment_manager, study_tips_generator, assistant_model=None):
        self.assignment_manager = assignment_manager
        self.study_tips_generator = study_tips_generator
        self.session_id = datetime.now().isoformat() # Unique ID for this app session

        # Models are loaded in the background by start_loading_models() so the window opens immediately.
        self.intent_classifier = None
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
            "bot status": lambda _: "I am functioning. My NLU and emotion models are " + \
                                   ("loaded" if self.intent_classifier and self.emotion_classifier else "not fully loaded") + \
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
            print(f"Chatbot: Loading intent detection model: {INTENT_MODEL_NAME}...")
            self.intent_classifier = pipeline(
                "zero-shot-classification",
                model=INTENT_MODEL_NAME,
                device=device
            )
            print("Chatbot: Intent detection model loaded.")
        except Exception as e:
            print(f"Error loading intent model {INTENT_MODEL_NAME}: {e}")
            print("Chatbot: Intent detection will be unavailable.")

        try:
            print(f"Chatbot: Loading emotion detection model: {EMOTION_MODEL_NAME}...")
            self.emotion_classifier = pipeline(
                "text-classification",
                model=EMOTION_MODEL_NAME,
                tokenizer=EMOTION_MODEL_NAME, # Explicitly specify tokenizer
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

    def _detect_intent(self, text):
        if not self.intent_classifier:
            return "unknown_intent", 0.0
        try:
            result = self.intent_classifier(text, INTENT_LABELS, multi_label=False) # multi_label=False if single intent expected
            return result['labels'][0], result['scores'][0]
        except Exception as e:
            print(f"Error during intent detection: {e}")
            return "unknown_intent", 0.0

    def _detect_emotion(self, text):
        if not self.emotion_classifier:
            return "neutral"
        try:
            results = self.emotion_classifier(text)
            # The model might return a list of dictionaries if top_k > 1 or no top_k specified
            # Assuming the first result is the most relevant
            if isinstance(results, list) and results:
                 # Map model labels (e.g., 'LABEL_0') to human-readable labels if necessary
                 # For j-hartmann/emotion-english-distilroberta-base, labels are directly 'sadness', 'joy', etc.
                return results[0]['label'].lower() # ensure lowercase
            return "neutral" # fallback
        except Exception as e:
            print(f"Error during emotion detection: {e}")
            return "neutral"

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

        if self.assistant and not HELP_REQUEST.fullmatch(user_input):
            try:
                reply, data_changed = self.assistant.respond(user_input)
                print(f"Chatbot Debug: Input='{user_input}', Assistant used tools={self.assistant.last_used_tools}, Emotion='{emotion}'")
                # Tool results are templated text, so the emotion model adds the tone; the LLM's own replies already have it
                use_prefix = self.assistant.last_used_tools and emotion in TOOL_REPLY_EMOTIONS
                final_response = (response_prefix + reply) if use_prefix else reply
                self._log_interaction_to_persistent_store(user_input, final_response)
                return final_response, data_changed
            except Exception as e:
                print(f"Assistant error, falling back to classic replies: {e}")

        if HELP_REQUEST.fullmatch(user_input):
            final_response = self._handle_ask_for_help(None)
            self._log_interaction_to_persistent_store(user_input, final_response)
            return final_response, False

        intent, intent_score = self._detect_intent(user_input)
        print(f"Chatbot Debug: Input='{user_input}', Detected Intent='{intent}' (Score: {intent_score:.2f}), Emotion='{emotion}'")
        base_response = ""

        # Confidence threshold for intent
        CONFIDENCE_THRESHOLD = 0.5 # Lowered slightly for more flexibility with natural language
        # Used when the model is unavailable or not confident enough
        keyword_intent = self._match_keyword_intent(user_input)

        if intent_score > CONFIDENCE_THRESHOLD and intent in self.command_handlers:
            handler = self.command_handlers[intent]
            # All remaining handlers are called without user_input directly
            base_response = handler(None)
        elif keyword_intent:
            base_response = self.command_handlers[keyword_intent](None)
        elif "help" in user_input.lower():
            base_response = self._handle_ask_for_help(None)
        elif not self.models_ready.is_set():
            base_response = ("I'm still loading my language models (the first run downloads them, which can take a minute). "
                             "Simple commands like 'list assignments', 'priorities', 'schedule', or 'help' work in the meantime.")
        elif intent_score > 0.3: # Low confidence but some match
            base_response = f"I think you might be asking about '{intent}', but I'm not entirely sure. Could you try rephrasing or type 'help'?"
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
                    "- \"What do I still have to do?\" or \"Make me a study plan\"\n"
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
