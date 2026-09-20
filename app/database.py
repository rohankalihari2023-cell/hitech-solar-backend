import logging
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

        _create_indexes()
        logger.info(f"MongoDB connected successfully to database: {db.name}")
        return db
    except Exception as e:
        logger.warning(f"MongoDB connection notice: {str(e)}")
        # In case MongoDB is offline during build or initial test, we still return client
        return None

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
