import re
from app.config import Config

def is_valid_email(email: str) -> bool:
    regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(regex, email.strip()))

def is_valid_coordinates(lat, lon) -> bool:
    try:
        f_lat = float(lat)
        f_lon = float(lon)
        return -90.0 <= f_lat <= 90.0 and -180.0 <= f_lon <= 180.0
    except (ValueError, TypeError):
        return False

def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS
