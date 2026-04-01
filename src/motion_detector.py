# motion_detector.py
# Детектор движения на основе вычитания фона (MOG2).
# Используется как резервный сигнал, когда YOLO не обнаруживает людей
# (например, человек наклоняется над столом, съёмка сверху).

import cv2
import numpy as np


class MotionDetector:
    """Определяет наличие движения в заданной зоне (table_zone) с помощью MOG2."""

    def __init__(self, table_zone: tuple[int, int, int, int]) -> None:
        """
        Параметры
        ---------
        table_zone : tuple[int, int, int, int]
            Координаты зоны столика в формате (x1, y1, x2, y2).
        """
        self._table_zone = table_zone
        # history=500  — количество кадров для построения модели фона
        # varThreshold=50 — порог дисперсии; выше = меньше шума, но медленнее реакция
        # detectShadows=False — не выделять тени (экономия CPU, нам тени не нужны)
        self._subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=50,
            detectShadows=False,
        )

    def update(self, frame: np.ndarray) -> float:
        """
        Применить вычитание фона к кадру и вернуть долю пикселей движения в зоне.

        Параметры
        ---------
        frame : np.ndarray
            Текущий кадр в формате BGR (как возвращает cv2.VideoCapture).

        Возвращает
        ----------
        float
            Доля белых пикселей в маске движения внутри table_zone (от 0.0 до 1.0).
            0.0 — движения нет, 1.0 — вся зона в движении.
        """
        # Получить маску переднего плана для всего кадра
        fg_mask = self._subtractor.apply(frame)

        # Обрезать маску до table_zone
        x1, y1, x2, y2 = self._table_zone
        zone_mask = fg_mask[y1:y2, x1:x2]

        # Если зона пустая (некорректные координаты), вернуть 0
        total_pixels = zone_mask.size
        if total_pixels == 0:
            return 0.0

        # Белые пиксели (255) — движение; подсчитать долю
        motion_pixels = int(np.count_nonzero(zone_mask))
        return motion_pixels / total_pixels
