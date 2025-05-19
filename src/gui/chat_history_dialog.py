import tkinter as tk
from tkinter import ttk, scrolledtext
import json
import os
from collections import defaultdict
from datetime import datetime

PERSISTENT_CHAT_LOG_FILE = "data/persistent_chat_log.json"

class ChatHistoryDialog(tk.Toplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent)
        self.app_instance = app_instance
        self.title("Chat History")
        self.geometry("700x500")
        self.minsize(500, 300)
        self.transient(parent)
        self.grab_set()
        self.sessions_data = self._load_and_group_sessions()
        self._setup_ui()
        self._populate_sessions_list()
        # Initial theme apply. Must be called after UI is set up.
        if hasattr(self.app_instance, 'is_dark_theme'):
             self.on_theme_changed(self.app_instance.is_dark_theme())
        else: # Fallback if app_instance isn't fully ready
            self.on_theme_changed(False)

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _load_and_group_sessions(self):
        sessions = defaultdict(list)
        if os.path.exists(PERSISTENT_CHAT_LOG_FILE):
            try:
                with open(PERSISTENT_CHAT_LOG_FILE, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                    if isinstance(log_data, list):
                        for entry in log_data:
                            sessions[entry.get("session_id", "Unknown Session")].append(entry)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading chat history: {e}")
                # Display error inside the dialog if it's already created
        return sessions

    def _setup_ui(self):
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        sessions_frame = ttk.Frame(main_pane, width=200)
        main_pane.add(sessions_frame, weight=1)
        ttk.Label(sessions_frame, text="Chat Sessions:", font=("Segoe UI", 10, "bold")).pack(pady=(0,5), anchor="w")
        self.sessions_listbox = tk.Listbox(sessions_frame, exportselection=False, font=("Segoe UI", 10), relief=tk.SUNKEN, borderwidth=1)
        self.sessions_listbox.pack(fill=tk.BOTH, expand=True)
        self.sessions_listbox.bind("<<ListboxSelect>>", self._on_session_selected)

        messages_frame = ttk.Frame(main_pane)
        main_pane.add(messages_frame, weight=3)
        ttk.Label(messages_frame, text="Messages:", font=("Segoe UI", 10, "bold")).pack(pady=(0,5), anchor="w")
        self.messages_display = scrolledtext.ScrolledText(messages_frame, wrap=tk.WORD, state='disabled', font=("Segoe UI", 10), relief=tk.SUNKEN, borderwidth=1)
        self.messages_display.pack(fill=tk.BOTH, expand=True)
        
        close_button = ttk.Button(self, text="Close", command=self.destroy, style="primary.TButton") # Example ttkbootstrap style
        close_button.pack(pady=(5,10))
        
    def _populate_sessions_list(self):
        self.sessions_listbox.delete(0, tk.END)
        sorted_session_ids = sorted(self.sessions_data.keys(), reverse=True)
        for session_id in sorted_session_ids:
            try: dt_obj = datetime.fromisoformat(session_id); display_name = f"Session: {dt_obj.strftime('%Y-%m-%d %H:%M:%S')}"
            except ValueError: display_name = session_id
            self.sessions_listbox.insert(tk.END, display_name)
        if sorted_session_ids: self.sessions_listbox.select_set(0); self._on_session_selected()

    def _on_session_selected(self, event=None):
        selected_indices = self.sessions_listbox.curselection()
        if not selected_indices: return
        selected_index = selected_indices[0]
        sorted_session_ids = sorted(self.sessions_data.keys(), reverse=True)
        if selected_index < len(sorted_session_ids):
            session_id_key = sorted_session_ids[selected_index]
            messages = self.sessions_data.get(session_id_key, [])
            self.messages_display.config(state='normal'); self.messages_display.delete('1.0', tk.END)
            for entry in messages:
                user, bot, time_str = entry.get("user_input",""), entry.get("bot_response",""), entry.get("timestamp","")
                try: time_disp = datetime.fromisoformat(time_str).strftime('%H:%M:%S')
                except ValueError: time_disp = "N/A"
                if self.messages_display.index('end-1c')!="1.0": self.messages_display.insert(tk.END, "\n")
                self.messages_display.insert(tk.END, f"[{time_disp}] You: ", "user_sender_hist")
                self.messages_display.insert(tk.END, f"{user}\n", "user_content_hist")
                self.messages_display.insert(tk.END, f"[{time_disp}] Bot: ", "bot_sender_hist")
                self.messages_display.insert(tk.END, f"{bot}\n", "bot_content_hist")
            self.messages_display.config(state='disabled'); self.messages_display.see('1.0')

    def on_theme_changed(self, is_dark_theme=None): # Parameter name consistent with app.py
        if not self.app_instance or not hasattr(self.app_instance, 'root') or \
           not hasattr(self.app_instance.root, 'style') or not hasattr(self.app_instance.root.style, 'colors'):
            print("ChatHistoryDialog: ttkbootstrap style or colors not available.")
            # Minimal fallback if full theme engine isn't ready
            fb_list_bg = '#2B2B2B' if is_dark_theme else 'white'
            fb_list_fg = 'white' if is_dark_theme else 'black'
            fb_select_bg = '#005A9E'
            fb_select_fg = 'white'
            self.sessions_listbox.config(bg=fb_list_bg, fg=fb_list_fg, selectbackground=fb_select_bg, selectforeground=fb_select_fg)
            self.messages_display.config(background=fb_list_bg, foreground=fb_list_fg)
            self.messages_display.tag_configure("user_sender_hist", foreground=fb_select_bg)
            self.messages_display.tag_configure("bot_sender_hist", foreground='#7CB342')
            self.messages_display.tag_configure("user_content_hist", foreground=fb_list_fg)
            self.messages_display.tag_configure("bot_content_hist", foreground=fb_list_fg)
            return

        if is_dark_theme is None: # Should be passed, but determine if necessary
             is_dark = self.app_instance.is_dark_theme()
        else:
             is_dark = is_dark_theme
        
        bs_colors = self.app_instance.root.style.colors

        default_list_bg = '#2B2B2B' if is_dark else 'white'
        list_bg = bs_colors.get('inputbg')
        if list_bg is None: list_bg = default_list_bg

        default_list_fg = 'white' if is_dark else 'black'
        list_fg = bs_colors.get('inputfg')
        if list_fg is None: list_fg = default_list_fg

        default_select_bg = '#005A9E'
        select_bg = bs_colors.get('primary')
        if select_bg is None: select_bg = default_select_bg
        
        # Simple contrast for selected text on primary background
        try: r,g,b = self.app_instance.root.winfo_rgb(select_bg); brightness = (r*299+g*587+b*114)/1000/255
        except: brightness = 0.4 # Assume dark if can't parse
        select_fg = 'white' if brightness < 0.6 else 'black'

        self.sessions_listbox.config(bg=list_bg, fg=list_fg, selectbackground=select_bg, selectforeground=select_fg)
        self.messages_display.config(background=list_bg) # Text widget bg

        default_user_sender_fg_hist = '#60AFFF' if is_dark else '#005A9E'
        user_sender_fg_hist = bs_colors.get('info')
        if user_sender_fg_hist is None: user_sender_fg_hist = default_user_sender_fg_hist

        default_bot_sender_fg_hist = '#7CB342' if is_dark else '#2E7D32'
        bot_sender_fg_hist = bs_colors.get('success')
        if bot_sender_fg_hist is None: bot_sender_fg_hist = default_bot_sender_fg_hist

        content_fg_hist = list_fg # Same as listbox text

        font_semibold = ("Segoe UI Semibold", 10)
        font_normal = ("Segoe UI", 10)

        self.messages_display.tag_configure("user_sender_hist", foreground=user_sender_fg_hist, font=font_semibold)
        self.messages_display.tag_configure("user_content_hist", foreground=content_fg_hist, font=font_normal)
        self.messages_display.tag_configure("bot_sender_hist", foreground=bot_sender_fg_hist, font=font_semibold)
        self.messages_display.tag_configure("bot_content_hist", foreground=content_fg_hist, font=font_normal)
        
        self._on_session_selected() # Refresh display with new tag colors