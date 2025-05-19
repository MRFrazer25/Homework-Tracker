from datetime import datetime
from .data_handler import DataHandler

class AssignmentManager:
    """Manages CRUD operations for assignments."""
    def __init__(self, data_handler: DataHandler):
        """
        Initializes the AssignmentManager.

        Args:
            data_handler: An instance of DataHandler to load/save assignments.
        """
        self.data_handler = data_handler
        self.assignments = self.data_handler.load_assignments()
        self._last_id = self._calculate_last_id()

    def _calculate_last_id(self):
        """Calculates the last used ID from loaded assignments."""
        if not self.assignments:
            return 0
        return max(assignment.get('id', 0) for assignment in self.assignments if isinstance(assignment.get('id'), int))

    def _generate_id(self):
        """Generates a new unique ID for an assignment."""
        self._last_id += 1
        return self._last_id

    def get_assignments(self):
        """Returns the current list of all assignments."""
        return self.assignments

    def add_assignment(self, assignment_data: dict):
        """
        Adds a new assignment to the list and saves it.

        Args:
            assignment_data: A dictionary containing the new assignment's details.
                             Expected keys: 'name', 'class', 'due_date' (datetime object),
                             'priority', 'difficulty', 'completed' (optional).

        Returns:
            tuple: (bool_success, message_or_new_id)
                   (True, new_assignment_id) on success.
                   (False, error_message_string) on failure.
        """
        name = assignment_data.get('name')
        subject_class = assignment_data.get('class') # 'class' is a reserved keyword, using subject_class internally
        due_date = assignment_data.get('due_date') # Expected to be a datetime object
        priority = assignment_data.get('priority')
        difficulty = assignment_data.get('difficulty')
        completed = assignment_data.get('completed', False)

        # Basic validation
        if not all([name, subject_class, due_date, priority, difficulty is not None]):
            return False, "Error: Name, class, due date, priority, and difficulty are required."
        
        if not isinstance(due_date, datetime):
            return False, f"Error: Due date must be a datetime object, got {type(due_date)}."

        try:
            difficulty_val = int(difficulty)
            if not (1 <= difficulty_val <= 10):
                return False, "Error: Difficulty must be an integer between 1 and 10."
        except ValueError:
            return False, "Error: Difficulty must be a valid integer."

        new_id = self._generate_id()
        new_assignment = {
            'id': new_id, 
            'name': str(name),
            'class': str(subject_class),
            'due_date': due_date, # Already a datetime object
            'priority': str(priority), 
            'difficulty': difficulty_val,
            'completed': bool(completed),
            'date_added': datetime.now() 
        }
        self.assignments.append(new_assignment)
        if self.data_handler.save_assignments(self.assignments):
            return True, new_id
        else:
            # Attempt to roll back if save failed (though this is rare for file-based save)
            self.assignments.pop() 
            self._last_id -=1 # Decrement ID if save failed
            return False, "Error: Failed to save assignments after adding."

    def update_assignment(self, updated_data: dict):
        """
        Updates an existing assignment identified by 'id' in updated_data.

        Args:
            updated_data: A dictionary containing the assignment 'id' and fields to update.

        Returns:
            tuple: (bool_success, message_string)
        """
        assignment_id = updated_data.get('id')
        if assignment_id is None:
            return False, "Error: Assignment ID is required for an update."

        assignment_to_update = self.get_assignment_by_id(assignment_id)
        if not assignment_to_update:
            return False, f"Error: Assignment with ID '{assignment_id}' not found."

        original_assignment_copy = assignment_to_update.copy() # Create a shallow copy for rollback

        # Updates fields present in updated_data
        for key, value in updated_data.items():
            if key == 'id': # Do not update ID
                continue
            if key == 'details': # Ignore details if present in data from older versions
                continue
            if key == 'due_date':
                if isinstance(value, datetime):
                    assignment_to_update[key] = value
                elif isinstance(value, str): # Attempt to parse if string
                    try:
                        assignment_to_update[key] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S') # Or common format
                    except ValueError:
                        return False, f"Error: Invalid date format for due_date: {value}."
                else:
                    return False, f"Error: Invalid type for due_date: {type(value)}."
            elif key == 'difficulty':
                try:
                    difficulty_val = int(value)
                    if not (1 <= difficulty_val <= 10):
                        return False, "Error: Difficulty must be between 1 and 10."
                    assignment_to_update[key] = difficulty_val
                except ValueError:
                    return False, "Error: Invalid difficulty value."
            elif key in assignment_to_update: # Ensure key is valid for assignment model
                assignment_to_update[key] = value
        
        if self.data_handler.save_assignments(self.assignments):
            return True, "Assignment updated successfully."
        else:
            # Restore the original state of the assignment in memory if save failed
            index = self.assignments.index(assignment_to_update) # Find the modified one
            self.assignments[index] = original_assignment_copy # Restore from copy
            # Note: If save fails, in-memory change is still there. A more robust system might reload.
            return False, "Error: Failed to save assignments after update."

    def delete_assignment(self, assignment_id):
        """
        Deletes an assignment by its ID.

        Args:
            assignment_id: The ID of the assignment to delete.

        Returns:
            tuple: (bool_success, message_string)
        """
        assignment_to_delete = self.get_assignment_by_id(assignment_id)
        if assignment_to_delete:
            self.assignments.remove(assignment_to_delete)
            if self.data_handler.save_assignments(self.assignments):
                return True, "Assignment deleted successfully."
            else:
                self.assignments.append(assignment_to_delete) # Rollback remove if save fails
                return False, "Error: Failed to save assignments after deletion."
        return False, f"Error: Assignment with ID '{assignment_id}' not found for deletion."

    def set_completion_status(self, assignment_id, completed: bool):
        """
        Sets the 'completed' status of an assignment by its ID.

        Args:
            assignment_id: The ID of the assignment to update.
            completed (bool): The new completion status (True for complete, False for incomplete).

        Returns:
            tuple: (bool_success, message_string)
        """
        assignment_to_update = self.get_assignment_by_id(assignment_id)
        if assignment_to_update:
            current_status = assignment_to_update.get('completed', False)
            if current_status == completed:
                # No change needed, or could return a specific message
                return True, f"Assignment is already marked as {'complete' if completed else 'incomplete'}."

            assignment_to_update['completed'] = completed
            if self.data_handler.save_assignments(self.assignments):
                return True, "Completion status updated successfully."
            else:
                # Rollback status update if save fails
                assignment_to_update['completed'] = not completed 
                return False, "Error: Failed to save assignments after updating completion."
        return False, f"Error: Assignment with ID '{assignment_id}' not found for updating completion."

    def get_assignment_by_id(self, assignment_id):
        """Retrieves an assignment by its ID."""
        for assignment in self.assignments:
            # Ensure consistent type comparison for ID, e.g. if ID can be int or str
            if str(assignment.get('id')) == str(assignment_id):
                return assignment
        return None
