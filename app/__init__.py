from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.database import init_db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS for Flutter mobile application
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize Database
    init_db(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.employees import employees_bp
    from app.routes.attendance import attendance_bp
    from app.routes.leave import leave_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.holidays import holidays_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(employees_bp, url_prefix="/api/employees")
    app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
    app.register_blueprint(leave_bp, url_prefix="/api/leave")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(settings_bp, url_prefix="/api/settings")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(holidays_bp, url_prefix="/api/holidays")

    @app.route("/", methods=["GET"])
    def index():
        return {"status": "online", "message": "Attendance Management REST API is Running"}, 200

    @app.route("/health", methods=["GET"])
    def health_check():
        return {"status": "online", "service": "Employee Attendance Management REST API"}, 200

    return app
