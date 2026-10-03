"""Headless smoke test: build the real window, add an assignment, check the Assignments tab."""

from datetime import datetime

import pytest

from src.core.chatbot import Chatbot
from src.gui.app import HomeworkTrackerApp


@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    """Point every data path at a temp dir and skip downloading language models."""
    monkeypatch.setattr("src.core.data_handler.DATA_DIR", tmp_path)
    monkeypatch.setattr("src.core.chatbot.DATA_DIR", tmp_path)
    monkeypatch.setattr("src.core.chatbot.PERSISTENT_CHAT_LOG_FILE", tmp_path / "persistent_chat_log.json")
    monkeypatch.setattr("src.utils.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("src.utils.settings_manager.DATA_DIR", tmp_path)
    monkeypatch.setattr("src.utils.settings_manager.SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(Chatbot, "start_loading_models", lambda self: None)
    # The add/edit handlers pop message boxes; keep the test non-interactive
    monkeypatch.setattr("src.gui.app.messagebox.showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.gui.app.messagebox.showerror", lambda *args, **kwargs: None)

    import ttkbootstrap as ttkbs
    root = ttkbs.Window(themename="litera")
    app = HomeworkTrackerApp(root, {"theme": "litera", "assistant_model": None})
    root.update_idletasks()
    root.update()
    try:
        yield app, root, tmp_path
    finally:
        root.destroy()


def _tree_names(app):
    tree = app.assignments_tab_instance.assignments_tree
    names = []
    for item_id in tree.get_children():
        values = tree.item(item_id, "values")
        names.append(values[1])  # Name column
    return names


def test_window_add_assignment_appears_on_assignments_tab(isolated_app):
    app, root, tmp_path = isolated_app
    assert app.assignments_tab_instance is not None
    assert _tree_names(app) == []
    assert not (tmp_path / "assignments.json").exists() or (
        tmp_path / "assignments.json").read_text(encoding="utf-8").strip() in ("", "[]")

    app.handle_add_assignment_request({
        "name": "Smoke Test Essay",
        "class": "English",
        "due_date": datetime(2030, 5, 1, 23, 59),
        "priority": "High",
        "difficulty": 6,
    })
    root.update_idletasks()
    root.update()

    assert _tree_names(app) == ["Smoke Test Essay"]
    saved = app.data_handler.load_assignments()
    assert [a["name"] for a in saved] == ["Smoke Test Essay"]
    assert "Smoke Test Essay" in (tmp_path / "assignments.json").read_text(encoding="utf-8")
    assert app.data_handler.load_error is None
