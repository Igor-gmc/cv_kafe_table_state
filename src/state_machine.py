# src/state_machine.py
# Module 4 — State Machine
# Block 6: TableStateMachine — 4-state FSM.

from math import ceil

from src.config.settings import REQUIRED_OCCUPIED_SEC, REQUIRED_EMPTY_SEC

# State constants
EMPTY_CONFIRMED = "EMPTY_CONFIRMED"
CANDIDATE_OCCUPIED = "CANDIDATE_OCCUPIED"
OCCUPIED_CONFIRMED = "OCCUPIED_CONFIRMED"
CANDIDATE_EMPTY = "CANDIDATE_EMPTY"

# Presence signal constants
INTERACTING_PERSON = "interacting_person"


class TableStateMachine:
    """4-state FSM for table occupancy.

    States: EMPTY_CONFIRMED, CANDIDATE_OCCUPIED, OCCUPIED_CONFIRMED, CANDIDATE_EMPTY
    Events emitted: became_occupied, approach, became_empty
    """

    def __init__(self, fps: float):
        self._state = EMPTY_CONFIRMED
        self._counter = 0
        self._required_occupied_frames = ceil(REQUIRED_OCCUPIED_SEC * fps)
        self._required_empty_frames = ceil(REQUIRED_EMPTY_SEC * fps)

    @property
    def current_state(self) -> str:
        return self._state

    def update(
        self, presence_signal: str, frame_idx: int, timestamp_sec: float
    ) -> list[dict]:
        """Process one frame's presence signal. Returns list of emitted events (may be empty)."""
        events = []
        is_interacting = presence_signal == INTERACTING_PERSON

        if self._state == EMPTY_CONFIRMED:
            if is_interacting:
                self._state = CANDIDATE_OCCUPIED
                self._counter = 1

        elif self._state == CANDIDATE_OCCUPIED:
            if is_interacting:
                self._counter += 1
                if self._counter >= self._required_occupied_frames:
                    prev = EMPTY_CONFIRMED
                    self._state = OCCUPIED_CONFIRMED
                    self._counter = 0
                    events.append(self._make_event(
                        "became_occupied", frame_idx, timestamp_sec, prev, OCCUPIED_CONFIRMED
                    ))
                    events.append(self._make_event(
                        "approach", frame_idx, timestamp_sec, prev, OCCUPIED_CONFIRMED
                    ))
            else:
                self._state = EMPTY_CONFIRMED
                self._counter = 0

        elif self._state == OCCUPIED_CONFIRMED:
            if not is_interacting:
                self._state = CANDIDATE_EMPTY
                self._counter = 1

        elif self._state == CANDIDATE_EMPTY:
            if not is_interacting:
                self._counter += 1
                if self._counter >= self._required_empty_frames:
                    prev = OCCUPIED_CONFIRMED
                    self._state = EMPTY_CONFIRMED
                    self._counter = 0
                    events.append(self._make_event(
                        "became_empty", frame_idx, timestamp_sec, prev, EMPTY_CONFIRMED
                    ))
            else:
                self._state = OCCUPIED_CONFIRMED
                self._counter = 0

        return events

    @staticmethod
    def _make_event(
        event_type: str,
        frame_idx: int,
        timestamp_sec: float,
        prev_state: str,
        new_state: str,
    ) -> dict:
        return {
            "frame_idx": frame_idx,
            "timestamp_sec": timestamp_sec,
            "event_type": event_type,
            "prev_state": prev_state,
            "new_state": new_state,
        }
