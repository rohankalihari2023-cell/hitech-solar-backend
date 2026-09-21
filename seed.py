"""Initialize MongoDB indexes without creating sample users or settings."""
import sys

from app.database import init_db


def initialize_database():
    print("Connecting to MongoDB...")
    if init_db() is None:
        print("[ERROR] Could not connect to MongoDB.")
        sys.exit(1)

    print("[SUCCESS] Database indexes are ready. No users, attendance, or settings data was created.")
    print("Use an existing administrator account to create employee records in the Admin Dashboard.")


if __name__ == "__main__":
    initialize_database()
