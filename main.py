# main.py
# Entry point: CLI argument parsing and pipeline orchestration.
# Block 10: full pipeline wiring.

import argparse
import ctypes
import os
import sys
import time
from pathlib import Path

import cv2

# Enable VT100 escape codes on Windows (fixes \r in PowerShell)
if os.name == "nt":
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

from src.config.settings import (
    FRAME_SKIP,
    INTERACTION_ZONE,
    OUTPUT_EVENTS_CSV,
    OUTPUT_REPORT,
    OUTPUT_TABLE_LOG,
    OUTPUT_VIDEO,
    REQUIRED_EMPTY_SEC,
    REQUIRED_OCCUPIED_SEC,
    SCREENSHOT_DIR,
    SCREENSHOT_PATTERN,
    VISUAL_ROI,
)
from src.analytics import compute_analytics, save_report
from src.detector import PersonDetector
from src.event_logger import EventLogger
from src.presence_logic import compute_presence_signal
from src.state_machine import TableStateMachine
from src.table_logger import TableStatusLogger
from src.video_io import VideoReader, VideoWriter
from src.visualizer import draw_frame


def parse_args():
    parser = argparse.ArgumentParser(description="Cafe table occupancy detector")
    parser.add_argument(
        "--video",
        required=True,
        help="Path to input video file (e.g. data/video/video1.mp4)",
    )
    return parser.parse_args()


def next_screenshot_path(video_stem: str) -> str:
    """Return the next available screenshot path with auto-incremented sequence number."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    seq = 1
    while True:
        name = SCREENSHOT_PATTERN.format(video_stem=video_stem, seq=seq)
        path = os.path.join(SCREENSHOT_DIR, name)
        if not os.path.exists(path):
            return path
        seq += 1


def save_screenshot(frame, visual_roi, interaction_zone, video_stem: str) -> str:
    """Draw ROI rectangles on frame and save as screenshot. Returns saved path."""
    preview = frame.copy()
    x1, y1, x2, y2 = visual_roi
    cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 255), 3)
    cv2.putText(preview, "VISUAL_ROI", (x1, y1 - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    ix1, iy1, ix2, iy2 = interaction_zone
    cv2.rectangle(preview, (ix1, iy1), (ix2, iy2), (0, 200, 0), 3)
    cv2.putText(preview, "INTERACTION_ZONE", (ix1, iy1 - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)
    path = next_screenshot_path(video_stem)
    cv2.imwrite(path, preview)
    return path


def parse_roi_input(prompt: str) -> tuple[int, int, int, int]:
    """Ask user to input ROI as 4 integers: x1 y1 x2 y2."""
    while True:
        raw = input(prompt).strip()
        parts = raw.replace(",", " ").split()
        if len(parts) == 4:
            try:
                x1, y1, x2, y2 = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
                if x2 > x1 and y2 > y1:
                    return x1, y1, x2, y2
                print("  Error: x2 must be > x1 and y2 must be > y1. Try again.")
            except ValueError:
                print("  Error: all values must be integers. Try again.")
        else:
            print("  Error: enter exactly 4 numbers: x1 y1 x2 y2. Try again.")


def validate_roi(roi: tuple[int, int, int, int], frame_width: int, frame_height: int, label: str):
    x1, y1, x2, y2 = roi
    if x1 < 0 or y1 < 0 or x2 > frame_width or y2 > frame_height:
        print(f"  WARNING: {label} {roi} is outside frame bounds ({frame_width}x{frame_height})")


def interactive_roi_setup(first_frame, video_stem: str, frame_width: int, frame_height: int):
    """Show first frame, get ROI coordinates from user input, save screenshot, confirm."""
    # Save first frame so user can view it
    first_frame_path = next_screenshot_path(video_stem)
    cv2.imwrite(first_frame_path, first_frame)
    print(f"\nПервый кадр сохранён: {first_frame_path}")
    print(f"Разрешение видео: {frame_width} x {frame_height}")
    print(f"Откройте изображение и определите координаты зон столика.\n")
    print("Формат координат: x1 y1 x2 y2")
    print("  (x1, y1) — левый верхний угол")
    print("  (x2, y2) — правый нижний угол\n")

    while True:
        print("Введите VISUAL_ROI (жёлтая рамка) — поверхность столика.")
        visual_roi = parse_roi_input("  VISUAL_ROI (x1 y1 x2 y2): ")
        validate_roi(visual_roi, frame_width, frame_height, "VISUAL_ROI")

        print("\nВведите INTERACTION_ZONE (зелёная рамка) — зона взаимодействия вокруг столика.")
        interaction_zone = parse_roi_input("  INTERACTION_ZONE (x1 y1 x2 y2): ")
        validate_roi(interaction_zone, frame_width, frame_height, "INTERACTION_ZONE")

        # Save screenshot with both rectangles
        screenshot_path = save_screenshot(first_frame, visual_roi, interaction_zone, video_stem)
        print(f"\nСкриншот с зонами сохранён: {screenshot_path}")
        print(f"  VISUAL_ROI (жёлтая):       {visual_roi}")
        print(f"  INTERACTION_ZONE (зелёная): {interaction_zone}")

        confirm = input("\nПодтвердить? (y — начать анализ / n — ввести заново): ").strip().lower()
        if confirm in ("y", "yes"):
            print("\nЗоны подтверждены. Запускаем анализ видео...")
            return visual_roi, interaction_zone
        print("Вводим координаты заново.\n")


def run_pipeline(video_path: str):
    Path("outputs").mkdir(exist_ok=True)
    video_stem = Path(video_path).stem

    with VideoReader(video_path) as reader:
        fps = reader.fps
        total = reader.total_frames
        frame_width = reader.frame_width
        frame_height = reader.frame_height

        first_frame = reader.read_first_frame()
        if first_frame is None:
            print("Error: cannot read first frame.", file=sys.stderr)
            sys.exit(1)

        visual_roi, interaction_zone = interactive_roi_setup(
            first_frame, video_stem, frame_width, frame_height
        )

        print(f"\nVideo: {video_path}")
        print(f"FPS: {fps}, Resolution: {frame_width}x{frame_height}, Frames: {total}")
        print(f"Visual ROI:       {visual_roi}")
        print(f"Interaction Zone: {interaction_zone}")
        print(f"Occupied threshold: {REQUIRED_OCCUPIED_SEC} sec")
        print(f"Empty threshold:    {REQUIRED_EMPTY_SEC} sec")
        print()

        detector = PersonDetector()
        state_machine = TableStateMachine(fps)
        table_logger = TableStatusLogger(OUTPUT_TABLE_LOG, video_path)

        with EventLogger(OUTPUT_EVENTS_CSV) as logger, \
             VideoWriter(OUTPUT_VIDEO, fps, frame_width, frame_height) as writer:
            start_time = time.time()
            last_detections = []
            for frame_idx, frame in reader:
                timestamp_sec = frame_idx / fps

                if frame_idx % FRAME_SKIP == 0:
                    last_detections = detector.detect(frame)
                presence = compute_presence_signal(last_detections, visual_roi, interaction_zone)
                events = state_machine.update(presence, frame_idx, timestamp_sec)

                for e in events:
                    logger.log(e)
                    table_logger.log_state_change(e)

                annotated = draw_frame(
                    frame, last_detections, visual_roi, state_machine.current_state, presence
                )
                writer.write(annotated)

                if frame_idx % 10 == 0:
                    pct = frame_idx / total * 100 if total > 0 else 0
                    elapsed = time.time() - start_time
                    if frame_idx > 0:
                        eta = elapsed / frame_idx * (total - frame_idx)
                        eta_str = f"{int(eta // 60)}:{int(eta % 60):02d}"
                    else:
                        eta_str = "--:--"
                    sys.stdout.write(f"\033[2K\r  {pct:5.1f}% {frame_idx}/{total} ETA:{eta_str}")
                    sys.stdout.flush()

            all_events = logger.get_dataframe()

    print()

    analytics = compute_analytics(all_events)
    save_report(analytics, OUTPUT_REPORT)
    table_logger.log_summary(analytics)

    print(f"\nEvents logged: {len(all_events)}")
    print(f"  became_occupied: {analytics['num_became_occupied']}")
    print(f"  became_empty:    {analytics['num_became_empty']}")
    print(f"  approach:        {analytics['num_approach']}")
    if analytics["mean_delay_sec"] is not None:
        print(f"  mean delay:      {analytics['mean_delay_sec']:.3f} sec")
    else:
        print("  mean delay:      N/A (no valid empty→approach pairs)")
    print(f"\nOutputs:")
    print(f"  Video:  {OUTPUT_VIDEO}")
    print(f"  Events: {OUTPUT_EVENTS_CSV}")
    print(f"  Report: {OUTPUT_REPORT}")


def main():
    args = parse_args()
    video_path = args.video

    if not Path(video_path).exists():
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    run_pipeline(video_path)


if __name__ == "__main__":
    main()
