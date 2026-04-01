# src/event_logger.py
# Модуль 5 — Логгер событий
# Блок 7: EventLogger — хранилище событий, CSV обновляется при каждом новом событии.

import pandas as pd


class EventLogger:
    """Накапливает события в список и обновляет CSV при каждом новом событии."""

    _COLUMNS = ["frame_idx", "timestamp_sec", "event_type", "prev_state", "new_state"]

    def __init__(self, csv_path: str):
        self._csv_path = csv_path
        self._events: list[dict] = []

    def log(self, event: dict):
        self._events.append(event)
        self._flush()

    def get_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self._events, columns=self._COLUMNS)

    def _flush(self):
        pd.DataFrame(self._events, columns=self._COLUMNS).to_csv(
            self._csv_path, index=False
        )

    def close(self):
        self._flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
