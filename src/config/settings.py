# config/settings.py
# Single source of truth for all tunable constants.
# Block 3 — Config & ROI

# --- Model ---
YOLO_MODEL = "yolov8n.pt"
CONF_THRESHOLD = 0.4
YOLO_IMGSZ = 640  # resize frame to this for YOLO inference (speeds up CPU)

# --- Frame skip ---
# Process every N-th frame with YOLO; intermediate frames reuse last detection
FRAME_SKIP = 10

# --- State machine thresholds (seconds) ---
# Converted to frames at runtime: ceil(SEC * fps)
REQUIRED_OCCUPIED_SEC = 1.0
REQUIRED_EMPTY_SEC = 1.5

# --- Table ROI ---
# Calibrate these against the actual video frame (Block 11).
# Use cv2.imwrite on frame 0, open in an image viewer, read pixel coords.
#
# visual_roi: rectangle drawn on video; also used for transit overlap test
# Format: (x1, y1, x2, y2)
# Video: "видео 1.mp4", 2560x1440, 20 FPS
# Selected table: center white table between dark booth dividers
VISUAL_ROI = (1350, 124, 1795, 306)

# interaction_zone: inner zone; foot-point (bottom-center of bbox) must be
# inside this zone for a person to be classified as "interacting"
INTERACTION_ZONE = (1280, 60, 1850, 350)

# --- Output paths ---
OUTPUT_VIDEO = "outputs/output.mp4"
OUTPUT_EVENTS_CSV = "outputs/events.csv"
OUTPUT_REPORT = "outputs/report.txt"
OUTPUT_TABLE_LOG = "outputs/table_status.log"

# --- Screenshot naming ---
# Pattern: outputs/screenshot_{video_stem}_{seq:03d}.png
# {video_stem} = video filename without extension
# {seq} = auto-incremented sequence number (001, 002, ...)
SCREENSHOT_DIR = "outputs"
SCREENSHOT_PATTERN = "screenshot_{video_stem}_{seq:03d}.png"
