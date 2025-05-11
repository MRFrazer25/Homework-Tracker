import tkinter as tk
from tkinter import ttk, scrolledtext
from src.core.chatbot import HomeworkChatbot # Assuming core.chatbot has the logic

class ChatbotTab(ttk.Frame):
    """Tab for interacting with the AI Chatbot."""
    def __init__(self, parent, data_handler, assignments_provider, app_callbacks=None): # Added app_callbacks
        """
        Initializes the Chatbot tab.

        Args:
            parent: The parent widget (notebook).
            data_handler: Instance of DataHandler for chatbot's internal logic.
            assignments_provider: Callable to get the list of current assignments.
            app_callbacks (dict, optional): Dictionary of callbacks from the main app.
                                            Used here to get theme settings.
        """
        super().__init__(parent)
        self.chatbot = HomeworkChatbot(data_handler) 
        self.assignments_provider = assignments_provider 
        self.app_callbacks = app_callbacks if app_callbacks else {}
        
        self.theme_settings_provider = self.app_callbacks.get('get_theme_settings', lambda: {})
        self.chat_font_details = ('Helvetica', 10) # Store base font details

        self.chat_display = None
        self.message_entry = None
        
        self.setup_ui()
        self.configure_styles() # Apply initial styles for ScrolledText

    def setup_ui(self):
        """Creates and lays out the UI elements for the Chatbot tab."""
        current_theme = self.theme_settings_provider()
        text_fg = current_theme.get("entry_fg", "black") # Default to black if not found
        text_bg = current_theme.get("entry_bg", "white") # Default to white

        # Chat display area (ScrolledText is a tk.Text widget with a scrollbar)
        self.chat_display = scrolledtext.ScrolledText(
            self, 
            wrap=tk.WORD, 
            state='disabled', # Start as read-only
            height=15,
            font=self.chat_font_details, # Use instance variable
            background=text_bg,
            foreground=text_fg,
            insertbackground=text_fg, # Cursor color for text widget
            relief=tk.SUNKEN, # Match TEntry relief for consistency
            borderwidth=1
        )
        self.chat_display.pack(pady=10, padx=10, fill="both", expand=True)

        # Define tags for styling sender messages - Updated vibrant colors
        bold_chat_font = (self.chat_font_details[0], self.chat_font_details[1], "bold")
        self.chat_display.tag_configure("You", foreground="#4169E1", font=bold_chat_font) # RoyalBlue
        self.chat_display.tag_configure("Bot", foreground="#2E8B57", font=bold_chat_font) # SeaGreen
        # These colors are chosen for vibrancy on a light theme.

        # Input frame
        input_frame = ttk.Frame(self) # This will pick up TFrame style
        input_frame.pack(pady=(0, 10), padx=10, fill="x")

        self.message_entry = ttk.Entry(input_frame, font=self.chat_font_details) # ttk.Entry will use theme
        self.message_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.message_entry.bind("<Return>", self.send_message) # Bind Enter key to send message

        send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        send_button.pack(side="right", padx=(5, 0))
        
        # Display initial welcome message from the chatbot
        self.add_message_to_display(self.chatbot.get_help_message(), "Bot")

    def configure_styles(self):
        """Applies theme-specific styles to non-ttk widgets like ScrolledText."""
        current_theme = self.theme_settings_provider()
        text_fg = current_theme.get("entry_fg", "black")
        text_bg = current_theme.get("entry_bg", "white")

        if self.chat_display:
            self.chat_display.config(background=text_bg, foreground=text_fg, insertbackground=text_fg)
            # Update tag colors if they need to be theme-dependent
            # Use the stored base font details to correctly apply bold style.
            bold_chat_font = (self.chat_font_details[0], self.chat_font_details[1], "bold")
            self.chat_display.tag_configure("You", foreground="#4169E1", font=bold_chat_font)
            self.chat_display.tag_configure("Bot", foreground="#2E8B57", font=bold_chat_font)


    def on_theme_changed(self):
        """Callback for when the application theme changes."""
        self.configure_styles()


    def send_message(self, event=None):
        """Handles sending a message from the user to the chatbot."""
        user_message = self.message_entry.get()
        if not user_message.strip(): # Don't send empty or whitespace-only messages
            return 

        self.add_message_to_display(user_message, "You")
        self.message_entry.delete(0, tk.END) # Clear the input field
        
        # Provide current assignments context to the chatbot
        current_assignments = self.assignments_provider()
        bot_response = self.chatbot.process_message(user_message, current_assignments)
        self.add_message_to_display(bot_response, "Bot")

    def add_message_to_display(self, message, sender):
        """Adds a message to the chat display area with sender-specific styling."""
        if not self.chat_display:
            return
            
        self.chat_display.config(state='normal') # Temporarily enable editing to insert text
        
        if self.chat_display.index('end-1c') != "1.0": # Add newline if not the first message
             self.chat_display.insert(tk.END, "\n\n") # Add some space between messages

        # Insert sender and message with the appropriate tag
        self.chat_display.insert(tk.END, f"{sender}: ", (sender,)) 
        self.chat_display.insert(tk.END, message)
        
        self.chat_display.config(state='disabled') # Revert to read-only
        self.chat_display.see(tk.END) # Auto-scroll to the latest message


if __name__ == '__main__':
    # Example usage for testing this tab independently
    root = tk.Tk()
    root.title("Chatbot Tab Test")

    # For testing, we need a mock DataHandler, assignments_provider, and theme_provider
    class MockDataHandler:
        def load_assignments(self): return [] 
        def save_assignments(self, data): pass 

    mock_data_handler = MockDataHandler()
    
    from datetime import datetime, timedelta 
    sample_assignments = [
        {'name': 'Test HW', 'due_date': datetime.now(), 'priority': 'High', 'class': 'Test', 'difficulty': 5, 'completed': False}
    ]
    def get_sample_assignments():
        return sample_assignments
    
    # Mock theme provider for testing
    def get_mock_theme_settings():
        return {"entry_bg": "white", "entry_fg": "black"} # Basic light theme defaults

    mock_app_callbacks = {'get_theme_settings': get_mock_theme_settings}

    # Pass all required arguments, including app_callbacks
    tab = ChatbotTab(root, mock_data_handler, get_sample_assignments, mock_app_callbacks)
    tab.pack(expand=True, fill='both')
    root.mainloop()
