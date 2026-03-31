# src/detector.py
# Module 2 — Detector
# Block 4: PersonDetector — YOLOv8n wrapper.

import numpy as np
from ultralytics import YOLO

from src.config.settings import YOLO_MODEL, CONF_THRESHOLD, YOLO_IMGSZ

# COCO class 0 = person
_PERSON_CLASS_ID = 0


class PersonDetector:
    """Detects persons on a frame using YOLOv8n."""

    def __init__(self):
        self._model = YOLO(YOLO_MODEL)

    def detect(self, frame: np.ndarray) -> list[tuple[tuple[int, int, int, int], float]]:
        """Run inference, return only person detections.

        Returns:
            List of ((x1, y1, x2, y2), confidence) tuples.
            Empty list if no persons found.
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
