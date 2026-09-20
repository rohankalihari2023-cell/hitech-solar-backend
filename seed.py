"""
Database Initialization & Seeder Script for Hi-Tech Solar Energy Solution
"""
import sys
import bcrypt
from datetime import datetime, timezone
from app.database import init_db
import app.database as db

def seed():
    print("Connecting to MongoDB Atlas...")
    database = init_db()
    if database is None:
        print("[ERROR] Could not connect to MongoDB.")
        sys.exit(1)

    print("Cleaning up old placeholder accounts...")
    db.users_col.delete_many({"email": {"$regex": "@company\\.com$"}})

    print("Configuring Hi-Tech Solar office geofence & attendance rules...")
    db.company_settings_col.update_one(
        {"key": "default_rules"},
        {"$set": {
            "key": "default_rules",
            "company_name": "Hi-Tech Solar Energy Solution",
            "website": "https://hi-tech-solar-energy-solution.vercel.app/",
            "office_latitude": 28.6139,
            "office_longitude": 77.2090,
            "office_radius": 150.0,
            "office_start_time": "09:30",
            "office_end_time": "18:30",
            "late_after": "09:45",
            "minimum_working_hours": 8.0,
            "half_day_hours": 4.0
        }},
        upsert=True
    )

    print("\nCreating official Hi-Tech Solar accounts...")
    accounts = [
        {
            "name": "Hi-Tech Administrator",
            "email": "admin@hitechsolar.com",
            "employee_id": "ADMIN01",
            "password": "Admin@123",
            "role": "ADMIN",
            "department": "Management",
            "phone": "+91 98765 43210"
        },
        {
            "name": "Solar Field Tech 1",
            "email": "alex@hitechsolar.com",
            "employee_id": "EMP01",
            "password": "Emp@123",
            "role": "EMPLOYEE",
            "department": "Solar Installation & Ops",
            "phone": "+91 98765 43211"
        },
        {
            "name": "Solar Systems Engineer",
            "email": "sarah@hitechsolar.com",
            "employee_id": "EMP02",
            "password": "Emp@123",
            "role": "EMPLOYEE",
            "department": "Engineering & Design",
            "phone": "+91 98765 43212"
        },
        {
            "name": "Operations Executive",
            "email": "david@hitechsolar.com",
            "employee_id": "EMP03",
            "password": "Emp@123",
            "role": "EMPLOYEE",
            "department": "Procurement & Dispatch",
            "phone": "+91 98765 43213"
        }
    ]

    for acc in accounts:
        hashed = bcrypt.hashpw(acc["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        doc = {
            "name": acc["name"],
            "email": acc["email"],
            "employee_id": acc["employee_id"],
            "password_hash": hashed,
            "role": acc["role"],
            "department": acc["department"],
            "phone": acc["phone"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }
        db.users_col.update_one({"employee_id": acc["employee_id"]}, {"$set": doc}, upsert=True)
        print(f"  -> Created [{acc['role']}]: {acc['email']} / ID: {acc['employee_id']} (Pass: {acc['password']})")

    print("\n[SUCCESS] Hi-Tech Solar accounts seeded successfully into MongoDB Atlas!")

if __name__ == "__main__":
    seed()
