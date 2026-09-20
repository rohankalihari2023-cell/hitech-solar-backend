from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    print(f"Starting Attendance Management REST API on port {Config.PORT}...")
    app.run(host="0.0.0.0", port=Config.PORT, debug=True)
