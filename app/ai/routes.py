import os
from pathlib import Path
from flask import Blueprint, request
from app.auth.permissions import require_jwt, require_roles
from app.auth.service import ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_INSPECTION_OFFICER
from app.storage import storage_service
from app.ai.yolo_detector import yolo_detector
from app.ai.video_processor import process_video_for_violations
from app.workflow.rule_engine import evaluate_rules
from app.violations.service import create_violation
from app.utils.responses import success_response, error_response
from app.config import Config

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/model-status", methods=["GET"])
@require_jwt
def model_status():
    return success_response(
        data={
            "model_name": yolo_detector.model_name,
            "is_mock": yolo_detector.is_mock,
            "weights_path": str(yolo_detector.model_path),
            "weights_exist": yolo_detector.model_path.exists(),
            "confidence_threshold": Config.CONFIDENCE_THRESHOLD
        },
        message="AI Vision model status"
    )


@ai_bp.route("/image-detect", methods=["POST"])
@require_jwt
def detect_image_endpoint():
    user = request.current_user
    image_file = request.files.get("image")
    image_path_str = request.form.get("image_path")
    mine_id = request.form.get("mine_id")
    zone_id = request.form.get("zone_id")
    auto_create_violation = request.form.get("auto_create_violation", "false").lower() in ("true", "1", "yes")

    saved_path = None
    if image_file and image_file.filename != "":
        upload_meta = storage_service.upload(image_file, filename=image_file.filename, subfolder="evidence")
        saved_path = upload_meta["absolute_path"]
    elif image_path_str:
        candidate = Config.UPLOAD_FOLDER / image_path_str.replace("/", os.sep)
        if candidate.exists():
            saved_path = str(candidate)
        elif Path(image_path_str).exists():
            saved_path = image_path_str

    if not saved_path:
        return error_response(code="VALIDATION_ERROR", message="An image file or valid image_path is required", status_code=400)

    # Run inference
    try:
        results = yolo_detector.detect_image(
            image_path=saved_path,
            confidence_threshold=Config.CONFIDENCE_THRESHOLD
        )
    except Exception as e:
        return error_response(code="AI_INFERENCE_ERROR", message=f"Computer vision analysis failed: {str(e)}", status_code=500)

    # Primary workflow bridge: If violations found and auto_create_violation is enabled
    created_violations = []
    if auto_create_violation and results.get("violations_detected", 0) > 0 and mine_id:
        for v in results["violations"]:
            # Evaluate against rule engine
            rule_eval = evaluate_rules({
                "missing_helmet": (v.get("violation_type") == "PPE_MISSING_HELMET"),
                "unauthorized_zone_entry": (v.get("violation_type") == "RESTRICTED_ZONE_BREACH")
            })

            v_doc = create_violation({
                "mine_id": mine_id,
                "zone_id": zone_id,
                "category": "PPE_VIOLATION" if v.get("violation_type") == "PPE_MISSING_HELMET" else "RESTRICTED_AREA",
                "description": f"[AI Detection] {v.get('description')}",
                "severity": v.get("severity", "HIGH"),
                "source": "AI_DETECTION",
                "evidence": [results.get("annotated_image_url")]
            }, user=user)
            created_violations.append(v_doc)

    results["dispatched_violations"] = created_violations
    return success_response(data=results, message="Image analysis completed")


@ai_bp.route("/video-detect", methods=["POST"])
@require_jwt
def detect_video_endpoint():
    video_file = request.files.get("video")
    if not video_file or video_file.filename == "":
        return error_response(code="VALIDATION_ERROR", message="A video file is required", status_code=400)

    upload_meta = storage_service.upload(video_file, filename=video_file.filename, subfolder="evidence")
    video_path = upload_meta["absolute_path"]

    try:
        results = process_video_for_violations(
            video_path=video_path,
            sample_interval_sec=1.5,
            confidence_threshold=Config.CONFIDENCE_THRESHOLD
        )
        return success_response(data=results, message="Video analysis completed successfully")
    except Exception as e:
        return error_response(code="VIDEO_PROCESSING_ERROR", message=f"Video analysis failed: {str(e)}", status_code=500)
