from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from app import database
from app.middleware.auth import jwt_required, admin_required

leave_bp = Blueprint("leave", __name__)

@leave_bp.route("", methods=["POST"])
@jwt_required
def apply_leave():
    user = g.current_user
    data = request.get_json() or {}
    start_date = data.get("start_date", "").strip()
    end_date = data.get("end_date", "").strip()
    leave_type = data.get("leave_type", "CASUAL").upper()
    reason = data.get("reason", "").strip()

    if not start_date or not end_date or not reason:
        return jsonify({"success": False, "message": "Start date, end date, and reason are required."}), 400

    doc = {
        "employee_id": user["employee_id"],
        "employee_name": user["name"],
        "start_date": start_date,
        "end_date": end_date,
        "leave_type": leave_type,
        "reason": reason,
        "status": "PENDING",
        "rejection_reason": None,
        "reviewed_by": None,
        "created_at": datetime.now(timezone.utc)
    }

    res = database.leave_requests_col.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    del doc["_id"]
    return jsonify({"success": True, "message": "Leave application submitted successfully.", "leave": doc}), 201

@leave_bp.route("/my", methods=["GET"])
@jwt_required
def get_my_leaves():
    user = g.current_user
    leaves = list(database.leave_requests_col.find({"employee_id": user["employee_id"]}).sort("created_at", -1))
    for l in leaves:
        l["id"] = str(l.pop("_id"))
    return jsonify({"success": True, "leaves": leaves}), 200

@leave_bp.route("/all", methods=["GET"])
@admin_required
def get_all_leaves():
    status = request.args.get("status")
    query = {}
    if status:
        query["status"] = status.upper()

    leaves = list(database.leave_requests_col.find(query).sort("created_at", -1))
    for l in leaves:
        l["id"] = str(l.pop("_id"))
    return jsonify({"success": True, "leaves": leaves}), 200

@leave_bp.route("/<leave_id>/approve", methods=["PUT"])
@admin_required
def approve_leave(leave_id):
    query = {"_id": ObjectId(leave_id)} if ObjectId.is_valid(leave_id) else {"_id": leave_id}
    res = database.leave_requests_col.update_one(
        query,
        {"$set": {
            "status": "APPROVED",
            "reviewed_by": g.current_user["name"],
            "reviewed_at": datetime.now(timezone.utc)
        }}
    )
    if res.matched_count == 0:
        return jsonify({"success": False, "message": "Leave request not found."}), 404
    return jsonify({"success": True, "message": "Leave request approved."}), 200

@leave_bp.route("/<leave_id>/reject", methods=["PUT"])
@admin_required
def reject_leave(leave_id):
    data = request.get_json() or {}
    reason = data.get("reason", "Not approved by administrator")
    query = {"_id": ObjectId(leave_id)} if ObjectId.is_valid(leave_id) else {"_id": leave_id}
    res = database.leave_requests_col.update_one(
        query,
        {"$set": {
            "status": "REJECTED",
            "rejection_reason": reason,
            "reviewed_by": g.current_user["name"],
            "reviewed_at": datetime.now(timezone.utc)
        }}
    )
    if res.matched_count == 0:
        return jsonify({"success": False, "message": "Leave request not found."}), 404
    return jsonify({"success": True, "message": "Leave request rejected."}), 200
