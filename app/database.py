import logging
from datetime import datetime, timezone
import bcrypt
from pymongo import MongoClient, ASCENDING, DESCENDING
from app.config import Config

logger = logging.getLogger(__name__)

client = None
db = None
users_col = None
attendance_col = None
leave_requests_col = None
company_settings_col = None
holidays_col = None
audit_logs_col = None


# MongoDB is schema-flexible by default. These validators make the persisted
# records predictable while still allowing an empty database at first launch.
COLLECTION_VALIDATORS = {
    "users": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "email", "employee_id", "password_hash", "role", "department", "phone", "is_field_worker", "is_active", "created_at"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "name": {"bsonType": "string", "minLength": 1},
                "email": {"bsonType": "string", "pattern": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"},
                "employee_id": {"bsonType": "string", "minLength": 1},
                "password_hash": {"bsonType": "string", "minLength": 1},
                "role": {"enum": ["ADMIN", "EMPLOYEE"]},
                "department": {"bsonType": "string"},
                "phone": {"bsonType": "string"},
                "is_field_worker": {"bsonType": "bool"},
                "is_active": {"bsonType": "bool"},
                "created_at": {"bsonType": "date"},
                "profile_photo": {"bsonType": ["string", "null"]},
            },
        }
    },
    "attendance": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["employee_id", "employee_name", "date", "check_in_time", "check_out_time", "working_hours", "check_in_latitude", "check_in_longitude", "check_out_latitude", "check_out_longitude", "check_in_photo", "check_out_photo", "status", "late_status", "is_field_worker", "distance_meters", "device_info", "created_at", "updated_at"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "employee_id": {"bsonType": "string"}, "employee_name": {"bsonType": "string"}, "date": {"bsonType": "string"},
                "check_in_time": {"bsonType": "string"}, "check_out_time": {"bsonType": ["string", "null"]},
                "working_hours": {"bsonType": ["double", "int", "long", "decimal"]},
                "check_in_latitude": {"bsonType": ["double", "int", "long", "decimal"]}, "check_in_longitude": {"bsonType": ["double", "int", "long", "decimal"]},
                "check_out_latitude": {"bsonType": ["double", "int", "long", "decimal", "null"]}, "check_out_longitude": {"bsonType": ["double", "int", "long", "decimal", "null"]},
                "check_in_photo": {"bsonType": "string"}, "check_out_photo": {"bsonType": ["string", "null"]},
                "status": {"enum": ["PRESENT", "LATE", "HALF_DAY"]}, "late_status": {"enum": ["LATE", "NO"]},
                "is_field_worker": {"bsonType": "bool"}, "distance_meters": {"bsonType": ["double", "int", "long", "decimal"]},
                "device_info": {"bsonType": "string"}, "created_at": {"bsonType": "date"}, "updated_at": {"bsonType": "date"},
            },
        }
    },
    "leave_requests": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["employee_id", "employee_name", "start_date", "end_date", "leave_type", "reason", "status", "rejection_reason", "reviewed_by", "created_at"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "employee_id": {"bsonType": "string"}, "employee_name": {"bsonType": "string"},
                "start_date": {"bsonType": "string"}, "end_date": {"bsonType": "string"}, "leave_type": {"bsonType": "string"}, "reason": {"bsonType": "string"},
                "status": {"enum": ["PENDING", "APPROVED", "REJECTED"]}, "rejection_reason": {"bsonType": ["string", "null"]},
                "reviewed_by": {"bsonType": ["string", "null"]}, "reviewed_at": {"bsonType": "date"}, "created_at": {"bsonType": "date"},
            },
        }
    },
    "company_settings": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["key", "office_latitude", "office_longitude", "office_radius", "office_start_time", "office_end_time", "late_after", "minimum_working_hours", "half_day_hours"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "key": {"enum": ["default_rules"]}, "office_latitude": {"bsonType": ["double", "int", "long", "decimal"]},
                "office_longitude": {"bsonType": ["double", "int", "long", "decimal"]}, "office_radius": {"bsonType": ["double", "int", "long", "decimal"]},
                "office_start_time": {"bsonType": "string"}, "office_end_time": {"bsonType": "string"}, "late_after": {"bsonType": "string"},
                "minimum_working_hours": {"bsonType": ["double", "int", "long", "decimal"]}, "half_day_hours": {"bsonType": ["double", "int", "long", "decimal"]},
            },
        }
    },
}

def init_db(app=None):
    global client, db, users_col, attendance_col, leave_requests_col, company_settings_col, holidays_col, audit_logs_col
    try:
        client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
        # Verify connection
        client.admin.command('ping')
        
        try:
            db_name = client.get_default_database().name
        except Exception:
            db_name = "attendance_db"
            
        if not db_name:
            db_name = "attendance_db"

        db = client[db_name]
        
        users_col = db["users"]
        attendance_col = db["attendance"]
        leave_requests_col = db["leave_requests"]
        company_settings_col = db["company_settings"]
        holidays_col = db["holidays"]
        audit_logs_col = db["audit_logs"]

        _apply_collection_validators()
        _create_indexes()
        _ensure_default_admin()
        logger.info(f"MongoDB connected successfully to database: {db.name}")
        return db
    except Exception as e:
        logger.warning(f"MongoDB connection notice: {str(e)}")
        # In case MongoDB is offline during build or initial test, we still return client
        return None


def _apply_collection_validators():
    existing_collections = set(db.list_collection_names())
    for name, validator in COLLECTION_VALIDATORS.items():
        options = {"validator": validator, "validationLevel": "moderate", "validationAction": "error"}
        if name in existing_collections:
            db.command("collMod", name, **options)
        else:
            db.create_collection(name, **options)

def _create_indexes():
    if users_col is None:
        return
    try:
        users_col.create_index("email", unique=True)
        users_col.create_index("employee_id", unique=True)
        attendance_col.create_index([("employee_id", ASCENDING), ("date", ASCENDING)], unique=True)
        attendance_col.create_index([("created_at", DESCENDING)])
        attendance_col.create_index("date")
        leave_requests_col.create_index([("employee_id", ASCENDING), ("created_at", DESCENDING)])
        leave_requests_col.create_index("status")
        company_settings_col.create_index("key", unique=True)
    except Exception as err:
        logger.warning(f"Index creation notice: {err}")


def _ensure_default_admin():
    """Create the initial administrator once, only for an otherwise empty database."""
    if users_col.count_documents({}) != 0:
        return

    admin = {
        "name": "Administrator",
        "email": "admin@hitechsolar.com",
        "employee_id": "ADMIN01",
        "password_hash": bcrypt.hashpw(b"Admin@123", bcrypt.gensalt()).decode("utf-8"),
        "role": "ADMIN",
        "department": "Administration",
        "phone": "",
        "is_field_worker": False,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    users_col.update_one(
        {"employee_id": admin["employee_id"]},
        {"$setOnInsert": admin},
        upsert=True,
    )
    logger.warning("Created initial administrator account with employee ID ADMIN01.")
