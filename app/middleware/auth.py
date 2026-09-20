from functools import wraps
from flask import request, jsonify, g
from bson import ObjectId
from app.utils.jwt_utils import decode_token
from app import database

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header:
            return jsonify({"success": False, "message": "Authorization header missing."}), 401
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"success": False, "message": "Invalid token format. Expected: Bearer <token>"}), 401
        
        try:
            payload = decode_token(parts[1])
            if database.users_col is not None:
                user = database.users_col.find_one({"_id": ObjectId(payload["user_id"])})
                if not user or not user.get("is_active", True):
                    return jsonify({"success": False, "message": "Account inactive or unauthorized."}), 403
                g.current_user = {
                    "user_id": str(user["_id"]),
                    "employee_id": user["employee_id"],
                    "role": user["role"],
                    "email": user["email"],
                    "name": user["name"]
                }
            else:
                g.current_user = {
                    "user_id": payload["user_id"],
                    "employee_id": payload["employee_id"],
                    "role": payload["role"],
                    "email": payload["email"],
                    "name": payload["name"]
                }
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)}), 401
        except Exception:
            return jsonify({"success": False, "message": "Authentication failed."}), 401
        
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    @jwt_required
    def decorated(*args, **kwargs):
        if g.current_user.get("role") != "ADMIN":
            return jsonify({"success": False, "message": "Access denied. Administrator privileges required."}), 403
        return f(*args, **kwargs)
    return decorated
