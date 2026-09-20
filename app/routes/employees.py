from flask import Blueprint, request, jsonify
from bson import ObjectId
import bcrypt
from datetime import datetime, timezone
from app import database
from app.middleware.auth import admin_required
from app.utils.validators import is_valid_email

employees_bp = Blueprint("employees", __name__)

@employees_bp.route("", methods=["GET"])
@admin_required
def list_employees():
    query = {}
    search = request.args.get("search", "").strip()
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"employee_id": {"$regex": search, "$options": "i"}}
        ]
        
    users = list(database.users_col.find(query, {"password_hash": 0}).sort("name", 1))
    for u in users:
        u["id"] = str(u.pop("_id"))
        
    return jsonify({"success": True, "employees": users}), 200

@employees_bp.route("", methods=["POST"])
@admin_required
def create_employee():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    employee_id = data.get("employee_id", "").strip().upper()
    password = data.get("password", "")
    role = data.get("role", "EMPLOYEE").upper()
    department = data.get("department", "General").strip()
    phone = data.get("phone", "").strip()

    if not name or not email or not employee_id or not password:
        return jsonify({"success": False, "message": "Name, email, employee ID, and password are required."}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Invalid email address format."}), 400

    if role not in ["ADMIN", "EMPLOYEE"]:
        return jsonify({"success": False, "message": "Role must be ADMIN or EMPLOYEE."}), 400

    # Duplicate check
    if database.users_col.find_one({"$or": [{"email": email}, {"employee_id": employee_id}]}):
        return jsonify({"success": False, "message": "Employee with this email or ID already exists."}), 409

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    doc = {
        "name": name,
        "email": email,
        "employee_id": employee_id,
        "password_hash": hashed_pw,
        "role": role,
        "department": department,
        "phone": phone,`n        "is_field_worker": data.get("is_field_worker", False),
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    
    result = database.users_col.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    del doc["password_hash"]
    del doc["_id"]

    return jsonify({"success": True, "message": "Employee registered successfully.", "employee": doc}), 201

@employees_bp.route("/<emp_id>", methods=["GET"])
@admin_required
def get_employee(emp_id):
    query = {"_id": ObjectId(emp_id)} if ObjectId.is_valid(emp_id) else {"employee_id": emp_id.upper()}
    user = database.users_col.find_one(query, {"password_hash": 0})

    if not user:
        return jsonify({"success": False, "message": "Employee not found."}), 404

    user["id"] = str(user.pop("_id"))
    return jsonify({"success": True, "employee": user}), 200

@employees_bp.route("/<emp_id>", methods=["PUT"])
@admin_required
def update_employee(emp_id):
    data = request.get_json() or {}
    update_fields = {}
    
    for f in ["name", "department", "phone", "role", "is_active", "is_field_worker"]:
        if f in data:
            update_fields[f] = data[f]

    if "role" in update_fields and update_fields["role"] not in ["ADMIN", "EMPLOYEE"]:
        return jsonify({"success": False, "message": "Role must be ADMIN or EMPLOYEE."}), 400

    query = {"_id": ObjectId(emp_id)} if ObjectId.is_valid(emp_id) else {"employee_id": emp_id.upper()}
    res = database.users_col.update_one(query, {"$set": update_fields})
    if res.matched_count == 0:
        return jsonify({"success": False, "message": "Employee not found."}), 404

    return jsonify({"success": True, "message": "Employee updated successfully."}), 200

@employees_bp.route("/<emp_id>", methods=["DELETE"])
@admin_required
def disable_employee(emp_id):
    query = {"_id": ObjectId(emp_id)} if ObjectId.is_valid(emp_id) else {"employee_id": emp_id.upper()}
    res = database.users_col.update_one(query, {"$set": {"is_active": False}})
    if res.matched_count == 0:
        return jsonify({"success": False, "message": "Employee not found."}), 404

    return jsonify({"success": True, "message": "Employee disabled successfully."}), 200

@employees_bp.route("/<emp_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(emp_id):
    data = request.get_json() or {}
    new_password = data.get("password", "Welcome@123")
    if len(new_password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400

    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    query = {"_id": ObjectId(emp_id)} if ObjectId.is_valid(emp_id) else {"employee_id": emp_id.upper()}
    res = database.users_col.update_one(query, {"$set": {"password_hash": hashed}})
    
    if res.matched_count == 0:
        return jsonify({"success": False, "message": "Employee not found."}), 404

    return jsonify({"success": True, "message": f"Password reset successfully to '{new_password}'."}), 200

