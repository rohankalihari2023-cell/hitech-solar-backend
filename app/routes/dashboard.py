from datetime import datetime
from flask import Blueprint, jsonify
from app import database
from app.middleware.auth import admin_required

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/stats", methods=["GET"])
@admin_required
def get_dashboard_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    
    total_employees = 0
    today_records = []
    on_leave_today = 0

    if database.users_col is not None:
        total_employees = database.users_col.count_documents({"role": "EMPLOYEE", "is_active": True})
    
    if database.attendance_col is not None:
        today_records = list(database.attendance_col.find({"date": today}))

    if database.leave_requests_col is not None:
        on_leave_today = database.leave_requests_col.count_documents({
            "status": "APPROVED",
            "start_date": {"$lte": today},
            "end_date": {"$gte": today}
        })

    present_today = len(today_records)
    late_today = sum(1 for r in today_records if r.get("status") == "LATE" or r.get("late_status") == "LATE")
    currently_working = sum(1 for r in today_records if r.get("check_in_time") and not r.get("check_out_time"))
    absent_today = max(0, total_employees - present_today - on_leave_today)

    for r in today_records:
        r["id"] = str(r.pop("_id"))

    return jsonify({
        "success": True,
        "stats": {
            "total_employees": total_employees,
            "present_today": present_today,
            "absent_today": absent_today,
            "late_today": late_today,
            "currently_working": currently_working,
            "on_leave_today": on_leave_today
        },
        "today_attendance": today_records
    }), 200
