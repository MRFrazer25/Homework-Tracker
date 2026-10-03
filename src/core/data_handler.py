import json
import threading
from datetime import datetime, time
from pathlib import Path
from src.utils.json_files import back_up_file, write_json_atomic
from src.utils.paths import DATA_DIR

# The app only collects due *dates*, so assignments are due at the end of that day.
DUE_TIME = time(23, 59)

class DataHandler:
    """Handles all data operations for the homework tracker"""
    
    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.assignments_file = self.data_dir / 'assignments.json'
        # Set when the assignments file exists but can't be used; saving is then refused so it isn't overwritten
        self.load_error = None
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty assignments list if file doesn't exist
        if not self.assignments_file.exists():
            self.save_assignments([])
    
    def load_assignments(self):
        """
        Load assignments from JSON file. If the file exists but can't be read or isn't a list of assignments
        (locked, bad encoding, bad JSON, wrong shape), it is backed up, load_error explains what happened,
        and saving is refused so the real data isn't replaced by an empty list.
        """
        try:
            with open(self.assignments_file, 'r', encoding='utf-8') as f:
                assignments = json.load(f)
            if not isinstance(assignments, list) or not all(isinstance(a, dict) for a in assignments):
                raise ValueError("the file does not contain a list of assignments")
        except FileNotFoundError:
            self.load_error = None
            return []
        except Exception as e:
            self._refuse_saving_after_load_failure(e)
            return []
        self.load_error = None

        # Convert string dates back to datetime objects
        for assignment in assignments:
            if 'due_date' in assignment and isinstance(assignment['due_date'], str):
                try:
                    assignment['due_date'] = datetime.strptime(assignment['due_date'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # Try older format if migration is needed, or log error
                    try:
                        assignment['due_date'] = datetime.strptime(assignment['due_date'], '%Y-%m-%d %H:%M')
                    except ValueError:
                        print(f"Warning: Could not parse due_date '{assignment['due_date']}' for assignment '{assignment.get('name')}'. Setting to None.")
                        assignment['due_date'] = None 
            # Older versions saved due dates at midnight, which made them look overdue all day.
            if isinstance(assignment.get('due_date'), datetime) and assignment['due_date'].time() == time(0, 0):
                assignment['due_date'] = datetime.combine(assignment['due_date'].date(), DUE_TIME)
            if 'date_added' in assignment and isinstance(assignment['date_added'], str):
                try:
                    assignment['date_added'] = datetime.strptime(assignment['date_added'], '%Y-%m-%d %H:%M:%S.%f') # datetime.now() includes microseconds
                except ValueError:
                     try: # Fallback if microseconds are not present
                        assignment['date_added'] = datetime.strptime(assignment['date_added'], '%Y-%m-%d %H:%M:%S')
                     except ValueError:
                        print(f"Warning: Could not parse date_added '{assignment['date_added']}' for assignment '{assignment.get('name')}'. Setting to None.")
                        assignment['date_added'] = None
        return assignments

    def _refuse_saving_after_load_failure(self, error):
        # Copied rather than renamed: a file another program has locked often can't be moved
        try:
            backup_note = f"A copy was saved to {back_up_file(self.assignments_file)}."
        except Exception as backup_e:
            backup_note = f"It could not be backed up ({backup_e})."
        self.load_error = (f"Could not load your assignments from {self.assignments_file}: {error}\n{backup_note}\n"
                           "To protect that file, changes won't be saved. Close any program using it, or fix or "
                           "remove it, then restart the app.")
        print(self.load_error)
    
    _save_lock = threading.Lock()

    def save_assignments(self, assignments):
        """Save assignments to JSON file. Refused (returns False) if the existing file couldn't be loaded."""
        with self._save_lock:
            if self.load_error:
                print("Not saving assignments: the existing assignments file could not be loaded.")
                return False
            return self._save_assignments(assignments)

    def _save_assignments(self, assignments):
        try:
            assignments_to_save = []
            for assignment_orig in assignments:
                assignment_copy = assignment_orig.copy()
                # Convert datetime objects to strings using a consistent format
                if 'due_date' in assignment_copy and isinstance(assignment_copy['due_date'], datetime):
                    assignment_copy['due_date'] = assignment_copy['due_date'].strftime('%Y-%m-%d %H:%M:%S')
                
                if 'date_added' in assignment_copy and isinstance(assignment_copy['date_added'], datetime):
                    # datetime.now() includes microseconds, strftime with %f saves them.
                    assignment_copy['date_added'] = assignment_copy['date_added'].strftime('%Y-%m-%d %H:%M:%S.%f')
                
                assignments_to_save.append(assignment_copy)
            
            write_json_atomic(self.assignments_file, assignments_to_save)
            return True
        except Exception as e:
            print(f"Error saving assignments: {e}")
            return False
