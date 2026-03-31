# src/analytics.py
# Module 5 — Analytics
# Block 8: compute_analytics and save_report.

import pandas as pd


def compute_analytics(events: pd.DataFrame) -> dict:
    """Find (became_empty, approach) pairs; compute delays.

    Returns dict with counts and mean_delay_sec (None if no valid pairs).
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
    """Write report.txt with analytics summary."""
    delays_str = ", ".join(f"{d:.3f}" for d in analytics["delays"]) if analytics["delays"] else "none"
    mean_str = f"{analytics['mean_delay_sec']:.3f}" if analytics["mean_delay_sec"] is not None else "N/A"

    lines = [
        "=== Cafe Table Occupancy Report ===",
        "",
        f"Total became_occupied events : {analytics['num_became_occupied']}",
        f"Total became_empty events    : {analytics['num_became_empty']}",
        f"Total approach events        : {analytics['num_approach']}",
        "---",
        f"Approach delays (sec)        : [{delays_str}]",
        f"Mean approach delay (sec)    : {mean_str}",
        "",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
