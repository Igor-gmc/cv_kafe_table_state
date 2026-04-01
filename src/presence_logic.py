# src/presence_logic.py
# Модуль 3 — ROI столика / Логика присутствия
# Блок 5: классификация опорной точки и агрегация presence_signal.

from math import hypot

from src.config.settings import TRANSIT_DISPLACEMENT_PX


def _foot_point(bbox: tuple[int, int, int, int]) -> tuple[int, int]:
    """Нижний центр ограничивающего прямоугольника."""
    x1, y1, x2, y2 = bbox
    cx = x1 + (x2 - x1) // 2
    return (cx, y2)


def _bbox_center(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
    """Центр ограничивающего прямоугольника."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _point_inside(point: tuple[int, int], zone: tuple[int, int, int, int]) -> bool:
    """Проверка вхождения AABB: находится ли точка внутри зоны?"""
    px, py = point
    x1, y1, x2, y2 = zone
    return x1 <= px <= x2 and y1 <= py <= y2


def _bbox_overlaps(bbox: tuple[int, int, int, int], roi: tuple[int, int, int, int]) -> bool:
    """Проверка перекрытия AABB: перекрываются ли bbox и roi?"""
    ax1, ay1, ax2, ay2 = bbox
    bx1, by1, bx2, by2 = roi
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def _match_prev_bbox(
    center: tuple[float, float],
    prev_centers: list[tuple[float, float]],
) -> tuple[float, float] | None:
    """Найти ближайший предыдущий центр bbox (простой nearest-neighbor)."""
    if not prev_centers:
        return None
    best = None
    best_dist = float("inf")
    for pc in prev_centers:
        d = hypot(center[0] - pc[0], center[1] - pc[1])
        if d < best_dist:
            best_dist = d
            best = pc
    return best


def _is_moving(
    bbox: tuple[int, int, int, int],
    prev_centers: list[tuple[float, float]],
) -> bool:
    """Определить, движется ли человек (смещение центра > порога)."""
    if not prev_centers:
        return False
    center = _bbox_center(bbox)
    matched = _match_prev_bbox(center, prev_centers)
    if matched is None:
        return False
    dist = hypot(center[0] - matched[0], center[1] - matched[1])
    return dist > TRANSIT_DISPLACEMENT_PX


def classify_person(
    bbox: tuple[int, int, int, int],
    table_zone: tuple[int, int, int, int],
    prev_centers: list[tuple[float, float]] | None = None,
) -> str:
    """Классифицировать отношение одного человека к столику.

    Логика:
    - опорная точка (нижний центр bbox) внутри table_zone:
        - если центр bbox сместился > TRANSIT_DISPLACEMENT_PX → "transit"
        - иначе → "interacting"
    - bbox перекрывает table_zone, но опорная точка снаружи:
        - если человек НЕ движется (стоит у столика) → "interacting"
        - если движется (проходит мимо) → "transit"
    - иначе → "irrelevant"

    Возвращает: "interacting" | "transit" | "irrelevant"
    """
    fp = _foot_point(bbox)
    if _point_inside(fp, table_zone):
        if prev_centers and _is_moving(bbox, prev_centers):
            return "transit"
        return "interacting"
    if _bbox_overlaps(bbox, table_zone):
        if prev_centers and _is_moving(bbox, prev_centers):
            return "transit"
        return "interacting"
    return "irrelevant"


def compute_presence_signal(
    detections: list[tuple[tuple[int, int, int, int], float]],
    table_zone: tuple[int, int, int, int],
    prev_detections: list[tuple[tuple[int, int, int, int], float]] | None = None,
) -> str:
    """Агрегировать все обнаружения в единый сигнал присутствия на кадр.

    Параметры
    ---------
    prev_detections : предыдущие детекции (для трекинга скорости).
        Если None — трекинг скорости не применяется (первый кадр).

    Возвращает: "interacting_person" | "transit_person" | "no_person"
    """
    prev_centers: list[tuple[float, float]] | None = None
    if prev_detections is not None:
        prev_centers = [_bbox_center(bbox) for bbox, _ in prev_detections]

    found_interacting = False
    found_transit = False

    for bbox, _conf in detections:
        relation = classify_person(bbox, table_zone, prev_centers)
        if relation == "interacting":
            found_interacting = True
        elif relation == "transit":
            found_transit = True

    if found_interacting:
        return "interacting_person"
    if found_transit:
        return "transit_person"
    return "no_person"
