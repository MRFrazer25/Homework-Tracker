import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap.widgets import DateEntry
from datetime import datetime, date # Ensure date is imported
from src.utils.helpers import format_date, ALLOWED_PRIORITIES, ALLOWED_DIFFICULTY, DATE_FORMATS # Import our defined DATE_FORMATS

class AddAssignmentDialog(tk.Toplevel):
    """Dialog for adding or editing an assignment."""
    def __init__(self, parent, app_callbacks, theme_settings_provider, assignment_to_edit=None):
        """
        Initializes the Add/Edit Assignment dialog.
        
        Args:
            parent: The parent widget.
            app_callbacks: Dictionary of callbacks to the main application.
            theme_settings_provider: Callable that returns current theme settings.
            assignment_to_edit (dict, optional): Assignment data to pre-fill for editing.
        """
        super().__init__(parent)
        self.transient(parent) # Ensure dialog stays on top of its parent.
        self.grab_set() # Make the dialog modal.
        
        self.app_callbacks = app_callbacks
        self.theme_settings_provider = theme_settings_provider 
        self.assignment_to_edit = assignment_to_edit
        self.result = None # Stores the assignment data if saved.

        self.title("Add New Assignment" if not assignment_to_edit else "Edit Assignment")
        
        # Variables for form fields
        self.name_var = tk.StringVar()
        self.class_var = tk.StringVar()
        self.priority_var = tk.StringVar(value=ALLOWED_PRIORITIES[1] if ALLOWED_PRIORITIES else "Medium") # Default to Medium
        self.difficulty_var = tk.IntVar(value=5 if ALLOWED_DIFFICULTY else 5) # Default
        self.completed_var = tk.BooleanVar(value=False)
        # Due date will be handled by DateEntry directly
        # Details will be handled by Text widget directly

        due_date_initial = datetime.now().date() # Default to today's date object

        if assignment_to_edit:
            self.name_var.set(assignment_to_edit.get("name", ""))
            self.class_var.set(assignment_to_edit.get("class", ""))
            self.priority_var.set(assignment_to_edit.get("priority", ALLOWED_PRIORITIES[1] if ALLOWED_PRIORITIES else "Medium"))
            self.difficulty_var.set(assignment_to_edit.get("difficulty", 5 if ALLOWED_DIFFICULTY else 5))
            self.completed_var.set(assignment_to_edit.get("completed", False))
            
            due_date_val = assignment_to_edit.get("due_date")
            if isinstance(due_date_val, str):
                try:
                    due_date_initial = datetime.strptime(due_date_val, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    try:
                        due_date_initial = datetime.strptime(due_date_val, '%Y-%m-%d').date()
                    except ValueError:
                        pass # Keep default if parsing fails
            elif isinstance(due_date_val, datetime):
                due_date_initial = due_date_val.date()
            elif isinstance(due_date_val, date):
                due_date_initial = due_date_val
        
        self.due_date_initial_val = due_date_initial # Store for DateEntry

        self._setup_form_ui()
        
        self.protocol("WM_DELETE_WINDOW", self._on_cancel) # Handle window close button.
        
        # Center window relative to parent.
        self.update_idletasks() # Ensure dimensions are calculated.
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        self.geometry(f"+{x}+{y}")
        
        self.wait_window(self) # Block execution until dialog is closed.

    def _setup_form_ui(self):
        """Creates and lays out the form widgets for the dialog."""
        form_frame = ttk.Frame(self, padding="15")
        form_frame.pack(expand=True, fill="both")

        current_theme_settings = self.theme_settings_provider()
        entry_bg = current_theme_settings.get("entry_bg", "white")
        entry_fg = current_theme_settings.get("entry_fg", "black")

        # Field: Name
        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=3, padx=5)
        self.name_entry = ttk.Entry(form_frame, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=3, padx=5)
        self.name_entry.focus_set() # Focus on name field initially

        # Field: Class
        ttk.Label(form_frame, text="Class:").grid(row=1, column=0, sticky="w", pady=3, padx=5)
        self.class_entry = ttk.Entry(form_frame, textvariable=self.class_var, width=40)
        self.class_entry.grid(row=1, column=1, sticky="ew", pady=3, padx=5)

        # Field: Due Date (ttkbootstrap.DateEntry)
        ttk.Label(form_frame, text="Due Date:").grid(row=2, column=0, sticky="w", pady=3, padx=5)
        self.due_date_entry = DateEntry(
            form_frame,
            startdate=self.due_date_initial_val,
            dateformat=DATE_FORMATS[self.app_callbacks['get_date_format_template_name']()] # Use new direct callback
        )
        self.due_date_entry.grid(row=2, column=1, sticky="w", pady=3, padx=5)
        
        # Field: Priority
        ttk.Label(form_frame, text="Priority:").grid(row=3, column=0, sticky="w", pady=3, padx=5)
        self.priority_combo = ttk.Combobox(form_frame, textvariable=self.priority_var, values=ALLOWED_PRIORITIES, state="readonly", width=15)
        self.priority_combo.grid(row=3, column=1, sticky="w", pady=3, padx=5)
        
        # Field: Difficulty
        ttk.Label(form_frame, text="Difficulty:").grid(row=4, column=0, sticky="w", pady=3, padx=5)
        self.difficulty_spinbox = ttk.Spinbox(
            form_frame, 
            from_=min(ALLOWED_DIFFICULTY) if ALLOWED_DIFFICULTY else 1, 
            to=max(ALLOWED_DIFFICULTY) if ALLOWED_DIFFICULTY else 10, 
            textvariable=self.difficulty_var, 
            width=5,
            state='readonly',
            wrap=True
        )
        self.difficulty_spinbox.grid(row=4, column=1, sticky="w", pady=3, padx=5)

        # Field: Completed
        self.completed_check = ttk.Checkbutton(form_frame, text="Completed", variable=self.completed_var)
        self.completed_check.grid(row=5, column=1, sticky="w", pady=5)

        # Buttons Frame
        button_frame = ttk.Frame(form_frame) 
        button_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky="e")
        
        save_button = ttk.Button(button_frame, text="Save", command=self._on_save, style="success.TButton")
        save_button.pack(side="left", padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel, style="danger.TButton")
        cancel_button.pack(side="left", padx=5)

        form_frame.columnconfigure(1, weight=1) # Allow entry fields and text area to expand.

    def _on_save(self):
        """Handles the save action, validates input, and sets the dialog result."""
        name = self.name_var.get().strip()
        assignment_class_name = self.class_var.get().strip()
        priority = self.priority_var.get()
        difficulty_str = self.difficulty_var.get()

        if not name:
            messagebox.showerror("Validation Error", "Assignment name cannot be empty.", parent=self)
            self.name_entry.focus_set()
            return
        if not assignment_class_name:
            messagebox.showerror("Validation Error", "Class name cannot be empty.", parent=self)
            self.class_entry.focus_set()
            return
        
        try:
            difficulty = int(difficulty_str) # Spinbox already ensures it's an int within range
        except ValueError: # Should not happen with spinbox, but good to have
            messagebox.showerror("Validation Error", "Invalid difficulty.", parent=self)
            self.difficulty_spinbox.focus_set()
            return

        try:
            # ttkbootstrap.DateEntry.entry.get() returns string, .startdate is a datetime object
            due_date_str = self.due_date_entry.entry.get()
            # Use the date_format from settings_manager to parse
            date_format_template = self.app_callbacks['get_date_format_template_name']() # Use new direct callback
            actual_date_format = DATE_FORMATS.get(date_format_template, '%Y-%m-%d') # Fallback to ISO
            
            due_date_obj = datetime.strptime(due_date_str, actual_date_format).date()
        except Exception as e: 
            messagebox.showerror("Validation Error", f"Invalid due date: {due_date_str}. Please use {actual_date_format} format. Error: {e}", parent=self)
            self.due_date_entry.focus_set()
            return

        self.result = {
            "name": name,
            "class": assignment_class_name,
            "due_date": datetime.combine(due_date_obj, datetime.min.time()), # Store as datetime object
            "priority": priority,
            "difficulty": difficulty,
            "completed": self.completed_var.get()
        }
        
        if self.assignment_to_edit: # If editing, retain original ID
            if "id" in self.assignment_to_edit:
                self.result["id"] = self.assignment_to_edit["id"]

        self.destroy()

    def _on_cancel(self):
        """Handles the cancel action, sets result to None, and closes the dialog."""
        self.result = None
        self.destroy()


class AssignmentsTab(ttk.Frame):
    """Tab for displaying and managing assignments."""
    def __init__(self, parent, assignments_data_provider, app_callbacks):
        """
        Initializes the Assignments tab.
        
        Args:
            parent: The parent widget (notebook).
            assignments_data_provider: Callable to get the list of assignments.
            app_callbacks: Dictionary of callbacks to the main application.
        """
        super().__init__(parent)
        self.assignments_provider = assignments_data_provider 
        self.app_callbacks = app_callbacks 
        
        self.assignments_tree = None
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.update_assignments_list())

        self.setup_ui()
        self.update_assignments_list() # Load initial data into the treeview.

    def setup_ui(self):
        """Creates and lays out the UI elements for the Assignments tab."""
        # Apply style for Treeview item font
        s = ttk.Style()
        s.configure("Assignments.Treeview", rowheight=25) # Optional: increase row height
        s.configure("Assignments.Treeview", font=("Segoe UI", 10)) # Item font, default is usually smaller
        s.configure("Assignments.Treeview.Heading", font=("Segoe UI", 10, "bold")) # Heading font

        # Main frame for this tab
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, weight=1) # Make the treeview column expandable
        main_frame.rowconfigure(1, weight=1)    # Make the treeview row expandable

        # Search and Filter Frame
        filter_frame = ttk.Frame(main_frame)
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side="left", padx=(0,5))
        ttk.Button(filter_frame, text="Search", command=self.update_assignments_list).pack(side="left", padx=(0,10))
        ttk.Button(filter_frame, text="Clear Search", command=self.clear_search).pack(side="left")

        # Assignments Treeview
        self.assignments_tree = ttk.Treeview(
            main_frame, 
            columns=("ID", "Name", "Class", "Due Date", "Priority", "Difficulty", "Status"), 
            displaycolumns=("Name", "Class", "Due Date", "Priority", "Difficulty", "Status"), 
            show="headings",
            style="Assignments.Treeview"
        )
        self.assignments_tree.heading("Name", text="Assignment Name")
        self.assignments_tree.heading("Class", text="Class")
        self.assignments_tree.heading("Due Date", text="Due Date")
        self.assignments_tree.heading("Priority", text="Priority")
        self.assignments_tree.heading("Difficulty", text="Difficulty")
        self.assignments_tree.heading("Status", text="Status")
        self.assignments_tree.grid(row=1, column=0, sticky="nsew")
        
        # Configure column widths (adjust as needed)
        self.assignments_tree.column("ID", width=0, stretch=tk.NO) # Hidden ID column
        self.assignments_tree.column("Name", width=250, anchor='w')
        self.assignments_tree.column("Class", width=120, anchor='w')
        self.assignments_tree.column("Due Date", width=100, anchor='center')
        self.assignments_tree.column("Priority", width=80, anchor='center')
        self.assignments_tree.column("Difficulty", width=80, anchor='center')
        self.assignments_tree.column("Status", width=70, anchor='center')

        # Scrollbars
        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.assignments_tree.yview)
        hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=self.assignments_tree.xview)
        self.assignments_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.grid(row=1, column=1, sticky='ns')
        hsb.grid(row=2, column=0, sticky='ew')
        
        # Button Frame for actions
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky="ew", pady=(10,0))

        add_button = ttk.Button(button_frame, text="Add New", command=self.open_add_assignment_dialog)
        add_button.pack(side="left", padx=5)

        # Edit Button
        self.edit_button = ttk.Button(button_frame, text="Edit Selected", command=self._edit_selected_assignment, state="disabled")
        self.edit_button.pack(side="left", padx=5)

        self.delete_button = ttk.Button(button_frame, text="Delete Selected", command=self._delete_selected_assignment, state="disabled")
        self.delete_button.pack(side="left", padx=5)

        self.mark_complete_button = ttk.Button(button_frame, text="Mark Complete", command=lambda: self._toggle_selected_completion(True), state="disabled")
        self.mark_complete_button.pack(side="left", padx=5)

        self.mark_incomplete_button = ttk.Button(button_frame, text="Mark Incomplete", command=lambda: self._toggle_selected_completion(False), state="disabled")
        self.mark_incomplete_button.pack(side="left", padx=5)
        
        # Initial population and event bindings
        self.update_assignments_list()
        self.assignments_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.assignments_tree.bind("<Double-1>", self.on_assignment_double_click)

    def get_assignments(self):
        """Fetches assignments from the data provider."""
        if callable(self.assignments_provider):
            return self.assignments_provider()
        return self.assignments_provider # Assuming it's a direct list/iterable if not callable

    def update_assignments_list(self):
        """Clears and repopulates the assignments treeview based on current data and search term."""
        if not self.assignments_tree:
            return

        for item in self.assignments_tree.get_children(): # Clear existing items
            self.assignments_tree.delete(item)
        
        search_term = self.search_var.get().lower()
        assignments = self.get_assignments()

        for assignment in assignments:
            # Ensure 'id' exists for robust item identification in the tree.
            # If 'id' can be missing, a fallback or error handling is needed.
            assignment_id = assignment.get('id')
            if assignment_id is None:
                print(f"Warning: Assignment '{assignment.get('name')}' missing ID, skipping.")
                continue # Or use a temporary unique ID if absolutely necessary

            # Filter by search term (name or class)
            if (search_term in assignment.get('name', '').lower() or
                search_term in assignment.get('class', '').lower()):
                
                completed_status = "Complete" if assignment.get('completed', False) else "Incomplete"
                difficulty_display = f"{assignment.get('difficulty', '-')}/10"
                
                self.assignments_tree.insert(
                    '', 'end',
                    iid=assignment_id, # Use actual assignment ID as item identifier
                    values=(
                        assignment_id, # Value for the hidden 'id' column
                        assignment.get('name', 'N/A'),
                        assignment.get('class', 'N/A'),
                        format_date(assignment.get('due_date')), 
                        assignment.get('priority', 'N/A'),
                        difficulty_display,
                        completed_status
                    ),
                    tags=('completed' if assignment.get('completed', False) else 'pending')
                )
        
        # Apply styling tags for visual differentiation
        self.assignments_tree.tag_configure('completed', foreground='gray') # Example style
        self.assignments_tree.tag_configure('pending', foreground=None) # Use default foreground

    def open_add_assignment_dialog(self):
        """Opens the dialog to add a new assignment."""
        # Get the theme provider callback from the main app instance.
        # self.master is the notebook, self.master.master is HomeworkTrackerApp.
        theme_provider_callback = getattr(self.master.master, 'get_current_theme_settings', lambda: {})
        
        dialog = AddAssignmentDialog(self, self.app_callbacks, theme_provider_callback)
        if dialog.result: # User clicked "Save" and data is valid
            new_assignment_data = dialog.result
            add_assignment_callback = self.app_callbacks.get('add_assignment')
            if add_assignment_callback:
                add_assignment_callback(new_assignment_data) 
                # App's callback (handle_add_assignment_request) is now responsible for messages and refresh.
                # self.update_assignments_list() # This is handled by app's refresh_all_tabs
            else:
                messagebox.showerror("Configuration Error", "Add assignment callback not configured.", parent=self.winfo_toplevel())

    def on_assignment_double_click(self, event):
        """Handles double-clicking an assignment to edit it."""
        self._edit_selected_assignment()

    def _get_selected_assignment_object(self):
        """Helper to get the full assignment object for the currently focused treeview item."""
        selected_item_iid = self.assignments_tree.focus()
        if not selected_item_iid:
            # Parent this info message to the top-level window for consistency
            messagebox.showinfo("Action", "Please select an assignment first.", parent=self.winfo_toplevel())
            return None
        
        for assignment in self.get_assignments():
            if str(assignment.get('id')) == str(selected_item_iid):
                return assignment
        
        messagebox.showwarning("Error", f"Could not find details for selected assignment (ID: {selected_item_iid}).", parent=self.winfo_toplevel())
        return None

    def _delete_selected_assignment(self):
        """Handles deleting the selected assignment."""
        selected_assignment = self._get_selected_assignment_object()
        if not selected_assignment:
            return

        delete_callback = self.app_callbacks.get('delete_assignment')
        if delete_callback:
            # The app.py handler will show confirmation and messages.
            # It expects the assignment object.
            delete_callback(selected_assignment) 
        else:
            messagebox.showerror("Configuration Error", "Delete assignment callback not configured.", parent=self.winfo_toplevel())

    def _toggle_selected_completion(self, mark_completed):
        """Handles toggling the completion status of the selected assignment."""
        selected_assignment = self._get_selected_assignment_object()
        if not selected_assignment:
            return
            
        set_status_callback = self.app_callbacks.get('set_completion_status')
        if set_status_callback:
            # Pass the assignment object and the desired completion status
            set_status_callback(selected_assignment, mark_completed)
        else:
            messagebox.showerror("Configuration Error", "Set completion status callback not configured.", parent=self.winfo_toplevel())

    def on_tree_select(self, event=None):
        """Updates button states based on Treeview selection and assignment status."""
        selected_item_iid = self.assignments_tree.focus()
        has_selection = bool(selected_item_iid)
        
        self.delete_button.config(state="normal" if has_selection else "disabled")
        self.edit_button.config(state="normal" if has_selection else "disabled")

        if has_selection:
            assignment_obj = self._get_selected_assignment_object() # Fetch the full object
            if assignment_obj:
                is_completed = assignment_obj.get('completed', False)
                self.mark_complete_button.config(state="disabled" if is_completed else "normal")
                self.mark_incomplete_button.config(state="normal" if is_completed else "disabled")
            else:
                self.mark_complete_button.config(state="disabled")
                self.mark_incomplete_button.config(state="disabled")
        else:
            self.mark_complete_button.config(state="disabled")
            self.mark_incomplete_button.config(state="disabled")

    def _edit_selected_assignment(self):
        """Opens the Add/Edit dialog for the currently selected assignment."""
        selected_assignment_obj = self._get_selected_assignment_object()
        if not selected_assignment_obj:
            messagebox.showinfo("Edit Assignment", "Please select an assignment to edit.", parent=self)
            return

        # Get the theme provider callback from the main app instance.
        theme_provider_callback = getattr(self.master.master, 'get_current_theme_settings', lambda: {})

        # The AddAssignmentDialog is reused for editing
        dialog = AddAssignmentDialog(self, self.app_callbacks, theme_provider_callback, assignment_to_edit=selected_assignment_obj)
        
        if dialog.result: # User clicked Save
            # The dialog result should already include the original ID if editing
            # Ensure the ID is part of the result for the update operation
            if 'id' not in dialog.result and 'id' in selected_assignment_obj:
                 dialog.result['id'] = selected_assignment_obj['id']
            
            if 'id' not in dialog.result:
                messagebox.showerror("Edit Error", "Failed to edit assignment: ID was missing.", parent=self)
                return

            if self.app_callbacks and 'edit_assignment' in self.app_callbacks:
                self.app_callbacks['edit_assignment'](dialog.result)
            else:
                messagebox.showerror("Error", "Edit callback not configured.", parent=self)
        # If dialog.result is None, user cancelled, so do nothing

    def clear_search(self):
        """Clears the search term and updates the assignments list."""
        self.search_var.set("")
        
        self.update_idletasks() # Refresh to get correct width/height for search entry

    def on_theme_changed(self, is_dark_theme):
        """Handles theme changes for the Assignments tab."""
        # Update Treeview tag colors
        # Get theme-appropriate colors
        master_app = self.app_callbacks.get('get_master_app')()
        if master_app and hasattr(master_app, 'style') and hasattr(master_app.style, 'colors'):
            completed_fg = master_app.style.colors.secondary # A muted color
            pending_fg = master_app.style.colors.fg
        else: # Fallback
            completed_fg = "#808080" if is_dark_theme else "gray"
            pending_fg = "#FFFFFF" if is_dark_theme else "#000000"

        self.assignments_tree.tag_configure('completed', foreground=completed_fg)
        self.assignments_tree.tag_configure('pending', foreground=pending_fg)
        
        # If other elements needed specific theme updates, they would go here.
        # For example, re-applying styles to buttons if they didn't update automatically.
        self.update_assignments_list() # Refresh list to apply new tag colors if items are already there