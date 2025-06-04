"""Handles data loading and saving for assignments and chat history."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class DataHandler:
    """Manages data persistence for assignments and chat logs."""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.assignments_file = self.data_dir / "assignments.json"
        self.data_dir.mkdir(exist_ok=True)
        
        # Create assignments file if it doesn't exist
        if not self.assignments_file.exists():
            self.save_assignments([])
    
    def load_assignments(self) -> List[Dict[str, Any]]:
        """Load assignments from JSON file."""
        try:
            with open(self.assignments_file, 'r', encoding='utf-8') as f:
                assignments = json.load(f)
                
                # Convert string dates back to datetime objects
                for assignment in assignments:
                    if 'due_date' in assignment and isinstance(assignment['due_date'], str):
                        try:
                            assignment['due_date'] = datetime.strptime(assignment['due_date'], '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            try:
                                assignment['due_date'] = datetime.strptime(assignment['due_date'], '%Y-%m-%d %H:%M')
                            except ValueError:
                                assignment['due_date'] = None 
                    if 'date_added' in assignment and isinstance(assignment['date_added'], str):
                        try:
                            assignment['date_added'] = datetime.strptime(assignment['date_added'], '%Y-%m-%d %H:%M:%S.%f')
                        except ValueError:
                            try:
                                assignment['date_added'] = datetime.strptime(assignment['date_added'], '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                assignment['date_added'] = None
                return assignments
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            # Backup corrupted file
            try:
                corrupted_backup_path = self.assignments_file.with_suffix(f'.json.corrupted.{datetime.now().strftime("%Y%m%d%H%M%S")}')
                self.assignments_file.rename(corrupted_backup_path)
            except Exception:
                pass
            return []
        except Exception:
            return []
    
    def save_assignments(self, assignments: List[Dict[str, Any]]) -> bool:
        """Save assignments to JSON file."""
        try:
            assignments_to_save = []
            for assignment_orig in assignments:
                assignment_copy = assignment_orig.copy()
                # Convert datetime objects to strings
                if 'due_date' in assignment_copy and isinstance(assignment_copy['due_date'], datetime):
                    assignment_copy['due_date'] = assignment_copy['due_date'].strftime('%Y-%m-%d %H:%M:%S')
                
                if 'date_added' in assignment_copy and isinstance(assignment_copy['date_added'], datetime):
                    assignment_copy['date_added'] = assignment_copy['date_added'].strftime('%Y-%m-%d %H:%M:%S.%f')
                
                assignments_to_save.append(assignment_copy)
        
            with open(self.assignments_file, 'w', encoding='utf-8') as f:
                json.dump(assignments_to_save, f, indent=2)
            return True
        except Exception:
            return False
    
    def get_assignment_categories(self):
        """Get unique categories from assignments."""
        assignments = self.load_assignments()
        categories = set()
        for assignment in assignments:
            if assignment.get('category'):
                categories.add(assignment['category'])
        return sorted(list(categories))
    
    def get_assignment_by_id(self, assignment_id):
        """Get assignment by ID."""
        assignments = self.load_assignments()
        for assignment in assignments:
            if assignment.get('id') == assignment_id:
                return assignment
        return None

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

    def load_chat_history(self) -> List[Dict[str, Any]]:
        """Load chat history from JSON file."""
        file_path = self.data_dir / 'chat_history.json'
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def save_chat_history(self, chat_history: List[Dict[str, Any]]) -> bool:
        """Save chat history to JSON file."""
        try:
            with open(self.data_dir / 'chat_history.json', 'w', encoding='utf-8') as f:
                json.dump(chat_history, f, ensure_ascii=False)
            return True
        except Exception:
            return False

    def load_persistent_chat_log(self) -> List[Dict[str, Any]]:
        """Load persistent chat log from JSON file."""
        file_path = self.data_dir / 'persistent_chat_log.json'
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def save_persistent_chat_log(self, chat_log: List[Dict[str, Any]]) -> bool:
        """Save persistent chat log to JSON file."""
        try:
            with open(self.data_dir / 'persistent_chat_log.json', 'w', encoding='utf-8') as f:
                json.dump(chat_log, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
