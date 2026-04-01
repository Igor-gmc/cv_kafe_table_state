# src/analytics.py
# Модуль 5 — Аналитика
# Блок 8: compute_analytics и save_report.

import pandas as pd


def compute_analytics(events: pd.DataFrame) -> dict:
    """Найти пары (became_empty, approach); вычислить задержки.

    Возвращает словарь со счётчиками и mean_delay_sec (None, если нет валидных пар).
    """
    num_became_occupied = int((events["event_type"] == "became_occupied").sum())
    num_became_empty = int((events["event_type"] == "became_empty").sum())
    num_approach = int((events["event_type"] == "approach").sum())

    delays = []
    last_empty_time = None

    for _, row in events.iterrows():
        if row["event_type"] == "became_empty":
            last_empty_time = row["timestamp_sec"]
        elif row["event_type"] == "approach" and last_empty_time is not None:
            delay = row["timestamp_sec"] - last_empty_time
            delays.append(delay)
            last_empty_time = None

    mean_delay_sec = sum(delays) / len(delays) if delays else None

    return {
        "num_became_occupied": num_became_occupied,
        "num_became_empty": num_became_empty,
        "num_approach": num_approach,
        "delays": delays,
        "mean_delay_sec": mean_delay_sec,
    }


def save_report(analytics: dict, path: str):
    """Записать report.txt со сводкой аналитики."""
    delays_str = ", ".join(f"{d:.3f}" for d in analytics["delays"]) if analytics["delays"] else "none"
    mean_str = f"{analytics['mean_delay_sec']:.3f}" if analytics["mean_delay_sec"] is not None else "N/A"

    lines = [
        "=== Отчёт о занятости столика в кафе ===",
        "",
        f"Всего событий became_occupied : {analytics['num_became_occupied']}",
        f"Всего событий became_empty    : {analytics['num_became_empty']}",
        f"Всего событий approach        : {analytics['num_approach']}",
        "---",
        f"Задержки approach (сек)       : [{delays_str}]",
        f"Средняя задержка approach (сек): {mean_str}",
        "",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
