from flask import Blueprint, jsonify
from app import database
from app.middleware.auth import admin_required
from app.services.attendance_service import get_current_time_data, is_sunday, get_holiday_info

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/stats", methods=["GET"])
@admin_required
def get_dashboard_stats():
    today, current_time = get_current_time_data()
    today_is_holiday, hol_name, hol_reason = get_holiday_info(today)
    
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
    
    # On Sunday or Admin-reserved Holiday, absent count is 0
    if today_is_holiday:
        absent_today = 0
    else:
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
            "on_leave_today": on_leave_today,
            "is_sunday": is_sunday(today),
            "is_holiday": today_is_holiday,
            "holiday_name": hol_name,
            "holiday_reason": hol_reason
        },
        "today_attendance": today_records
    }), 200
