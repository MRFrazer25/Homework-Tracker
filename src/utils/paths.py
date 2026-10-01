"""Filesystem locations used by the application."""

from pathlib import Path

# Resolve relative to the project root so the app works regardless of the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
