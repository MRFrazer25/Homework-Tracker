"""Crash-safe writing and backing up of the app's JSON files."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


def write_json_atomic(path, data, indent=2):
    """Writes to a temp file and swaps it in, so a crash mid-write can't leave the real file half-written."""
    path = Path(path)
    tmp_file = path.with_name(path.name + '.tmp')
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, path)
    except BaseException:
        tmp_file.unlink(missing_ok=True)
        raise


def back_up_file(path):
    """Copies the file to '<name>.corrupted.<timestamp>' next to it and returns the copy's path."""
    path = Path(path)
    backup_path = path.with_name(f"{path.name}.corrupted.{datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(path, backup_path)
    return backup_path
