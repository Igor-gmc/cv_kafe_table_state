# src/detector.py
# Модуль 2 — Детектор
# Блок 4: PersonDetector — обёртка над YOLOv8n.

import numpy as np
from ultralytics import YOLO

from src.config.settings import YOLO_MODEL, CONF_THRESHOLD, YOLO_IMGSZ

# Класс COCO 0 = человек
_PERSON_CLASS_ID = 0


class PersonDetector:
    """Обнаруживает людей на кадре с помощью YOLOv8n."""

    def __init__(self):
        self._model = YOLO(YOLO_MODEL)

    def detect(self, frame: np.ndarray) -> list[tuple[tuple[int, int, int, int], float]]:
        """Запустить инференс, вернуть только обнаружения людей.

        Возвращает:
            Список кортежей ((x1, y1, x2, y2), confidence).
            Пустой список, если люди не найдены.
        """
        results = self._model(frame, conf=CONF_THRESHOLD, imgsz=YOLO_IMGSZ, verbose=False)
        detections = []
        for result in results:
            boxes = result.boxes
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i])
                if cls_id != _PERSON_CLASS_ID:
                    continue
                x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                conf = float(boxes.conf[i])
                detections.append(((int(x1), int(y1), int(x2), int(y2)), conf))
        return detections
