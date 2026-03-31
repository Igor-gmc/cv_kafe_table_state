# src/event_logger.py
# Module 5 — Event Logger
# Block 7: EventLogger — DataFrame-backed event store, CSV flushed on close.

import pandas as pd


class EventLogger:
    """Accumulates events in a Pandas DataFrame and writes them to CSV on close."""

    _COLUMNS = ["frame_idx", "timestamp_sec", "event_type", "prev_state", "new_state"]

    def __init__(self, csv_path: str):
        self._csv_path = csv_path
        self._df = pd.DataFrame(columns=self._COLUMNS)

    def log(self, event: dict):
        row = pd.DataFrame([event], columns=self._COLUMNS)
        self._df = pd.concat([self._df, row], ignore_index=True)

    def get_dataframe(self) -> pd.DataFrame:
        return self._df.copy()

    def close(self):
        self._df.to_csv(self._csv_path, index=False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
