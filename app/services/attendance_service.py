from datetime import datetime, time
from zoneinfo import ZoneInfo
from app import database

def get_current_time_data():
    """Returns exact current date and time in India Standard Time (IST)"""
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    return now_ist.strftime("%Y-%m-%d"), now_ist.strftime("%H:%M:%S")

def get_company_settings():
    default_settings = {
        "office_latitude": 28.6139,
        "office_longitude": 77.2090,
        "office_radius": 150.0,
        "office_start_time": "09:30",
        "office_end_time": "18:30",
        "late_after": "09:45",
        "minimum_working_hours": 8.0,
        "half_day_hours": 4.0
    }
    if database.company_settings_col is None:
        return default_settings
    settings = database.company_settings_col.find_one({"key": "default_rules"})
    if not settings:
        return default_settings
    for k, v in default_settings.items():
        if k not in settings:
            settings[k] = v
    return settings

def determine_status_on_checkin(check_in_time_str: str, settings: dict) -> str:
    try:
        c_time = datetime.strptime(check_in_time_str, "%H:%M:%S").time()
        late_parts = [int(p) for p in settings.get("late_after", "09:45").split(":")]
        late_threshold = time(late_parts[0], late_parts[1])
        return "LATE" if c_time > late_threshold else "PRESENT"
    except Exception:
        return "PRESENT"

def calculate_working_hours(check_in_str: str, check_out_str: str) -> float:
    try:
        fmt = "%H:%M:%S"
        diff = datetime.strptime(check_out_str, fmt) - datetime.strptime(check_in_str, fmt)
        hours = diff.total_seconds() / 3600.0
        return max(0.0, round(hours, 2))
    except Exception:
        return 0.0
