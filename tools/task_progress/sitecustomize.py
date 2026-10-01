"""Opt-in, read-only stack sampling for project task progress (no model changes)."""
import os

if os.environ.get("COIN_TASK_PROGRESS") == "1":
    import task_progress_sample
    task_progress_sample.start()
