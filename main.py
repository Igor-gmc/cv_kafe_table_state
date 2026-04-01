# main.py
# Точка входа: разбор аргументов CLI и оркестровка конвейера.
# Блок 10: полное соединение конвейера.

import argparse
import ctypes
import os
import sys
import time
from pathlib import Path

import cv2

# Включить VT100 escape-коды на Windows (исправляет \r в PowerShell)
if os.name == "nt":
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

from src.config.settings import (
    FRAME_SKIP,
    MOTION_THRESHOLD,
    OUTPUT_EVENTS_CSV,
    OUTPUT_REPORT,
    OUTPUT_TABLE_LOG,
    OUTPUT_TARGET_SIZE_MB,
    REQUIRED_EMPTY_SEC,
    REQUIRED_OCCUPIED_SEC,
    SCREENSHOT_DIR,
    SCREENSHOT_PATTERN,
    TABLE_ZONE,
)
from src.analytics import compute_analytics, save_report
from src.detector import PersonDetector
from src.motion_detector import MotionDetector
from src.event_logger import EventLogger
from src.presence_logic import compute_presence_signal
from src.state_machine import (
    CANDIDATE_EMPTY,
    OCCUPIED_CONFIRMED,
    TableStateMachine,
)
from src.surface_comparator import SurfaceComparator
from src.table_logger import TableStatusLogger
from src.video_io import VideoReader, VideoWriter
from src.visualizer import draw_frame


def parse_args():
    parser = argparse.ArgumentParser(description="Детектор занятости столика в кафе")
    parser.add_argument(
        "--video",
        required=True,
        help="Путь к входному видеофайлу (например: data/video/video1.mp4)",
    )
    return parser.parse_args()


def next_screenshot_path(video_stem: str) -> str:
    """Вернуть следующий доступный путь для скриншота с автоинкрементным порядковым номером."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    seq = 1
    while True:
        name = SCREENSHOT_PATTERN.format(video_stem=video_stem, seq=seq)
        path = os.path.join(SCREENSHOT_DIR, name)
        if not os.path.exists(path):
            return path
        seq += 1


def save_screenshot(frame, table_zone, video_stem: str) -> str:
    """Нарисовать прямоугольник TABLE_ZONE на кадре и сохранить как скриншот. Возвращает путь к файлу."""
    preview = frame.copy()
    x1, y1, x2, y2 = table_zone
    cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 255), 3)
    cv2.putText(preview, "TABLE_ZONE", (x1, y1 - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    path = next_screenshot_path(video_stem)
    cv2.imwrite(path, preview)
    return path


def parse_roi_input(prompt: str) -> tuple[int, int, int, int]:
    """Запросить у пользователя ROI в виде 4 целых чисел: x1 y1 x2 y2."""
    while True:
        raw = input(prompt).strip()
        parts = raw.replace(",", " ").split()
        if len(parts) == 4:
            try:
                x1, y1, x2, y2 = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
                if x2 > x1 and y2 > y1:
                    return x1, y1, x2, y2
                print("  Ошибка: x2 должен быть > x1, а y2 > y1. Попробуйте ещё раз.")
            except ValueError:
                print("  Ошибка: все значения должны быть целыми числами. Попробуйте ещё раз.")
        else:
            print("  Ошибка: введите ровно 4 числа: x1 y1 x2 y2. Попробуйте ещё раз.")


def validate_roi(roi: tuple[int, int, int, int], frame_width: int, frame_height: int, label: str):
    x1, y1, x2, y2 = roi
    if x1 < 0 or y1 < 0 or x2 > frame_width or y2 > frame_height:
        print(f"  ПРЕДУПРЕЖДЕНИЕ: {label} {roi} выходит за границы кадра ({frame_width}x{frame_height})")


def interactive_roi_setup(first_frame, video_stem: str, frame_width: int, frame_height: int):
    """Показать первый кадр, получить координаты ROI от пользователя, сохранить скриншот, подтвердить."""
    # Сохранить первый кадр, чтобы пользователь мог его просмотреть
    first_frame_path = next_screenshot_path(video_stem)
    cv2.imwrite(first_frame_path, first_frame)
    print(f"\nПервый кадр сохранён: {first_frame_path}")
    print(f"Разрешение видео: {frame_width} x {frame_height}")
    print(f"Откройте изображение и определите координаты зон столика.\n")
    print("Формат координат: x1 y1 x2 y2")
    print("  (x1, y1) — левый верхний угол")
    print("  (x2, y2) — правый нижний угол\n")

    while True:
        print("Введите TABLE_ZONE — зона столика и посадочных мест.")
        table_zone = parse_roi_input("  TABLE_ZONE (x1 y1 x2 y2): ")
        validate_roi(table_zone, frame_width, frame_height, "TABLE_ZONE")

        # Сохранить скриншот с жёлтым прямоугольником TABLE_ZONE
        screenshot_path = save_screenshot(first_frame, table_zone, video_stem)
        print(f"\nСкриншот с зоной сохранён: {screenshot_path}")
        print(f"  TABLE_ZONE (жёлтая): {table_zone}")

        confirm = input("\nПодтвердить? (y — начать анализ / n — ввести заново): ").strip().lower()
        if confirm in ("y", "yes"):
            print("\nЗона подтверждена. Запускаем анализ видео...")
            return table_zone
        print("Вводим координаты заново.\n")


def run_pipeline(video_path: str):
    Path("outputs").mkdir(exist_ok=True)
    video_stem = Path(video_path).stem
    output_video = f"outputs/output_{video_stem}.mp4"

    with VideoReader(video_path) as reader:
        fps = reader.fps
        total = reader.total_frames
        frame_width = reader.frame_width
        frame_height = reader.frame_height

        first_frame = reader.read_first_frame()
        if first_frame is None:
            print("Ошибка: не удалось прочитать первый кадр.", file=sys.stderr)
            sys.exit(1)

        table_zone = interactive_roi_setup(
            first_frame, video_stem, frame_width, frame_height
        )

        print(f"\nВидео: {video_path}")
        print(f"FPS: {fps}, Разрешение: {frame_width}x{frame_height}, Кадров: {total}")
        print(f"TABLE_ZONE: {table_zone}")
        print(f"Порог занятости:  {REQUIRED_OCCUPIED_SEC} сек")
        print(f"Порог пустоты:    {REQUIRED_EMPTY_SEC} сек")
        print()

        detector = PersonDetector()
        # Детектор движения запускается на каждом кадре (не зависит от FRAME_SKIP),
        # так как вычитание фона дёшево и требует непрерывного потока кадров для корректной модели фона.
        motion_detector = MotionDetector(table_zone)
        table_logger = TableStatusLogger(OUTPUT_TABLE_LOG, video_path)

        # Определить начальный статус столика по первому кадру
        initial_detections = detector.detect(first_frame)
        initial_presence = compute_presence_signal(initial_detections, table_zone, None)
        if initial_presence == "interacting_person":
            initial_state = OCCUPIED_CONFIRMED
        else:
            from src.state_machine import EMPTY_CONFIRMED
            initial_state = EMPTY_CONFIRMED

        state_machine = TableStateMachine(fps, initial_state=initial_state)

        # Сравнение поверхности столика с эталоном чистого состояния
        surface_comparator = SurfaceComparator(table_zone)
        if initial_state == EMPTY_CONFIRMED:
            surface_comparator.capture_reference(first_frame)

        initial_event = {
            "frame_idx": 0,
            "timestamp_sec": 0.0,
            "event_type": "initial_state",
            "prev_state": "N/A",
            "new_state": initial_state,
        }
        table_logger.log_state_change(initial_event)
        # Сохранить скриншот начального состояния
        state_screen_dir = os.path.join("outputs", "screen_table_state")
        os.makedirs(state_screen_dir, exist_ok=True)
        cv2.imwrite(
            os.path.join(state_screen_dir, f"{video_stem}_f00000_00m00s_{initial_state}.png"),
            first_frame,
        )

        # Рассчитать битрейт для целевого размера файла
        duration_sec = total / fps if fps > 0 else 1
        bitrate_kbps = int(OUTPUT_TARGET_SIZE_MB * 8 * 1024 / duration_sec)
        print(f"Целевой размер: {OUTPUT_TARGET_SIZE_MB} МБ → битрейт: {bitrate_kbps} kbps")

        with EventLogger(OUTPUT_EVENTS_CSV) as logger, \
             VideoWriter(output_video, fps, frame_width, frame_height, bitrate_kbps) as writer:
            logger.log(initial_event)
            start_time = time.time()
            last_detections = []
            prev_detections = None
            for frame_idx, frame in reader:
                timestamp_sec = frame_idx / fps

                if frame_idx % FRAME_SKIP == 0:
                    prev_detections = last_detections if last_detections else None
                    last_detections = detector.detect(frame)
                presence = compute_presence_signal(last_detections, table_zone, prev_detections)

                # Резервный сигнал движения: если YOLO не видит человека,
                # но в зоне взаимодействия есть значимое движение — считаем столик занятым.
                # Покрывает случаи нестандартных поз (наклон над столом, съёмка сверху).
                motion_ratio = motion_detector.update(frame)
                if presence == "no_person" and motion_ratio >= MOTION_THRESHOLD:
                    presence = "interacting_person"

                # Проверка поверхности: если людей нет, но столик грязный — считаем занятым.
                # Работает только когда столик уже был OCCUPIED (кто-то сидел и ушёл),
                # чтобы не ловить случайные изменения освещения/теней в пустом состоянии.
                if (
                    presence != "interacting_person"
                    and state_machine.current_state in (OCCUPIED_CONFIRMED, CANDIDATE_EMPTY)
                    and surface_comparator.is_surface_dirty(frame)
                ):
                    presence = "interacting_person"

                events = state_machine.update(presence, frame_idx, timestamp_sec)

                for e in events:
                    logger.log(e)
                    table_logger.log_state_change(e)
                    # Обновить эталон чистого столика при переходе в EMPTY
                    if e["event_type"] == "became_empty":
                        surface_comparator.capture_reference(frame)
                    # Сохранить кадр при смене статуса
                    ts = e["timestamp_sec"]
                    m, s = int(ts // 60), int(ts % 60)
                    state_screen_name = (
                        f"{video_stem}_f{e['frame_idx']:05d}_{m:02d}m{s:02d}s_{e['new_state']}.png"
                    )
                    state_screen_dir = os.path.join("outputs", "screen_table_state")
                    os.makedirs(state_screen_dir, exist_ok=True)
                    cv2.imwrite(os.path.join(state_screen_dir, state_screen_name), frame)

                annotated = draw_frame(
                    frame, last_detections, table_zone, state_machine.current_state, presence
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

    print(f"\nСобытий записано: {len(all_events)}")
    print(f"  became_occupied: {analytics['num_became_occupied']}")
    print(f"  became_empty:    {analytics['num_became_empty']}")
    print(f"  approach:        {analytics['num_approach']}")
    if analytics["mean_delay_sec"] is not None:
        print(f"  средняя задержка: {analytics['mean_delay_sec']:.3f} сек")
    else:
        print("  средняя задержка: N/A (нет валидных пар пустой→подход)")
    print(f"\nВыходные файлы:")
    print(f"  Видео:   {output_video}")
    print(f"  События: {OUTPUT_EVENTS_CSV}")
    print(f"  Отчёт:   {OUTPUT_REPORT}")


def main():
    args = parse_args()
    video_path = args.video

    if not Path(video_path).exists():
        print(f"Ошибка: видеофайл не найден: {video_path}", file=sys.stderr)
        sys.exit(1)

    run_pipeline(video_path)


if __name__ == "__main__":
    main()
