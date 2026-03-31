# src/presence_logic.py
# Module 3 — Table ROI / Presence Logic
# Block 5: foot-point classification and presence_signal aggregation.


def _foot_point(bbox: tuple[int, int, int, int]) -> tuple[int, int]:
    """Bottom-center of bounding box."""
    x1, y1, x2, y2 = bbox
    cx = x1 + (x2 - x1) // 2
    return (cx, y2)


def _point_inside(point: tuple[int, int], zone: tuple[int, int, int, int]) -> bool:
    """AABB containment: is point inside zone?"""
    px, py = point
    x1, y1, x2, y2 = zone
    return x1 <= px <= x2 and y1 <= py <= y2


def _bbox_overlaps(bbox: tuple[int, int, int, int], roi: tuple[int, int, int, int]) -> bool:
    """AABB overlap test: do bbox and roi overlap?"""
    ax1, ay1, ax2, ay2 = bbox
    bx1, by1, bx2, by2 = roi
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def classify_person(
    bbox: tuple[int, int, int, int],
    visual_roi: tuple[int, int, int, int],
    interaction_zone: tuple[int, int, int, int],
) -> str:
    """Classify a single person's relation to the table.

    Returns: "interacting" | "transit" | "irrelevant"
    """
    fp = _foot_point(bbox)
    if _point_inside(fp, interaction_zone):
        return "interacting"
    if _bbox_overlaps(bbox, visual_roi):
        return "transit"
    return "irrelevant"


def compute_presence_signal(
    detections: list[tuple[tuple[int, int, int, int], float]],
    visual_roi: tuple[int, int, int, int],
    interaction_zone: tuple[int, int, int, int],
) -> str:
    """Aggregate all detections into a single per-frame presence signal.

    Returns: "interacting_person" | "transit_person" | "no_person"
    """
    found_interacting = False
    found_transit = False

    for bbox, _conf in detections:
        relation = classify_person(bbox, visual_roi, interaction_zone)
        if relation == "interacting":
            found_interacting = True
        elif relation == "transit":
            found_transit = True

    if found_interacting:
        return "interacting_person"
    if found_transit:
        return "transit_person"
    return "no_person"
