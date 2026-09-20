import jwt
import datetime
from app.config import Config

def generate_token(user_id: str, employee_id: str, role: str, email: str, name: str) -> str:
    payload = {
        "user_id": str(user_id),
        "employee_id": employee_id,
        "role": role,
        "email": email,
        "name": name,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=Config.JWT_EXPIRY_HOURS),
        "iat": datetime.datetime.now(datetime.timezone.utc)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid authentication token.")
