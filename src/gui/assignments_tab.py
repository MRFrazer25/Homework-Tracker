import tkinter as tk
from tkinter import ttk, messagebox, Text 
from tkcalendar import DateEntry # For the add/edit assignment form
from datetime import datetime # For parsing dates
from src.utils.helpers import format_date # Assuming helpers.py is in src/utils/

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
        self.priority_var = tk.StringVar(value="Medium") # Default
        self.difficulty_var = tk.IntVar(value=5) # Default
        self.completed_var = tk.BooleanVar(value=False)
        # Due date will be handled by DateEntry directly
        # Details will be handled by Text widget directly

        if assignment_to_edit:
            self.name_var.set(assignment_to_edit.get("name", ""))
            self.class_var.set(assignment_to_edit.get("class", ""))
            self.priority_var.set(assignment_to_edit.get("priority", "Medium"))
            self.difficulty_var.set(assignment_to_edit.get("difficulty", 5))
            self.completed_var.set(assignment_to_edit.get("completed", False))
            # Due date and details need to be set on the widgets after creation

        self._setup_form_ui()
        
        self.protocol("WM_DELETE_WINDOW", self._on_cancel) # Handle window close button.
        
        # Optional: Center window relative to parent.
        # self.update_idletasks() # Ensure dimensions are calculated.
        # parent_x = parent.winfo_rootx()
        # parent_y = parent.winfo_rooty()
        # parent_width = parent.winfo_width()
        # parent_height = parent.winfo_height()
        # dialog_width = self.winfo_width()
        # dialog_height = self.winfo_height()
        # x = parent_x + (parent_width - dialog_width) // 2
        # y = parent_y + (parent_height - dialog_height) // 2
        # self.geometry(f"+{x}+{y}")
        
        self.wait_window(self) # Block execution until dialog is closed.

    def _setup_form_ui(self):
        """Creates and lays out the form widgets for the dialog."""
        form_frame = ttk.Frame(self, padding="10")
        form_frame.pack(expand=True, fill="both")

        # Field: Name
        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.name_entry = ttk.Entry(form_frame, textvariable=self.name_var, width=50)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=2)

        # Field: Class
        ttk.Label(form_frame, text="Class:").grid(row=1, column=0, sticky="w", pady=2)
        self.class_entry = ttk.Entry(form_frame, textvariable=self.class_var, width=50)
        self.class_entry.grid(row=1, column=1, sticky="ew", pady=2)

        # Field: Due Date
        ttk.Label(form_frame, text="Due Date:").grid(row=2, column=0, sticky="w", pady=2)
        initial_due_date_obj = self.assignment_to_edit.get("due_date", datetime.today()) if self.assignment_to_edit else datetime.today()
        # Ensure initial_due_date_obj is a datetime object for DateEntry
        if isinstance(initial_due_date_obj, str): 
            try: # Attempt to parse from YYYY-MM-DD HH:MM:SS
                initial_due_date_obj = datetime.strptime(initial_due_date_obj, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                 try: # Attempt to parse from YYYY-MM-DD
                    initial_due_date_obj = datetime.strptime(initial_due_date_obj, '%Y-%m-%d')
                 except ValueError: # Fallback to today if parsing fails
                    initial_due_date_obj = datetime.today()
        elif not isinstance(initial_due_date_obj, datetime): # If not datetime or str, fallback
            initial_due_date_obj = datetime.today()


        current_theme_settings = self.theme_settings_provider()
        
        date_entry_args = {
            "master": form_frame, # Explicitly set master for DateEntry
            "width": 12, "date_pattern": 'yyyy-mm-dd',
            "year": initial_due_date_obj.year, "month": initial_due_date_obj.month, "day": initial_due_date_obj.day
        }
        
        # Apply DateEntry specific styles from theme settings
        # These are direct keyword arguments for tkcalendar.DateEntry constructor
        if "date_entry_style" in current_theme_settings:
            # Only pass valid DateEntry constructor arguments
            # Common arguments for styling DateEntry's calendar dropdown
            valid_calendar_kwargs = [
                "background", "foreground", "disabledbackground", "disabledforeground",
                "bordercolor", "headersbackground", "headersforeground", 
                "selectbackground", "selectforeground", 
                "normalbackground", "normalforeground", 
                "othermonthbackground", "othermonthforeground",
                "weekendbackground", "weekendforeground",
                "font", "firstweekday", "mindate", "maxdate", "showweeknumbers",
                "locale" 
                # Note: 'style' kwarg is for its own named themes, not individual colors.
                # The entry part of DateEntry is a ttk.Entry, styled by TEntry ttk style.
            ]
            for key, value in current_theme_settings["date_entry_style"].items():
                 if key in valid_calendar_kwargs: 
                    date_entry_args[key] = value
        
        self.due_date_entry = DateEntry(**date_entry_args)
        self.due_date_entry.grid(row=2, column=1, sticky="w", pady=2)
        
        # Field: Priority
        ttk.Label(form_frame, text="Priority:").grid(row=3, column=0, sticky="w", pady=2)
        self.priority_combo = ttk.Combobox(form_frame, textvariable=self.priority_var, values=["Low", "Medium", "High"], state="readonly")
        self.priority_combo.grid(row=3, column=1, sticky="w", pady=2)
        
        # Field: Difficulty
        ttk.Label(form_frame, text="Difficulty (1-10):").grid(row=4, column=0, sticky="w", pady=2)
        self.difficulty_spinbox = ttk.Spinbox(
            form_frame, 
            from_=1, 
            to=10, 
            textvariable=self.difficulty_var, 
            width=5, # Adjust width as needed
            state='readonly' # Or 'normal' if direct typing is preferred over just arrows
        )
        self.difficulty_spinbox.grid(row=4, column=1, sticky="w", pady=2) # Use sticky="w" to align left

        # Field: Details/Notes (tk.Text widget, needs direct styling)
        ttk.Label(form_frame, text="Details/Notes:").grid(row=5, column=0, sticky="nw", pady=2)
        self.details_text = Text(
            form_frame, width=50, height=5, wrap="word", relief="sunken", borderwidth=1,
            background=current_theme_settings.get("entry_bg", "white"), 
            foreground=current_theme_settings.get("entry_fg", "black"), 
            insertbackground=current_theme_settings.get("entry_fg", "black") # Cursor color
        )
        self.details_text.grid(row=5, column=1, sticky="ew", pady=2)
        if self.assignment_to_edit and self.assignment_to_edit.get("details"):
            self.details_text.insert("1.0", self.assignment_to_edit.get("details"))

        # Field: Completed
        self.completed_check = ttk.Checkbutton(form_frame, text="Completed", variable=self.completed_var)
        self.completed_check.grid(row=6, column=1, sticky="w", pady=5)

        # Buttons Frame
        button_frame = ttk.Frame(form_frame) 
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        
        save_button = ttk.Button(button_frame, text="Save", command=self._on_save)
        save_button.pack(side="left", padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        cancel_button.pack(side="left", padx=5)

        form_frame.columnconfigure(1, weight=1) # Allow entry fields and text area to expand.

    def _on_save(self):
        """Handles the save action, validates input, and sets the dialog result."""
        name = self.name_var.get().strip()
        klass = self.class_var.get().strip()
        priority = self.priority_var.get()
        difficulty = self.difficulty_var.get() 
        completed = self.completed_var.get()
        details = self.details_text.get("1.0", "end-1c").strip()

        if not name:
            messagebox.showerror("Validation Error", "Assignment name cannot be empty.", parent=self)
            return
        
        try:
            due_date_obj = self.due_date_entry.get_date() # Returns a datetime.date object
        except Exception as e: 
            messagebox.showerror("Validation Error", f"Invalid due date: {e}", parent=self)
            return

        self.result = {
            "name": name,
            "class": klass,
            "due_date": datetime.combine(due_date_obj, datetime.min.time()), # Store as full datetime
            "priority": priority,
            "difficulty": difficulty,
            "details": details,
            "completed": completed
        }
        
        if self.assignment_to_edit and "id" in self.assignment_to_edit:
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
        self.assignments_tree.grid(row=1, column=0, sticky="nsew") # Reverted row to 1
        
        # Configure column widths (adjust as needed)
        self.assignments_tree.column("ID", width=0, stretch=tk.NO) # Hidden ID column
        self.assignments_tree.column("Name", width=250, anchor='w')
        self.assignments_tree.column("Class", width=120, anchor='w')
        self.assignments_tree.column("Due Date", width=100, anchor='center')
        self.assignments_tree.column("Priority", width=80, anchor='center')
        self.assignments_tree.column("Difficulty", width=80, anchor='center')
        self.assignments_tree.column("Status", width=70, anchor='center')

        # Scrollbars - DEFINED HERE
        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.assignments_tree.yview)
        hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=self.assignments_tree.xview)
        self.assignments_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.grid(row=1, column=1, sticky='ns') # Reverted row to 1
        hsb.grid(row=2, column=0, sticky='ew') # Reverted row to 2, removed pady
        
        # Button Frame for actions
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky="ew", pady=(10,0)) # Reverted row to 3, restored original pady

        add_button = ttk.Button(button_frame, text="Add New", command=self.open_add_assignment_dialog)
        add_button.pack(side="left", padx=5)

        # Edit Button - ADDED HERE
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
        self._edit_selected_assignment() # MODIFIED to call _edit_selected_assignment

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
            # self.update_assignments_list() # app.py's refresh_all_tabs will handle this
        else:
            messagebox.showerror("Configuration Error", "Delete assignment callback not configured.", parent=self.winfo_toplevel())

    def _toggle_selected_completion(self, mark_completed):
        """Handles toggling the completion status of the selected assignment."""
        selected_assignment = self._get_selected_assignment_object()
        if not selected_assignment:
            return
            
        toggle_callback = self.app_callbacks.get('toggle_completion')
        if toggle_callback:
            # The app.py handler will manage the toggle and refresh.
            # It expects the assignment object.
            toggle_callback(selected_assignment)
            # self.update_assignments_list() # app.py's refresh_all_tabs will handle this
        else:
            messagebox.showerror("Configuration Error", "Toggle completion callback not configured.", parent=self.winfo_toplevel())

    def on_tree_select(self, event=None):
        """Updates button states based on Treeview selection."""
        selected_item = self.assignments_tree.selection()
        has_selection = bool(selected_item)
        
        self.delete_button.config(state="normal" if has_selection else "disabled")
        self.edit_button.config(state="normal" if has_selection else "disabled") # Enable/disable edit button
        self.mark_complete_button.config(state="normal" if has_selection else "disabled")
        self.mark_incomplete_button.config(state="normal" if has_selection else "disabled")

    def _edit_selected_assignment(self):
        """Opens the Add/Edit dialog for the currently selected assignment."""
        selected_assignment_obj = self._get_selected_assignment_object()
        if not selected_assignment_obj:
            messagebox.showinfo("Edit Assignment", "Please select an assignment to edit.", parent=self)
            return

        # Get the theme provider callback from the main app instance.
        # self.master is the notebook, self.master.master is HomeworkTrackerApp.
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
        # self.update_assignments_list() # The trace on search_var should trigger this automatically


if __name__ == '__main__':
    # Example usage for testing this tab independently
    root = tk.Tk()
    root.title("Assignments Tab Test")

    # Sample assignments data for testing
    from datetime import datetime, timedelta # Required for sample data
    sample_assignments_list = [
        {'id': 1, 'name': 'Math Homework Chapter 3', 'class': 'Mathematics', 'due_date': datetime.now() + timedelta(days=2), 'priority': 'High', 'difficulty': 7, 'completed': False},
        {'id': 2, 'name': 'History Paper on Rome', 'class': 'History', 'due_date': datetime.now() + timedelta(days=5), 'priority': 'Medium', 'difficulty': 5, 'completed': False},
        {'id': 3, 'name': 'Science Lab Report', 'class': 'Science', 'due_date': datetime.now() + timedelta(days=1), 'priority': 'High', 'difficulty': 8, 'completed': True},
    ]

    def get_sample_assignments():
        return sample_assignments_list

    def sample_edit_callback(assignment_obj):
        messagebox.showinfo("Test Edit", f"Editing: {assignment_obj['name']}")

    app_cbs = {'edit_assignment': sample_edit_callback}
    
    tab = AssignmentsTab(root, get_sample_assignments, app_cbs)
    tab.pack(expand=True, fill='both')
    root.mainloop()
