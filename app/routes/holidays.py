from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from datetime import datetime, timezone
from app import database
from app.middleware.auth import admin_required, jwt_required

holidays_bp = Blueprint("holidays", __name__)

@holidays_bp.route("", methods=["GET"])
@jwt_required
def get_holidays():
    if database.holidays_col is None:
        return jsonify({"success": False, "message": "Database not initialized"}), 503

    holidays = list(database.holidays_col.find({}).sort("date", 1))
    for h in holidays:
        h["id"] = str(h.pop("_id"))
    return jsonify({"success": True, "holidays": holidays}), 200

@holidays_bp.route("", methods=["POST"])
@admin_required
def create_holiday():
    data = request.get_json() or {}
    date_str = data.get("date", "").strip()
    name = data.get("name", "").strip()
    reason = data.get("reason", "").strip()

    if not date_str or not name:
        return jsonify({"success": False, "message": "Holiday date and name are required."}), 400

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."}), 400

    doc = {
        "date": date_str,
        "name": name,
        "reason": reason if reason else name,
        "created_by": g.current_user.get("name", "Admin"),
        "created_at": datetime.now(timezone.utc)
    }

    database.holidays_col.update_one(
        {"date": date_str},
        {"$set": doc},
        upsert=True
    )

    saved = database.holidays_col.find_one({"date": date_str})
    saved["id"] = str(saved.pop("_id"))
    return jsonify({
        "success": True,
        "message": f"Holiday '{name}' reserved for {date_str}.",
        "holiday": saved
    }), 201

@holidays_bp.route("/<holiday_id>", methods=["DELETE"])
@admin_required
def delete_holiday(holiday_id):
    if database.holidays_col is None:
        return jsonify({"success": False, "message": "Database not initialized"}), 503

    query = {"_id": ObjectId(holiday_id)} if ObjectId.is_valid(holiday_id) else {"date": holiday_id}
    res = database.holidays_col.delete_one(query)
    if res.deleted_count == 0:
        return jsonify({"success": False, "message": "Holiday not found."}), 404
    return jsonify({"success": True, "message": "Holiday removed successfully."}), 200
