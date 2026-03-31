# src/visualizer.py
# Module 6 — Visualization
# Block 9: draw_frame — annotates each frame with ROI rect, person bboxes, state label.

import cv2
import numpy as np

# State -> BGR color
_STATE_COLORS = {
    "EMPTY_CONFIRMED": (0, 200, 0),       # green
    "OCCUPIED_CONFIRMED": (0, 0, 200),     # red
    "CANDIDATE_OCCUPIED": (0, 200, 200),   # yellow
    "CANDIDATE_EMPTY": (0, 200, 200),      # yellow
}

_DEFAULT_COLOR = (200, 200, 200)  # gray fallback


def draw_frame(
    frame: np.ndarray,
    detections: list[tuple[tuple[int, int, int, int], float]],
    visual_roi: tuple[int, int, int, int],
    current_state: str,
    presence_signal: str,
) -> np.ndarray:
    """Annotate a frame for the output video. Returns a copy."""
    out = frame.copy()
    color = _STATE_COLORS.get(current_state, _DEFAULT_COLOR)

    # Draw visual ROI rectangle
    x1, y1, x2, y2 = visual_roi
    cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

    # State label on ROI
    label = current_state.replace("_", " ")
    cv2.putText(out, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Person bboxes and foot points
    for bbox, conf in detections:
        bx1, by1, bx2, by2 = bbox
        cv2.rectangle(out, (bx1, by1), (bx2, by2), (255, 255, 255), 1)
        # Foot point
        cx = bx1 + (bx2 - bx1) // 2
        cy = by2
        cv2.circle(out, (cx, cy), 4, (0, 255, 255), -1)

    # Presence signal in top-left corner
    cv2.putText(out, presence_signal, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    return out
