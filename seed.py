"""Initialize MongoDB indexes and the one required administrator account."""
import sys

from app.database import init_db


def initialize_database():
    print("Connecting to MongoDB...")
    if init_db() is None:
        print("[ERROR] Could not connect to MongoDB.")
        sys.exit(1)

    print("[SUCCESS] Database indexes are ready and the initial admin account is available.")
    print("Sign in with ID ADMIN01 and password Admin@123, then create employee records in the Admin Dashboard.")


if __name__ == "__main__":
    initialize_database()
