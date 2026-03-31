# kafe_place_table_detect

Cafe table occupancy detector. Detects when a table becomes occupied or vacant using YOLOv8 on video footage.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py --video "data/video/видео 1.mp4"
```

The script will:
1. Save the first frame as a screenshot and display the video resolution
2. Ask you to enter VISUAL_ROI coordinates (x1 y1 x2 y2) — the yellow outer rectangle
3. Ask you to enter INTERACTION_ZONE coordinates (x1 y1 x2 y2) — the green inner rectangle
4. Save a screenshot with both zones drawn for visual confirmation
5. Ask you to confirm (y/n) before starting the analysis

Outputs:
- `outputs/output.mp4` — annotated video
- `outputs/events.csv` — event log with timestamps
- `outputs/report.txt` — analytics summary
- `outputs/screenshot_{video}_{NNN}.png` — saved screenshots (first frame, ROI preview)

## Selected table and ROI

On each run the user enters table coordinates manually after viewing the first frame screenshot. The video resolution is displayed to help determine pixel coordinates.

## Detection logic

- YOLOv8n detects persons on each frame
- Each person is classified by foot-point (bottom-center of bbox) relative to `INTERACTION_ZONE`
- A 4-state machine (`EMPTY_CONFIRMED` → `CANDIDATE_OCCUPIED` → `OCCUPIED_CONFIRMED` → `CANDIDATE_EMPTY` → ...) produces confirmed state transitions
- Events: `became_occupied`, `became_empty`, `approach`
- `approach` fires only on confirmed `EMPTY_CONFIRMED → OCCUPIED_CONFIRMED` transition

## Results

## Limitations

- Single table, hardcoded ROI
- No distinction between guest and staff
- Possible false positives in complex poses or high-traffic aisle
