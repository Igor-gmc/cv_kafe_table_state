# src/surface_comparator.py
# Визуальное сравнение поверхности столика с эталоном «чистого» состояния.
# Если поверхность отличается от эталона на ≥ SURFACE_DIFF_THRESHOLD,
# столик считается грязным (занятым), даже если людей нет.

import cv2
import numpy as np

from src.config.settings import SURFACE_DIFF_THRESHOLD, SURFACE_PIXEL_THRESHOLD


class SurfaceComparator:
    """Сравнивает текущий вид TABLE_ZONE с эталоном чистого столика."""

    def __init__(self, table_zone: tuple[int, int, int, int]):
        self._zone = table_zone
        self._reference: np.ndarray | None = None

    @property
    def has_reference(self) -> bool:
        return self._reference is not None

    def capture_reference(self, frame: np.ndarray) -> None:
        """Сохранить эталон чистого столика из текущего кадра."""
        crop = self._crop(frame)
        self._reference = self._prepare(crop)

    def is_surface_dirty(self, frame: np.ndarray) -> bool:
        """Сравнить текущий кадр с эталоном. True если отличие ≥ порога."""
        if self._reference is None:
            return False
        crop = self._crop(frame)
        current = self._prepare(crop)
        diff = cv2.absdiff(self._reference, current)
        _, binary = cv2.threshold(diff, SURFACE_PIXEL_THRESHOLD, 255, cv2.THRESH_BINARY)
        changed = int(np.count_nonzero(binary))
        total = binary.size
        if total == 0:
            return False
        ratio = changed / total
        return ratio >= SURFACE_DIFF_THRESHOLD

    def _crop(self, frame: np.ndarray) -> np.ndarray:
        x1, y1, x2, y2 = self._zone
        return frame[y1:y2, x1:x2]

    @staticmethod
    def _prepare(crop: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (7, 7), 0)
