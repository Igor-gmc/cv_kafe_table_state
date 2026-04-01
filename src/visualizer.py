# src/visualizer.py
# Модуль 6 — Визуализация
# Блок 9: draw_frame — аннотирует каждый кадр прямоугольником ROI, рамками bbox людей, меткой состояния.

import cv2
import numpy as np

# Состояние -> цвет BGR
_STATE_COLORS = {
    "EMPTY_CONFIRMED": (0, 200, 0),       # зелёный
    "OCCUPIED_CONFIRMED": (0, 0, 200),     # красный
    "CANDIDATE_OCCUPIED": (0, 200, 200),   # жёлтый
    "CANDIDATE_EMPTY": (0, 200, 200),      # жёлтый
}

_DEFAULT_COLOR = (200, 200, 200)  # серый запасной цвет


def draw_frame(
    frame: np.ndarray,
    detections: list[tuple[tuple[int, int, int, int], float]],
    table_zone: tuple[int, int, int, int],
    current_state: str,
    presence_signal: str,
) -> np.ndarray:
    """Аннотировать кадр для выходного видео. Возвращает копию."""
    out = frame.copy()
    color = _STATE_COLORS.get(current_state, _DEFAULT_COLOR)

    # Нарисовать прямоугольник TABLE_ZONE
    x1, y1, x2, y2 = table_zone
    cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

    # Метка состояния на ROI
    label = current_state.replace("_", " ")
    cv2.putText(out, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Рамки bbox людей и опорные точки
    for bbox, conf in detections:
        bx1, by1, bx2, by2 = bbox
        cv2.rectangle(out, (bx1, by1), (bx2, by2), (255, 255, 255), 1)
        # Опорная точка
        cx = bx1 + (bx2 - bx1) // 2
        cy = by2
        cv2.circle(out, (cx, cy), 4, (0, 255, 255), -1)

    # Сигнал присутствия в левом верхнем углу
    cv2.putText(out, presence_signal, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    return out
