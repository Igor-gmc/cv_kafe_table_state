# src/table_logger.py
# Logs table status changes to file and terminal.

import logging
from pathlib import Path


class TableStatusLogger:
    """Logs table state transitions to a file and terminal simultaneously."""

    def __init__(self, log_path: str, video_source: str):
        self._video_source = video_source
        self._logger = logging.getLogger("table_status")
        self._logger.setLevel(logging.INFO)
        self._logger.handlers.clear()

        Path(log_path).parent.mkdir(parents=True, exist_ok=True)

        fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        fh.setFormatter(fmt)
        self._logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        self._logger.addHandler(ch)

        self._logger.info(f"Video: {video_source}")
        self._logger.info(f"Table status log started")

    def log_state_change(self, event: dict):
        """Log a state transition event."""
        frame = event["frame_idx"]
        ts = event["timestamp_sec"]
        etype = event["event_type"]
        prev = event["prev_state"]
        new = event["new_state"]

        minutes = int(ts // 60)
        seconds = ts % 60

        self._logger.info(
            f"[{minutes:02d}:{seconds:05.2f}] frame={frame} "
            f"{etype}: {prev} -> {new} | src={self._video_source}"
        )

    def log_summary(self, analytics: dict):
        """Log final analytics summary."""
        self._logger.info("--- Summary ---")
        self._logger.info(f"Video: {self._video_source}")
        self._logger.info(f"became_occupied: {analytics['num_became_occupied']}")
        self._logger.info(f"became_empty: {analytics['num_became_empty']}")
        self._logger.info(f"approach: {analytics['num_approach']}")
        if analytics["mean_delay_sec"] is not None:
            self._logger.info(f"mean_delay: {analytics['mean_delay_sec']:.3f} sec")
        else:
            self._logger.info("mean_delay: N/A")
        self._logger.info("--- End ---")
