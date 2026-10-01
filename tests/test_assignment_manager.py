import json
from datetime import datetime, timedelta

import pytest

from src.core.assignment_manager import AssignmentManager
from src.core.data_handler import DataHandler


@pytest.fixture
def data_handler(tmp_path):
    return DataHandler(data_dir=tmp_path)


@pytest.fixture
def manager(data_handler):
    return AssignmentManager(data_handler)


def make_assignment(**overrides):
    data = {
        'name': "Essay",
        'class': "English",
        'due_date': datetime(2030, 5, 1, 23, 59),
        'priority': "High",
        'difficulty': 6,
    }
    data.update(overrides)
    return data


def test_add_assigns_incrementing_ids_and_persists(manager, data_handler):
    ok1, id1 = manager.add_assignment(make_assignment())
    ok2, id2 = manager.add_assignment(make_assignment(name="Lab"))
    assert ok1 and ok2
    assert id2 == id1 + 1
    saved = data_handler.load_assignments()
    assert [a['name'] for a in saved] == ["Essay", "Lab"]
    assert saved[0]['due_date'] == datetime(2030, 5, 1, 23, 59)


@pytest.mark.parametrize("bad", [
    {'name': ""},
    {'difficulty': 11},
    {'difficulty': "hard"},
    {'due_date': "2030-05-01"},
])
def test_add_rejects_invalid_data(manager, bad):
    ok, message = manager.add_assignment(make_assignment(**bad))
    assert not ok
    assert message.startswith("Error")
    assert manager.get_assignments() == []


def test_set_completion_is_idempotent(manager):
    _, assignment_id = manager.add_assignment(make_assignment())

    manager.set_completion(assignment_id, True)
    manager.set_completion(assignment_id, True)  # Marking complete twice must not flip it back
    assert manager.get_assignment_by_id(assignment_id)['completed'] is True

    manager.set_completion(assignment_id, False)
    manager.set_completion(assignment_id, False)
    assert manager.get_assignment_by_id(assignment_id)['completed'] is False


def test_update_changes_completed_flag(manager):
    _, assignment_id = manager.add_assignment(make_assignment())
    ok, _ = manager.update_assignment({'id': assignment_id, 'completed': True, 'difficulty': 9})
    assert ok
    updated = manager.get_assignment_by_id(assignment_id)
    assert updated['completed'] is True
    assert updated['difficulty'] == 9


def test_delete(manager):
    _, assignment_id = manager.add_assignment(make_assignment())
    ok, _ = manager.delete_assignment(assignment_id)
    assert ok
    assert manager.get_assignments() == []
    ok, _ = manager.delete_assignment(assignment_id)
    assert not ok


def test_ids_continue_after_reload(data_handler):
    first = AssignmentManager(data_handler)
    _, assignment_id = first.add_assignment(make_assignment())
    second = AssignmentManager(data_handler)
    _, next_id = second.add_assignment(make_assignment(name="Next"))
    assert next_id == assignment_id + 1


def test_handles_assignments_without_int_ids(tmp_path):
    (tmp_path / 'assignments.json').write_text(json.dumps([{'id': "abc", 'name': "Old"}]))
    manager = AssignmentManager(DataHandler(data_dir=tmp_path))
    _, new_id = manager.add_assignment(make_assignment())
    assert new_id == 1


def test_midnight_due_dates_are_migrated_to_end_of_day(tmp_path):
    (tmp_path / 'assignments.json').write_text(json.dumps([
        {'id': 1, 'name': "Old", 'due_date': "2030-05-01 00:00:00"},
        {'id': 2, 'name': "Timed", 'due_date': "2030-05-01 14:30:00"},
    ]))
    loaded = DataHandler(data_dir=tmp_path).load_assignments()
    assert loaded[0]['due_date'] == datetime(2030, 5, 1, 23, 59)
    assert loaded[1]['due_date'] == datetime(2030, 5, 1, 14, 30)


def test_corrupted_file_is_backed_up(tmp_path):
    (tmp_path / 'assignments.json').write_text("{not json")
    handler = DataHandler(data_dir=tmp_path)
    assert handler.load_assignments() == []
    assert any(p.name.startswith('assignments.json.corrupted') for p in tmp_path.iterdir())


def test_save_leaves_no_temp_file(data_handler, tmp_path):
    data_handler.save_assignments([make_assignment(id=1, due_date=datetime.now() + timedelta(days=1))])
    assert sorted(p.name for p in tmp_path.iterdir()) == ['assignments.json']
