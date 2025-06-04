from datetime import datetime
from .data_handler import DataHandler

class AssignmentManager:
    """Manages CRUD operations for assignments."""
    
    def __init__(self, data_handler: DataHandler):
        self.data_handler = data_handler
        self.assignments = self.data_handler.load_assignments()
        self._last_id = self._calculate_last_id()

    def _calculate_last_id(self):
        """Get the highest ID from existing assignments."""
        if not self.assignments:
            return 0
        return max(assignment.get('id', 0) for assignment in self.assignments if isinstance(assignment.get('id'), int))

    def _generate_id(self):
        """Generate a new unique ID."""
        self._last_id += 1
        return self._last_id

    def get_assignments(self):
        """Return all assignments."""
        return self.assignments

    def add_assignment(self, assignment_data: dict):
        """Add a new assignment."""
        name = assignment_data.get('name')
        subject_class = assignment_data.get('class')
        due_date = assignment_data.get('due_date')
        priority = assignment_data.get('priority')
        difficulty = assignment_data.get('difficulty')
        completed = assignment_data.get('completed', False)

        # Basic validation
        if not all([name, subject_class, due_date, priority, difficulty is not None]):
            return False, "Name, class, due date, priority, and difficulty are required."
        
        if not isinstance(due_date, datetime):
            return False, f"Due date must be a datetime object, got {type(due_date)}."

        try:
            difficulty_val = int(difficulty)
            if not (1 <= difficulty_val <= 10):
                return False, "Difficulty must be between 1 and 10."
        except ValueError:
            return False, "Difficulty must be a valid integer."

        new_id = self._generate_id()
        new_assignment = {
            'id': new_id, 
            'name': str(name),
            'class': str(subject_class),
            'due_date': due_date,
            'priority': str(priority), 
            'difficulty': difficulty_val,
            'completed': bool(completed),
            'date_added': datetime.now() 
        }
        
        self.assignments.append(new_assignment)
        if self.data_handler.save_assignments(self.assignments):
            return True, new_id
        else:
            # Rollback if save failed
            self.assignments.pop() 
            self._last_id -= 1
            return False, "Failed to save assignment."

    def update_assignment(self, updated_data: dict):
        """Update an existing assignment."""
        assignment_id = updated_data.get('id')
        if assignment_id is None:
            return False, "Assignment ID is required for update."

        assignment_to_update = self.get_assignment_by_id(assignment_id)
        if not assignment_to_update:
            return False, f"Assignment with ID '{assignment_id}' not found."

        original_assignment_copy = assignment_to_update.copy()

        # Update fields
        for key, value in updated_data.items():
            if key == 'id':
                continue
            if key == 'details':
                continue
            if key == 'due_date':
                if isinstance(value, datetime):
                    assignment_to_update[key] = value
                elif isinstance(value, str):
                    try:
                        assignment_to_update[key] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        return False, f"Invalid date format: {value}."
                else:
                    return False, f"Invalid type for due_date: {type(value)}."
            elif key == 'difficulty':
                try:
                    difficulty_val = int(value)
                    if not (1 <= difficulty_val <= 10):
                        return False, "Difficulty must be between 1 and 10."
                    assignment_to_update[key] = difficulty_val
                except ValueError:
                    return False, "Invalid difficulty value."
            elif key in assignment_to_update:
                assignment_to_update[key] = value
        
        if self.data_handler.save_assignments(self.assignments):
            return True, "Assignment updated successfully."
        else:
            # Rollback on save failure
            index = self.assignments.index(assignment_to_update)
            self.assignments[index] = original_assignment_copy
            return False, "Failed to save assignment update."

    def delete_assignment(self, assignment_id):
        """Delete an assignment by ID."""
        assignment_to_delete = self.get_assignment_by_id(assignment_id)
        if assignment_to_delete:
            self.assignments.remove(assignment_to_delete)
            if self.data_handler.save_assignments(self.assignments):
                return True, "Assignment deleted successfully."
            else:
                self.assignments.append(assignment_to_delete)
                return False, "Failed to save after deletion."
        return False, f"Assignment with ID '{assignment_id}' not found."

    def set_completion_status(self, assignment_id, completed: bool):
        """Set assignment completion status."""
        assignment_to_update = self.get_assignment_by_id(assignment_id)
        if assignment_to_update:
            current_status = assignment_to_update.get('completed', False)
            if current_status == completed:
                return True, f"Assignment already marked as {'complete' if completed else 'incomplete'}."

            assignment_to_update['completed'] = completed
            if self.data_handler.save_assignments(self.assignments):
                return True, "Completion status updated successfully."
            else:
                assignment_to_update['completed'] = not completed 
                return False, "Failed to save completion status."
        return False, f"Assignment with ID '{assignment_id}' not found."

    def get_assignment_by_id(self, assignment_id):
        """Get assignment by ID."""
        for assignment in self.assignments:
            if str(assignment.get('id')) == str(assignment_id):
                return assignment
        return None
