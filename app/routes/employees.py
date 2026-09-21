from flask import Blueprint, request, jsonify, g
from bson import ObjectId
import bcrypt
from datetime import datetime, timezone
from app import database
from app.middleware.auth import admin_required
from app.utils.validators import is_valid_email

employees_bp = Blueprint("employees", __name__)


def _database_unavailable_response():
    """Return a useful response instead of an AttributeError when MongoDB is down."""
    return jsonify({
        "success": False,
        "message": "Database is unavailable. Check the MongoDB connection and try again."
    }), 503

@employees_bp.route("", methods=["GET"])
@admin_required
def list_employees():
    if database.users_col is None:
        return _database_unavailable_response()
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
    if database.users_col is None:
        return _database_unavailable_response()
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
        "phone": phone,
        "is_field_worker": data.get("is_field_worker", False),
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    
    try:
        result = database.users_col.insert_one(doc)
    except Exception as exc:
        # The unique index is the final authority when two requests arrive together.
        if getattr(exc, "code", None) == 11000:
            return jsonify({"success": False, "message": "Employee with this email or ID already exists."}), 409
        raise
    doc["id"] = str(result.inserted_id)
    del doc["password_hash"]
    del doc["_id"]

    return jsonify({"success": True, "message": "Employee registered successfully.", "employee": doc}), 201

@employees_bp.route("/<emp_id>", methods=["GET"])
@admin_required
def get_employee(emp_id):
    if database.users_col is None:
        return _database_unavailable_response()
    query = {"_id": ObjectId(emp_id)} if ObjectId.is_valid(emp_id) else {"employee_id": emp_id.upper()}
    user = database.users_col.find_one(query, {"password_hash": 0})

    if not user:
        return jsonify({"success": False, "message": "Employee not found."}), 404

    user["id"] = str(user.pop("_id"))
    return jsonify({"success": True, "employee": user}), 200

@employees_bp.route("/<emp_id>", methods=["PUT"])
@admin_required
def update_employee(emp_id):
    if database.users_col is None:
        return _database_unavailable_response()
    data = request.get_json() or {}
    query = {"_id": ObjectId(emp_id)} if ObjectId.is_valid(emp_id) else {"employee_id": emp_id.upper()}
    current_user = database.users_col.find_one(query)
    if not current_user:
        return jsonify({"success": False, "message": "Employee not found."}), 404

    old_emp_id = current_user.get("employee_id")
    update_fields = {}

    # 1. Update Name
    if "name" in data and str(data["name"]).strip():
        new_name = str(data["name"]).strip()
        update_fields["name"] = new_name
        if database.attendance_col is not None:
            database.attendance_col.update_many({"employee_id": old_emp_id}, {"$set": {"employee_name": new_name}})

    # 2. Update Department, phone, role, is_active, is_field_worker
    for f in ["department", "phone", "role", "is_active", "is_field_worker"]:
        if f in data:
            update_fields[f] = data[f]

    if "role" in update_fields and update_fields["role"] not in ["ADMIN", "EMPLOYEE"]:
        return jsonify({"success": False, "message": "Role must be ADMIN or EMPLOYEE."}), 400

    # 3. Update / Reset Password
    if "password" in data and data["password"] and len(str(data["password"]).strip()) > 0:
        new_pw = str(data["password"]).strip()
        if len(new_pw) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400
        update_fields["password_hash"] = bcrypt.hashpw(new_pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # 4. Update Employee ID (with uniqueness check & cascading)
    new_emp_id = (data.get("new_employee_id") or data.get("employee_id") or "").strip().upper()
    if new_emp_id and new_emp_id != old_emp_id:
        existing = database.users_col.find_one({"employee_id": new_emp_id})
        if existing:
            return jsonify({"success": False, "message": f"Employee ID '{new_emp_id}' is already in use."}), 409
        update_fields["employee_id"] = new_emp_id
        if database.attendance_col is not None:
            database.attendance_col.update_many({"employee_id": old_emp_id}, {"$set": {"employee_id": new_emp_id}})
        if database.leave_requests_col is not None:
            database.leave_requests_col.update_many({"employee_id": old_emp_id}, {"$set": {"employee_id": new_emp_id}})

    if not update_fields:
        return jsonify({"success": False, "message": "No fields provided to update."}), 400

    database.users_col.update_one({"_id": current_user["_id"]}, {"$set": update_fields})
    return jsonify({"success": True, "message": "Employee updated successfully.", "updated_fields": list(update_fields.keys())}), 200

@employees_bp.route("/<emp_id>", methods=["DELETE"])
@admin_required
def delete_employee(emp_id):
    if database.users_col is None:
        return _database_unavailable_response()

    query = {"_id": ObjectId(emp_id)} if ObjectId.is_valid(emp_id) else {"employee_id": emp_id.upper()}
    employee = database.users_col.find_one(query, {"employee_id": 1, "role": 1})
    if not employee:
        return jsonify({"success": False, "message": "Employee not found."}), 404

    if str(employee["_id"]) == g.current_user["user_id"]:
        return jsonify({"success": False, "message": "You cannot delete your own administrator account."}), 400

    # Never permit the last administrator account to be deleted.
    if employee.get("role") == "ADMIN" and database.users_col.count_documents({"role": "ADMIN", "is_active": True}) <= 1:
        return jsonify({"success": False, "message": "At least one active administrator account must remain."}), 400

    employee_id = employee["employee_id"]
    database.users_col.delete_one({"_id": employee["_id"]})
    # These records only belong to this employee, so removing them keeps the database consistent.
    if database.attendance_col is not None:
        database.attendance_col.delete_many({"employee_id": employee_id})
    if database.leave_requests_col is not None:
        database.leave_requests_col.delete_many({"employee_id": employee_id})

    return jsonify({"success": True, "message": "Employee and associated records deleted successfully."}), 200

@employees_bp.route("/<emp_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(emp_id):
    if database.users_col is None:
        return _database_unavailable_response()
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

