import os
import cv2
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import Config
from app.ai.yolo_detector import yolo_detector

logger = logging.getLogger("coal_governance.video")


def process_video_for_violations(
    video_path: str,
    sample_interval_sec: float = 1.0,
    confidence_threshold: float = 0.45,
    max_frames_to_process: int = 60
) -> Dict[str, Any]:
    """
    Samples frames from video stream/file, analyzes them for PPE or perimeter violations,
    and extracts keyframe evidence for detected violations.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        raise FileNotFoundError(f"Video file not found at {video_path}")

    cap = cv2.VideoCapture(str(v_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video at {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_sec = total_frames / fps if fps > 0 else 0

    frame_step = max(int(fps * sample_interval_sec), 1)
    evidence_dir = Config.UPLOAD_FOLDER / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    frame_index = 0
    processed_count = 0
    violations_found = []
    keyframes = []

    while cap.isOpened() and processed_count < max_frames_to_process:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index % frame_step == 0:
            timestamp_sec = round(frame_index / fps, 2)
            temp_frame_name = f"frame_{v_path.stem}_{frame_index}.jpg"
            temp_frame_path = evidence_dir / temp_frame_name
            cv2.imwrite(str(temp_frame_path), frame)

            try:
                detection_result = yolo_detector.detect_image(
                    image_path=str(temp_frame_path),
                    confidence_threshold=confidence_threshold
                )

                if detection_result.get("violations_detected", 0) > 0:
                    keyframes.append({
                        "timestamp_sec": timestamp_sec,
                        "frame_index": frame_index,
                        "annotated_frame_url": detection_result.get("annotated_image_url"),
                        "violations": detection_result.get("violations", [])
                    })
                    for v in detection_result.get("violations", []):
                        v_entry = dict(v)
                        v_entry["timestamp_sec"] = timestamp_sec
                        v_entry["frame_url"] = detection_result.get("annotated_image_url")
                        violations_found.append(v_entry)
            except Exception as e:
                logger.error(f"Error processing video frame {frame_index}: {e}")

            processed_count += 1

        frame_index += 1

    cap.release()

    return {
        "video_filename": v_path.name,
        "duration_seconds": round(duration_sec, 2),
        "total_video_frames": total_frames,
        "frames_analyzed": processed_count,
        "total_violations": len(violations_found),
        "violations": violations_found,
        "keyframes": keyframes
    }
