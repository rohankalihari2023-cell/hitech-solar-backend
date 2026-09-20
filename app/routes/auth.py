from flask import Blueprint, request, jsonify, g
import bcrypt
from bson import ObjectId
from app import database
from app.utils.jwt_utils import generate_token
from app.middleware.auth import jwt_required

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    identifier = data.get("identifier", "").strip()
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({"success": False, "message": "Email/Employee ID and password are required."}), 400

    if database.users_col is None:
        return jsonify({"success": False, "message": "Database not initialized. Please verify MongoDB connection."}), 503

    user = database.users_col.find_one({
        "$or": [
            {"email": identifier.lower()},
            {"employee_id": identifier.upper()}
        ]
    })

    if not user or not user.get("is_active", True):
        return jsonify({"success": False, "message": "Invalid credentials or account is disabled."}), 401

    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return jsonify({"success": False, "message": "Invalid credentials."}), 401

    token = generate_token(
        user_id=str(user["_id"]),
        employee_id=user["employee_id"],
        role=user["role"],
        email=user["email"],
        name=user["name"]
    )

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "employee_id": user["employee_id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "department": user.get("department", "General"),
            "phone": user.get("phone", "")
        }
    }), 200

@auth_bp.route("/change-password", methods=["POST"])
@jwt_required
def change_password():
    data = request.get_json() or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"success": False, "message": "Current and new password are required."}), 400

    if len(new_password) < 6:
        return jsonify({"success": False, "message": "New password must be at least 6 characters long."}), 400

    user = database.users_col.find_one({"_id": ObjectId(g.current_user["user_id"])})
    if not user or not bcrypt.checkpw(current_password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return jsonify({"success": False, "message": "Current password is incorrect."}), 400

    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    database.users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hashed}}
    )

    return jsonify({"success": True, "message": "Password changed successfully."}), 200

@auth_bp.route("/me", methods=["GET"])
@jwt_required
def get_current_user_profile():
    user = database.users_col.find_one({"_id": ObjectId(g.current_user["user_id"])}, {"password_hash": 0})
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    
    user["id"] = str(user.pop("_id"))
    return jsonify({"success": True, "user": user}), 200
