from flask import Blueprint, request, jsonify
from app import database
from app.middleware.auth import admin_required, jwt_required
from app.services.attendance_service import get_company_settings

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("", methods=["GET"])
@jwt_required
def fetch_settings():
    settings = get_company_settings()
    if "_id" in settings:
        settings["_id"] = str(settings["_id"])
    return jsonify({"success": True, "settings": settings}), 200

@settings_bp.route("", methods=["PUT"])
@admin_required
def update_settings():
    data = request.get_json() or {}
    # Store the complete document on first save so it satisfies the collection schema.
    update_data = {
        "key": "default_rules",
        "office_latitude": 28.6139,
        "office_longitude": 77.2090,
        "office_radius": 150.0,
        "office_start_time": "09:30",
        "office_end_time": "18:30",
        "late_after": "09:45",
        "minimum_working_hours": 8.0,
        "half_day_hours": 4.0,
    }
    existing = database.company_settings_col.find_one({"key": "default_rules"})
    if existing:
        update_data.update({key: existing[key] for key in update_data if key in existing})

    numeric_keys = ["office_latitude", "office_longitude", "office_radius", "minimum_working_hours", "half_day_hours"]
    string_keys = ["office_start_time", "office_end_time", "late_after"]

    for k in numeric_keys:
        if k in data:
            try:
                update_data[k] = float(data[k])
            except (ValueError, TypeError):
                return jsonify({"success": False, "message": f"Invalid numeric value for {k}"}), 400

    for k in string_keys:
        if k in data:
            update_data[k] = str(data[k]).strip()

    database.company_settings_col.update_one(
        {"key": "default_rules"},
        {"$set": update_data},
        upsert=True
    )

    updated = get_company_settings()
    if "_id" in updated:
        updated["_id"] = str(updated["_id"])

    return jsonify({
        "success": True,
        "message": "Company attendance rules updated successfully.",
        "settings": updated
    }), 200
