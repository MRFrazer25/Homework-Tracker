from datetime import datetime
from .data_handler import DataHandler # Assuming DataHandler is in the same directory

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
                             'priority', 'difficulty', 'details' (optional), 'completed' (optional).

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
        details = assignment_data.get('details', "")
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
            'details': str(details),
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

        # Update fields present in updated_data
        for key, value in updated_data.items():
            if key == 'id': # Do not update ID
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

    def toggle_completion(self, assignment_id):
        """
        Toggles the 'completed' status of an assignment by its ID.

        Args:
            assignment_id: The ID of the assignment to toggle.

        Returns:
            tuple: (bool_success, message_string)
        """
        assignment_to_toggle = self.get_assignment_by_id(assignment_id)
        if assignment_to_toggle:
            assignment_to_toggle['completed'] = not assignment_to_toggle.get('completed', False)
            if self.data_handler.save_assignments(self.assignments):
                return True, "Completion status toggled successfully."
            else:
                # Rollback toggle if save fails
                assignment_to_toggle['completed'] = not assignment_to_toggle['completed']
                return False, "Error: Failed to save assignments after toggling completion."
        return False, f"Error: Assignment with ID '{assignment_id}' not found for toggling completion."

    def get_assignment_by_id(self, assignment_id):
        """Retrieves an assignment by its ID."""
        for assignment in self.assignments:
            # Ensure consistent type comparison for ID, e.g. if ID can be int or str
            if str(assignment.get('id')) == str(assignment_id):
                return assignment
        return None


if __name__ == '__main__':
    # Example usage for testing AssignmentManager
    # This requires a mock or real DataHandler
    class MockDataHandler:
        def __init__(self):
            self.temp_assignments = []
        def load_assignments(self):
            print("MockDataHandler: Loading assignments")
            return list(self.temp_assignments) # Return a copy
        def save_assignments(self, assignments_list):
            print(f"MockDataHandler: Saving {len(assignments_list)} assignments")
            self.temp_assignments = list(assignments_list) # Save a copy
            return True

    mock_dh = MockDataHandler()
    manager = AssignmentManager(mock_dh)

    print("Initial assignments:", manager.get_assignments())
    
    # Add an assignment
    success_add1, result1 = manager.add_assignment({
        'name': "Test Math HW", 'class': "Math", 
        'due_date': datetime.strptime("2024-12-20 14:00", '%Y-%m-%d %H:%M'), 
        'priority': "High", 'difficulty': 7, 'details': "Chapter 1 problems"
    })
    added_id1 = None
    if success_add1:
        added_id1 = result1
        print(f"Added: Test Math HW with ID {added_id1}")
    else:
        print(f"Failed to add Test Math HW: {result1}")

    success_add2, result2 = manager.add_assignment({
        'name': "History Reading", 'class': "History", 
        'due_date': datetime.strptime("2024-12-15 23:59", '%Y-%m-%d %H:%M'),
        'priority': "Medium", 'difficulty': 4
    })
    added_id2 = None
    if success_add2:
        added_id2 = result2
        print(f"Added: History Reading with ID {added_id2}")
    else:
        print(f"Failed to add History Reading: {result2}")

    print("Current assignments count:", len(manager.get_assignments()))
    # print("Full list:", manager.get_assignments())


    # Update an assignment
    if added_id1:
        success_update, msg_update = manager.update_assignment({
            'id': added_id1, 'completed': True, 'difficulty': 8, 'details': "All problems done."
        })
        if success_update:
            updated_assign1 = manager.get_assignment_by_id(added_id1)
            print(f"Updated 'Test Math HW': Completed={updated_assign1['completed']}, Difficulty={updated_assign1['difficulty']}")
        else:
            print(f"Failed to update Test Math HW: {msg_update}")


    # Toggle completion
    if added_id2:
        original_assign2 = manager.get_assignment_by_id(added_id2) # Get object before toggle for name
        name_assign2 = original_assign2.get('name') if original_assign2 else "ID " + str(added_id2)

        success_toggle1, msg_toggle1 = manager.toggle_completion(added_id2)
        if success_toggle1:
            toggled_assign2 = manager.get_assignment_by_id(added_id2)
            print(f"Toggled '{name_assign2}': Completed={toggled_assign2['completed']}")
        else:
            print(f"Failed to toggle {name_assign2}: {msg_toggle1}")

        success_toggle2, msg_toggle2 = manager.toggle_completion(added_id2) # Toggle back
        if success_toggle2:
            toggled_assign2_again = manager.get_assignment_by_id(added_id2)
            print(f"Toggled again '{name_assign2}': Completed={toggled_assign2_again['completed']}")
        else:
             print(f"Failed to toggle again {name_assign2}: {msg_toggle2}")


    # Delete an assignment
    if added_id1:
        original_assign1 = manager.get_assignment_by_id(added_id1) # Get object before delete for name
        name_assign1 = original_assign1.get('name') if original_assign1 else "ID " + str(added_id1)
        success_delete, msg_delete = manager.delete_assignment(added_id1)
        if success_delete:
            print(f"Deleted '{name_assign1}'")
        else:
            print(f"Failed to delete {name_assign1}: {msg_delete}")
    
    print("Final assignments count:", len(manager.get_assignments()))
