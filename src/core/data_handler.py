import json
from datetime import datetime, time
from pathlib import Path
from src.utils.paths import DATA_DIR

# The app only collects due *dates*, so assignments are due at the end of that day.
DUE_TIME = time(23, 59)

class DataHandler:
    """Handles all data operations for the homework tracker"""
    
    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.assignments_file = self.data_dir / 'assignments.json'
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty assignments list if file doesn't exist
        if not self.assignments_file.exists():
            self.save_assignments([])
    
    def load_assignments(self):
        """Load assignments from JSON file"""
        try:
            with open(self.assignments_file, 'r', encoding='utf-8') as f:
                assignments = json.load(f)
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
        except FileNotFoundError:
            return [] # Return empty list if file does not exist
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from assignments file: {e}")
            # Backup corrupted file
            try:
                corrupted_backup_path = self.assignments_file.with_suffix(f'.json.corrupted.{datetime.now().strftime("%Y%m%d%H%M%S")}')
                self.assignments_file.rename(corrupted_backup_path)
                print(f"Backed up corrupted assignments file to: {corrupted_backup_path}")
            except Exception as backup_e:
                print(f"Could not back up corrupted assignments file: {backup_e}")
            return [] # Return empty list if JSON is corrupted
        except Exception as e:
            print(f"Error loading assignments: {e}")
            return [] # General catch-all
    
    def save_assignments(self, assignments):
        """Save assignments to JSON file"""
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
            
            # Write to a temp file then swap it in, so a crash mid-write can't corrupt the real file
            tmp_file = self.assignments_file.with_suffix('.json.tmp')
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(assignments_to_save, f, indent=2)
            tmp_file.replace(self.assignments_file)
            return True
        except Exception as e:
            print(f"Error saving assignments: {e}")
            return False
