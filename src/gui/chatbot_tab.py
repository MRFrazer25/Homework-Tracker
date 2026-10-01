import queue
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from .chat_history_dialog import ChatHistoryDialog

class ChatbotTab(ttk.Frame):
    def __init__(self, parent, app_instance, chatbot_instance, assignment_manager, study_tips_generator):
        super().__init__(parent)
        self.app_instance = app_instance # To access main app methods if needed
        self.chatbot = chatbot_instance # Use the passed chatbot instance
        self.assignment_manager = assignment_manager
        self.study_tips_generator = study_tips_generator
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._create_widgets()
        # Call on_theme_changed with the initial theme state
        if hasattr(self.app_instance, 'is_dark_theme'):
             self.on_theme_changed(self.app_instance.is_dark_theme())
        else: # Fallback if app_instance isn't fully ready (shouldn't happen in normal flow)
            self.on_theme_changed(False)

    def _create_widgets(self):
        # Main frame for chat area and input
        chat_frame = ttk.Frame(self, padding="10")
        chat_frame.grid(row=0, column=0, sticky="nsew")
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        # Chat display area
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            state='disabled',
            height=15,
            font=("Segoe UI", 11)
        )
        self.chat_display.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0,10))
        # Initial tag configurations will be overridden by on_theme_changed

        # Input field
        self.input_field = ttk.Entry(chat_frame, font=("Segoe UI", 11))
        self.input_field.grid(row=1, column=0, sticky="ew", padx=(0,10))
        self.input_field.bind("<Return>", self._on_send_message)

        # Button Frame for Send and History
        action_button_frame = ttk.Frame(chat_frame)
        action_button_frame.grid(row=1, column=1, sticky="ew")

        # ttkbootstrap provides styles like 'Accent.TButton' or 'primary.TButton', 'success.TButton' etc.
        # We can use a default style and let the theme handle it, or specify if needed.
        self.send_button = ttk.Button(action_button_frame, text="Send", command=self._on_send_message, style="primary.TButton") # Example style
        self.send_button.pack(side=tk.LEFT, padx=(0,5))

        self.history_button = ttk.Button(action_button_frame, text="History", command=self._on_show_history)
        self.history_button.pack(side=tk.LEFT)

        # Shows whether the AI assistant is still loading
        self.status_label = ttk.Label(chat_frame, text="", font=("Segoe UI", 9))
        self.status_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self._update_status()

        # Welcome message
        self._add_message("Bot", "Hello! I'm your Homework Helper. How can I assist with your assignments today? (Try typing 'help')", "bot_welcome")

    def _update_status(self):
        """Polls the chatbot's assistant status until it settles."""
        status = getattr(self.chatbot, "assistant_status", "disabled") if self.chatbot else "disabled"
        texts = {
            "waiting to load": "AI assistant: starting up... (simple commands work in the meantime)",
            "loading": "AI assistant: loading model... (the first run downloads it, which takes a few minutes)",
            "ready": "AI assistant: ready. Ask in plain English, e.g. \"move my essay to friday\".",
            "unavailable": "AI assistant: couldn't load, using simple commands instead (type 'help').",
            "disabled": "",
        }
        self.status_label.config(text=texts.get(status, ""))
        if status in ("waiting to load", "loading"):
            self.after(2000, self._update_status)

    def _set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.send_button.config(state=state)
        self.input_field.config(state=state)
        if not busy:
            self.input_field.focus_set()

    def _on_send_message(self, event=None):
        user_input = self.input_field.get()
        if not user_input.strip() or str(self.send_button.cget("state")) == "disabled":
            return

        self._add_message("You", user_input, "user")
        self.input_field.delete(0, tk.END)

        if not self.chatbot:
            self._add_message("Bot", "Chatbot is not available at the moment.", "error")
            return

        # The model can take several seconds, so answer on a worker thread and poll for the result.
        self._set_busy(True)
        self.chat_display.mark_set("thinking_start", "end-1c")
        self.chat_display.mark_gravity("thinking_start", tk.LEFT)
        self._add_message("Bot", "Thinking...", "bot")
        results = queue.Queue()

        def work():
            try:
                results.put(("ok", self.chatbot.get_response(user_input)))
            except Exception as e:
                results.put(("error", e))

        threading.Thread(target=work, daemon=True).start()
        self._poll_response(results)

    def _poll_response(self, results):
        try:
            kind, payload = results.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_response, results)
            return

        # Replace the "Thinking..." placeholder with the real answer
        self.chat_display.config(state='normal')
        self.chat_display.delete("thinking_start", tk.END)
        self.chat_display.config(state='disabled')
        self._set_busy(False)

        if kind == "ok":
            bot_response, data_changed = payload
            self._add_message("Bot", bot_response, "bot")
            if data_changed and hasattr(self.app_instance, 'refresh_all_tabs'):
                self.app_instance.refresh_all_tabs()
        else:
            error_msg = f"An error occurred: {payload}"
            print(f"Chatbot tab error: {error_msg}")
            self._add_message("Bot", error_msg, "error")
            messagebox.showerror("Chatbot Error", "Sorry, I encountered a problem. Please try again.", parent=self.winfo_toplevel())

    def _add_message(self, sender, message, tag_prefix):
        self.chat_display.config(state='normal')
        if self.chat_display.index('end-1c') != "1.0": # Add newline if not the first message
            self.chat_display.insert(tk.END, "\n\n")
        self.chat_display.insert(tk.END, f"{sender}:\n", f"{tag_prefix}_sender")
        # Ensure message is treated as a single block, newlines preserved by ScrolledText
        self.chat_display.insert(tk.END, message, f"{tag_prefix}_content") 
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END) # Scroll to the end

    def _on_show_history(self):
        """Handles the Show History button click by opening the ChatHistoryDialog."""
        # Pass self.app_instance which ChatHistoryDialog expects for theme settings etc.
        ChatHistoryDialog(self.winfo_toplevel(), self.app_instance)  # The dialog manages itself (modal, etc.)
    
    def refresh_data(self):
        """Called when data might have changed elsewhere (e.g., assignments updated)."""
        pass

    def on_theme_changed(self, is_dark_theme=None):
        """Updates chat display tag colors based on the current application theme."""
        if not self.app_instance or not hasattr(self.app_instance, 'root') or \
           not hasattr(self.app_instance.root, 'style') or not hasattr(self.app_instance.root.style, 'colors'):
            print("ChatbotTab: ttkbootstrap style or colors not available for theme update.")
            # Fallback styling if full theme engine isn't ready
            fallback_content_fg = 'white' if is_dark_theme else 'black'
            fallback_chat_bg = '#2B2B2B' if is_dark_theme else 'white'
            self.chat_display.config(background=fallback_chat_bg, foreground=fallback_content_fg) 
            self.chat_display.tag_configure("user_sender", foreground="#60AFFF", font=("Segoe UI Semibold", 11))
            self.chat_display.tag_configure("bot_sender", foreground="#7CB342", font=("Segoe UI Semibold", 11))
            self.chat_display.tag_configure("error_sender", foreground="#EF5350", font=("Segoe UI Semibold", 11, "italic"))
            self.chat_display.tag_configure("bot_welcome_sender", foreground="#7CB342", font=("Segoe UI Semibold", 11))
            self.chat_display.tag_configure("user_content", foreground=fallback_content_fg, font=("Segoe UI", 11))
            self.chat_display.tag_configure("bot_content", foreground=fallback_content_fg, font=("Segoe UI", 11))
            self.chat_display.tag_configure("error_content", foreground=fallback_content_fg, font=("Segoe UI", 11, "italic"))
            self.chat_display.tag_configure("bot_welcome_content", foreground=fallback_content_fg, font=("Segoe UI", 11))
            return

        if is_dark_theme is None: # Should be passed by app.py, but determine if necessary
             is_dark = self.app_instance.is_dark_theme()
        else:
             is_dark = is_dark_theme

        bs_colors = self.app_instance.root.style.colors
        
        # Define sender colors using ttkbootstrap semantic colors with fallbacks
        default_user_sender_fg = "#60AFFF" if is_dark else "#005A9E"
        user_sender_fg = bs_colors.get('info')
        if user_sender_fg is None: user_sender_fg = default_user_sender_fg

        default_bot_sender_fg = "#7CB342" if is_dark else "#2E7D32"
        bot_sender_fg = bs_colors.get('success')
        if bot_sender_fg is None: bot_sender_fg = default_bot_sender_fg
        
        default_error_sender_fg = "#EF5350" if is_dark else "#C62828"
        error_sender_fg = bs_colors.get('danger')
        if error_sender_fg is None: error_sender_fg = default_error_sender_fg
        
        default_content_fg = "white" if is_dark else "black"
        content_fg = bs_colors.get('inputfg')
        if content_fg is None: content_fg = default_content_fg

        default_chat_bg = "#2B2B2B" if is_dark else "white"
        chat_bg = bs_colors.get('inputbg')
        if chat_bg is None: chat_bg = default_chat_bg

        self.chat_display.config(background=chat_bg) # Let content tags handle fg for ScrolledText content
        # Input field (ttk.Entry) should be styled by ttkbootstrap automatically.
        # self.input_field.configure(background=chat_bg, foreground=content_fg) # Not usually needed for ttk.Entry
        
        font_semibold = ("Segoe UI Semibold", 11)
        font_normal = ("Segoe UI", 11)
        font_italic = ("Segoe UI", 11, "italic")

        self.chat_display.tag_configure("user_sender", foreground=user_sender_fg, font=font_semibold)
        self.chat_display.tag_configure("bot_sender", foreground=bot_sender_fg, font=font_semibold)
        self.chat_display.tag_configure("error_sender", foreground=error_sender_fg, font=font_italic)
        self.chat_display.tag_configure("bot_welcome_sender", foreground=bot_sender_fg, font=font_semibold)

        self.chat_display.tag_configure("user_content", foreground=content_fg, font=font_normal)
        self.chat_display.tag_configure("bot_content", foreground=content_fg, font=font_normal)
        self.chat_display.tag_configure("error_content", foreground=content_fg, font=font_italic)
        self.chat_display.tag_configure("bot_welcome_content", foreground=content_fg, font=font_normal)
        
        # print(f"ChatbotTab: Theme updated. Dark mode: {is_dark}. Input FG: {content_fg}, Input BG: {chat_bg}")

        print(f"ChatbotTab: Theme updated. Dark mode: {is_dark}")
        # Refresh chat display if it's already populated to re-apply tags might be complex.
        # New messages will use the new tag colors.
        # A full re-render of chat history on theme change would be needed for immediate effect on old messages.