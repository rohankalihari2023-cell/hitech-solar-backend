import os
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g, send_from_directory
from werkzeug.utils import secure_filename
from app import database
from app.config import Config
from app.middleware.auth import jwt_required, admin_required
from app.services.geofence_service import verify_geofence
from app.services.attendance_service import (
    get_company_settings,
    determine_status_on_checkin,
    calculate_working_hours,
    get_current_time_data
)
from app.utils.validators import allowed_file

attendance_bp = Blueprint("attendance", __name__)

@attendance_bp.route("/uploads/<path:filename>", methods=["GET"])
def get_uploaded_image(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

@attendance_bp.route("/check-in", methods=["POST"])
@jwt_required
def check_in():
    user = g.current_user
    today_str, current_time_str = get_current_time_data()

    # Anti-Proxy: One check-in per day
    existing = database.attendance_col.find_one({"employee_id": user["employee_id"], "date": today_str})
    if existing and existing.get("check_in_time"):
        return jsonify({"success": False, "message": "Attendance already marked for today."}), 400

    lat = request.form.get("latitude")
    lon = request.form.get("longitude")
    device_info = request.form.get("device_info", "Android Device")

    if not lat or not lon:
        return jsonify({"success": False, "message": "GPS coordinates are required."}), 400

    try:
        f_lat = float(lat)
        f_lon = float(lon)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid GPS coordinates format."}), 400

    # Fetch user to check if Field Worker
    user_doc = database.users_col.find_one({"employee_id": user["employee_id"]})
    is_field_worker = user_doc.get("is_field_worker", False) if user_doc else False

    settings = get_company_settings()
    office_lat = float(settings.get("office_latitude", 28.6139))
    office_lon = float(settings.get("office_longitude", 77.2090))
    office_radius = float(settings.get("office_radius", 150.0))

    is_inside, distance = verify_geofence(f_lat, f_lon, office_lat, office_lon, office_radius)

    # If NOT a field worker, enforce strict office geofence
    if not is_field_worker and not is_inside:
        return jsonify({
            "success": False,
            "message": f"Outside office area. Distance: {distance}m (Allowed: {office_radius}m)."
        }), 403

    # Attendance Selfie Verification
    if "photo" not in request.files:
        return jsonify({"success": False, "message": "Attendance selfie photo is required."}), 400
    
    file = request.files["photo"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Valid image file (.jpg, .png, .webp) is required."}), 400

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"in_{user['employee_id']}_{today_str}_{uuid.uuid4().hex[:8]}.{ext}"
    saved_path = os.path.join(Config.UPLOAD_FOLDER, secure_filename(filename))
    file.save(saved_path)

    status = determine_status_on_checkin(current_time_str, settings)
    late_status = "LATE" if status == "LATE" else "NO"

    record = {
        "employee_id": user["employee_id"],
        "employee_name": user["name"],
        "date": today_str,
        "check_in_time": current_time_str,
        "check_out_time": None,
        "working_hours": 0.0,
        "check_in_latitude": f_lat,
        "check_in_longitude": f_lon,
        "check_out_latitude": None,
        "check_out_longitude": None,
        "check_in_photo": f"/api/attendance/uploads/{filename}",
        "check_out_photo": None,
        "status": status,
        "late_status": late_status,
        "is_field_worker": is_field_worker,
        "distance_meters": distance,
        "device_info": device_info,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    database.attendance_col.update_one(
        {"employee_id": user["employee_id"], "date": today_str},
        {"$set": record},
        upsert=True
    )

    mode_label = "Field Worker" if is_field_worker else "Office"
    return jsonify({
        "success": True,
        "message": f"Check-in successful ({mode_label})! Time: {current_time_str}",
        "attendance": record
    }), 201

@attendance_bp.route("/check-out", methods=["POST"])
@jwt_required
def check_out():
    user = g.current_user
    today_str, current_time_str = get_current_time_data()

    existing = database.attendance_col.find_one({"employee_id": user["employee_id"], "date": today_str})
    if not existing or not existing.get("check_in_time"):
        return jsonify({"success": False, "message": "Cannot check-out without checking in first."}), 400

    if existing.get("check_out_time"):
        return jsonify({"success": False, "message": "Check-out already completed for today."}), 400

    lat = request.form.get("latitude")
    lon = request.form.get("longitude")
    if not lat or not lon:
        return jsonify({"success": False, "message": "GPS coordinates are required."}), 400

    try:
        f_lat = float(lat)
        f_lon = float(lon)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid GPS coordinates format."}), 400

    user_doc = database.users_col.find_one({"employee_id": user["employee_id"]})
    is_field_worker = user_doc.get("is_field_worker", False) if user_doc else False

    settings = get_company_settings()
    office_lat = float(settings.get("office_latitude", 28.6139))
    office_lon = float(settings.get("office_longitude", 77.2090))
    office_radius = float(settings.get("office_radius", 150.0))

    is_inside, distance = verify_geofence(f_lat, f_lon, office_lat, office_lon, office_radius)
    if not is_field_worker and not is_inside:
        return jsonify({
            "success": False,
            "message": f"Outside office area for check-out. Distance: {distance}m"
        }), 403

    photo_url = None
    if "photo" in request.files:
        file = request.files["photo"]
        if file.filename != "" and allowed_file(file.filename):
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            ext = file.filename.rsplit(".", 1)[1].lower()
            filename = f"out_{user['employee_id']}_{today_str}_{uuid.uuid4().hex[:8]}.{ext}"
            file.save(os.path.join(Config.UPLOAD_FOLDER, secure_filename(filename)))
            photo_url = f"/api/attendance/uploads/{filename}"

    hours = calculate_working_hours(existing["check_in_time"], current_time_str)
    status = existing.get("status", "PRESENT")
    half_day_limit = float(settings.get("half_day_hours", 4.0))
    if hours < half_day_limit:
        status = "HALF_DAY"

    update_doc = {
        "check_out_time": current_time_str,
        "check_out_latitude": f_lat,
        "check_out_longitude": f_lon,
        "check_out_photo": photo_url or existing.get("check_out_photo"),
        "working_hours": hours,
        "status": status,
        "updated_at": datetime.now(timezone.utc)
    }

    database.attendance_col.update_one({"_id": existing["_id"]}, {"$set": update_doc})
    existing.update(update_doc)
    existing["id"] = str(existing.pop("_id"))

    return jsonify({
        "success": True,
        "message": f"Check-out completed! Hours: {hours} hrs",
        "attendance": existing
    }), 200

@attendance_bp.route("/today", methods=["GET"])
@jwt_required
def get_today_attendance():
    user = g.current_user
    today_str, _ = get_current_time_data()
    record = database.attendance_col.find_one({"employee_id": user["employee_id"], "date": today_str})
    if record:
        record["id"] = str(record.pop("_id"))
    return jsonify({"success": True, "attendance": record}), 200

@attendance_bp.route("/history", methods=["GET"])
@jwt_required
def get_attendance_history():
    user = g.current_user
    emp_id = request.args.get("employee_id")
    target_id = emp_id.upper() if (user["role"] == "ADMIN" and emp_id) else user["employee_id"]
    month = request.args.get("month")
    query = {"employee_id": target_id}
    if month:
        query["date"] = {"$regex": f"^{month}"}
    records = list(database.attendance_col.find(query).sort("date", -1).limit(60))
    for r in records:
        r["id"] = str(r.pop("_id"))
    return jsonify({"success": True, "records": records}), 200

@attendance_bp.route("/report", methods=["GET"])
@admin_required
def get_attendance_report_json():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    emp_id = request.args.get("employee_id")
    status = request.args.get("status")
    query = {}
    if emp_id:
        query["employee_id"] = emp_id.upper()
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    if status:
        query["status"] = status.upper()
    records = list(database.attendance_col.find(query).sort("date", -1))
    for r in records:
        r["id"] = str(r.pop("_id"))
    return jsonify({"success": True, "records": records}), 200
