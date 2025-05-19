import json
from datetime import datetime
from pathlib import Path

class DataHandler:
    """Handles all data operations for the homework tracker"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / 'data'
        self.assignments_file = self.data_dir / 'assignments.json'
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize empty assignments list if file doesn't exist
        if not self.assignments_file.exists():
            self.save_assignments([])
    
    def load_assignments(self):
        """Load assignments from JSON file"""
        try:
            with open(self.assignments_file, 'r') as f:
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
                                assignment['due_date'] = None 
                    if 'date_added' in assignment and isinstance(assignment['date_added'], str):
                        try:
                            assignment['date_added'] = datetime.strptime(assignment['date_added'], '%Y-%m-%d %H:%M:%S.%f') # datetime.now() includes microseconds
                        except ValueError:
                             try: # Fallback if microseconds are not present
                                assignment['date_added'] = datetime.strptime(assignment['date_added'], '%Y-%m-%d %H:%M:%S')
                             except ValueError:
                                assignment['date_added'] = None
                return assignments
        except FileNotFoundError:
            return [] # Return empty list if file does not exist
        except json.JSONDecodeError:
            # Backup corrupted file
            try:
                corrupted_backup_path = self.assignments_file.with_suffix(f'.json.corrupted.{datetime.now().strftime("%Y%m%d%H%M%S")}')
                self.assignments_file.rename(corrupted_backup_path)
            except Exception:
                pass # Silently pass backup error, main error is decode error
            return [] # Return empty list if JSON is corrupted
        except Exception:
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
            
            # Save to file with pretty printing (indent=2 for readability)
            with open(self.assignments_file, 'w') as f:
                json.dump(assignments_to_save, f, indent=2)
            return True
        except Exception:
            return False
    
    def get_assignment_categories(self):
        """Get list of available assignment categories"""
        return [
            'Exam',
            'Quiz',
            'Homework',
            'Project',
            'Paper',
            'Lab',
            'Presentation',
            'Other'
        ]
    
    def get_class_list(self):
        """Get list of available classes."""
        assignments = self.load_assignments()
        # Use 'class' key, fall back to 'Uncategorized' if missing or empty
        classes = set(
            assignment.get('class', 'Uncategorized') or 'Uncategorized' 
            for assignment in assignments
        )
        # Return sorted list, perhaps with 'Uncategorized' last or first if desired
        sorted_classes = sorted(list(classes), key=lambda x: (x == 'Uncategorized', x.lower()))
        return sorted_classes

    def get_priority_levels(self):
        """Get list of priority levels with descriptions"""
        return {
            'High': 'Urgent and Important',
            'Medium': 'Important but not Urgent',
            'Low': 'Can be done later'
        }

    def get_assignment_by_id(self, assignment_id):
        """Get a single assignment by its ID."""
        assignments = self.load_assignments()
        for assignment in assignments:
            if assignment.get('id') == assignment_id:
                return assignment
        return None
