# src/video_io.py
# Модуль 1 — Ввод/вывод видео
# Блок 2: классы VideoReader и VideoWriter.

import subprocess

import cv2
import numpy as np


class VideoReader:
    """Читает кадры видео. Контекстный менеджер, итерируемый объект."""

    def __init__(self, path: str):
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            raise FileNotFoundError(f"Не удалось открыть видео: {path}")

    @property
    def fps(self) -> float:
        return self._cap.get(cv2.CAP_PROP_FPS)

    @property
    def frame_width(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def frame_height(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @property
    def total_frames(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def read_first_frame(self) -> np.ndarray | None:
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self._cap.read()
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        return frame if ret else None

    def __iter__(self):
        frame_idx = 0
        while True:
            ret, frame = self._cap.read()
            if not ret:
                break
            yield frame_idx, frame
            frame_idx += 1

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


def _get_ffmpeg_path() -> str | None:
    """Получить путь к ffmpeg: сначала системный, затем из imageio-ffmpeg."""
    import shutil

    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        return None


class VideoWriter:
    """Записывает кадры видео. Использует ffmpeg для контроля битрейта (H.264),
    с фолбэком на OpenCV (mp4v) если ffmpeg недоступен."""

    def __init__(self, path: str, fps: float, width: int, height: int,
                 bitrate_kbps: int | None = None):
        self._path = path
        self._proc = None
        self._cv_writer = None

        ffmpeg = _get_ffmpeg_path() if bitrate_kbps else None

        if ffmpeg and bitrate_kbps:
            cmd = [
                ffmpeg, "-y",
                "-f", "rawvideo",
                "-pix_fmt", "bgr24",
                "-s", f"{width}x{height}",
                "-r", str(fps),
                "-i", "-",
                "-c:v", "libx264",
                "-b:v", f"{bitrate_kbps}k",
                "-maxrate", f"{int(bitrate_kbps * 1.5)}k",
                "-bufsize", f"{bitrate_kbps * 2}k",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                path,
            ]
            self._proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._cv_writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
            if not self._cv_writer.isOpened():
                raise RuntimeError(f"Не удалось открыть видеозаписывающий модуль: {path}")

    def write(self, frame: np.ndarray):
        if self._proc:
            self._proc.stdin.write(frame.tobytes())
        elif self._cv_writer:
            self._cv_writer.write(frame)

    def release(self):
        if self._proc is not None:
            self._proc.stdin.close()
            self._proc.wait()
            self._proc = None
        if self._cv_writer is not None:
            self._cv_writer.release()
            self._cv_writer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False
