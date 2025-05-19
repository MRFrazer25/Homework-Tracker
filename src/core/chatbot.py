import json
from datetime import datetime
from transformers import pipeline
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import FileChatMessageHistory
import torch
import os

# Define the path for the new persistent chat log
PERSISTENT_CHAT_LOG_FILE = "data/persistent_chat_log.json"

# Model Configuration
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

# Define the path for chat history
CHAT_HISTORY_FILE = "data/chat_history.json"

class Chatbot:
    def __init__(self, assignment_manager, study_tips_generator):
        self.assignment_manager = assignment_manager
        self.study_tips_generator = study_tips_generator
        self.session_id = datetime.now().isoformat() # Unique ID for this app session
        
        # Initialize file-based chat message history
        # This will load history if the file exists, or create an empty one
        self.message_history = FileChatMessageHistory(file_path=CHAT_HISTORY_FILE)
        
        self.memory = ConversationBufferMemory(
            chat_history=self.message_history,
            return_messages=True
        )

        # Determine device (use GPU if available, otherwise CPU)
        self.device = 0 if torch.cuda.is_available() else -1
        print(f"Chatbot: Using device: {'cuda' if self.device == 0 else 'cpu'}")

        try:
            print(f"Chatbot: Loading intent detection model: {INTENT_MODEL_NAME}...")
            self.intent_classifier = pipeline(
                "zero-shot-classification",
                model=INTENT_MODEL_NAME,
                device=self.device
            )
            print("Chatbot: Intent detection model loaded.")
        except Exception as e:
            print(f"Error loading intent model {INTENT_MODEL_NAME}: {e}")
            self.intent_classifier = None
            print("Chatbot: Intent detection will be unavailable.")

        try:
            print(f"Chatbot: Loading emotion detection model: {EMOTION_MODEL_NAME}...")
            self.emotion_classifier = pipeline(
                "text-classification",
                model=EMOTION_MODEL_NAME,
                tokenizer=EMOTION_MODEL_NAME, # Explicitly specify tokenizer
                device=self.device
            )
            print("Chatbot: Emotion detection model loaded.")
        except Exception as e:
            print(f"Error loading emotion model {EMOTION_MODEL_NAME}: {e}")
            self.emotion_classifier = None
            print("Chatbot: Emotion detection will be unavailable.")

        self.command_handlers = {
            "list assignments": self._handle_list_assignments,
            "show assignments": self._handle_list_assignments,
            "get study tips": self._handle_get_study_tips,
            "show priorities": self._handle_show_priorities,
            "check schedule": self._handle_check_schedule,
            "bot status": lambda _: "I am functioning. My NLU and emotion models are " + \
                                   ("loaded." if self.intent_classifier and self.emotion_classifier else "not fully loaded."),
            "thank you": lambda _: "You're welcome!",
            "general greeting": lambda _: "Hello! How can I help you today?",
            "general farewell": lambda _: "Goodbye! Have a great day!",
            "ask for help": self._handle_ask_for_help,
        }

    def _detect_intent(self, text):
        if not self.intent_classifier:
            return "unknown_intent", 0.0
        try:
            # Simple classification of current input
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

    def get_response(self, user_input):
        # Save user input to memory
        self.memory.chat_memory.add_user_message(user_input)

        intent, intent_score = self._detect_intent(user_input)
        emotion = self._detect_emotion(user_input)

        response_prefix = EMOTION_ADJUSTMENTS.get(emotion, "")
        base_response = ""

        # Confidence threshold for intent
        CONFIDENCE_THRESHOLD = 0.5 # Lowered slightly for more flexibility with natural language

        if intent_score > CONFIDENCE_THRESHOLD and intent in self.command_handlers:
            handler = self.command_handlers[intent]
            # All remaining handlers are called without user_input directly
            base_response = handler(None) 
        elif "help" in user_input.lower():
            base_response = self._handle_ask_for_help(None)
        elif intent_score > 0.3: # Low confidence but some match
            base_response = f"I think you might be asking about '{intent}', but I'm not entirely sure. Could you try rephrasing or type 'help'?"
        else:
            base_response = "I'm not sure how to respond to that. Could you try rephrasing, or type 'help' for a list of commands?"


        final_response = response_prefix + base_response

        # Save bot response to memory
        self.memory.chat_memory.add_ai_message(final_response)
        
        # Save to persistent log for history viewer
        self._log_interaction_to_persistent_store(user_input, final_response)

        return final_response

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
            # Ensure data directory exists (should be handled by settings_manager too)
            data_dir = os.path.dirname(PERSISTENT_CHAT_LOG_FILE)
            if not os.path.exists(data_dir) and data_dir:
                os.makedirs(data_dir)

            if os.path.exists(PERSISTENT_CHAT_LOG_FILE) and os.path.getsize(PERSISTENT_CHAT_LOG_FILE) > 0:
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

    # Command Handler Methods
    def _handle_list_assignments(self, _):
        assignments = self.assignment_manager.get_assignments()
        if not assignments:
            return "You have no assignments. Well done!"
        
        response_lines = ["Here are your current assignments:"]
        for i, assign in enumerate(assignments):
            status = "Completed" if assign.get('completed', False) else "Incomplete"
            due_date_str = assign.get('due_date', 'N/A')
            if isinstance(due_date_str, datetime):
                due_date_str = due_date_str.strftime('%Y-%m-%d %H:%M')
            
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

        # Add a general study tip since get_enhanced_study_tips requires a specific assignment
        response_parts.append("General Tip: Remember to take breaks and prioritize your tasks!")
        
        return "\n\n".join(response_parts)

    def _handle_show_priorities(self, _):
        assignments = self.assignment_manager.get_assignments()
        active_assignments = [a for a in assignments if not a.get('completed', False)]

        if not active_assignments:
            return "No active assignments to prioritize!"

        high = [a['name'] for a in active_assignments if a.get('priority') == 'High']
        medium = [a['name'] for a in active_assignments if a.get('priority') == 'Medium']
        low = [a['name'] for a in active_assignments if a.get('priority') == 'Low']
        other = [a['name'] for a in active_assignments if a.get('priority') not in ['High', 'Medium', 'Low']]

        response_lines = ["Here's a breakdown of your assignment priorities:"]
        if high:
            response_lines.append("- High priority:")
            for name in high: response_lines.append(f"  - {name}")
        if medium:
            response_lines.append("- Medium priority:")
            for name in medium: response_lines.append(f"  - {name}")
        if low:
            response_lines.append("- Low priority:")
            for name in low: response_lines.append(f"  - {name}")
        if other:
            response_lines.append("- Other/Uncategorized:")
            for name in other: response_lines.append(f"  - {name}")
        
        if not (high or medium or low or other):
            return "You have active assignments, but none seem to have priority set."
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
        help_text = (
            "I can help you with the following:\n"
            "- list assignments\n"
            "- get study tips: for workload assessment and general advice\n"
            "- show priorities: to see a breakdown by priority\n"
            "- check schedule: for a suggested study plan\n"
            "- bot status: to check my system status\n"
            "(You can also use the 'History' button in the Chatbot tab to view past conversations.)\n\n"
            "You can also use the buttons and tabs in the application for detailed actions!"
        )
        return help_text
