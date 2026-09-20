"""
Automated System Verification Script
Verifies:
1. Haversine formula calculation & Geofencing verification
2. JWT Token generation & verification
3. Attendance rules (late calculation, working hours calculation)
4. CSV & PDF generation pipeline
"""
import sys
import unittest
from datetime import datetime

from app.services.geofence_service import calculate_haversine_distance, verify_geofence
from app.services.attendance_service import determine_status_on_checkin, calculate_working_hours
from app.services.report_service import generate_csv_report, generate_pdf_report
from app.utils.jwt_utils import generate_token, decode_token
from app.utils.validators import is_valid_email, is_valid_coordinates, allowed_file

class TestAttendanceSystem(unittest.TestCase):

    def test_haversine_geofence(self):
        # Office at New Delhi (28.6139, 77.2090)
        office_lat, office_lon = 28.6139, 77.2090
        
        # Point 1: Same location (distance should be 0)
        dist = calculate_haversine_distance(office_lat, office_lon, office_lat, office_lon)
        self.assertEqual(dist, 0.0)

        # Point 2: Very close (approx 40-50m away)
        close_lat, close_lon = 28.6142, 77.2092
        is_inside, d = verify_geofence(close_lat, close_lon, office_lat, office_lon, radius_meters=150.0)
        self.assertTrue(is_inside)
        self.assertLess(d, 150.0)

        # Point 3: Far away (approx 10km away)
        far_lat, far_lon = 28.5355, 77.3910
        is_inside_far, d_far = verify_geofence(far_lat, far_lon, office_lat, office_lon, radius_meters=150.0)
        self.assertFalse(is_inside_far)
        self.assertGreater(d_far, 150.0)
        print(f"Haversine geofence tests passed! (Close: {d}m, Far: {d_far}m)")

    def test_jwt_lifecycle(self):
        token = generate_token(
            user_id="60d5ec49f1b2c8b1f8e4e1a1",
            employee_id="EMP01",
            role="EMPLOYEE",
            email="alex@company.com",
            name="Alex Miller"
        )
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 20)

        decoded = decode_token(token)
        self.assertEqual(decoded["employee_id"], "EMP01")
        self.assertEqual(decoded["role"], "EMPLOYEE")
        self.assertEqual(decoded["email"], "alex@company.com")
        print("JWT token lifecycle tests passed!")

    def test_attendance_status_rules(self):
        settings = {"late_after": "09:45"}
        
        # Check-in at 09:15 -> PRESENT
        s1 = determine_status_on_checkin("09:15:00", settings)
        self.assertEqual(s1, "PRESENT")

        # Check-in at 09:44:59 -> PRESENT
        s2 = determine_status_on_checkin("09:44:59", settings)
        self.assertEqual(s2, "PRESENT")

        # Check-in at 09:50 -> LATE
        s3 = determine_status_on_checkin("09:50:00", settings)
        self.assertEqual(s3, "LATE")

        # Working hours calculation
        hours = calculate_working_hours("09:30:00", "18:00:00")
        self.assertEqual(hours, 8.5)
        print("Attendance rules tests passed!")

    def test_validators(self):
        self.assertTrue(is_valid_email("alex@company.com"))
        self.assertFalse(is_valid_email("invalid-email"))
        self.assertTrue(is_valid_coordinates(28.6139, 77.2090))
        self.assertFalse(is_valid_coordinates(190.0, 77.2090))
        self.assertTrue(allowed_file("selfie.jpg"))
        self.assertTrue(allowed_file("photo.png"))
        self.assertFalse(allowed_file("script.sh"))
        print("Validator tests passed!")

    def test_report_generation(self):
        sample_records = [
            {
                "employee_id": "EMP01",
                "employee_name": "Alex Miller",
                "date": "2026-09-20",
                "check_in_time": "09:15:00",
                "check_out_time": "18:15:00",
                "working_hours": 9.0,
                "status": "PRESENT",
                "late_status": "NO",
                "check_in_latitude": 28.6139,
                "check_in_longitude": 77.2090
            }
        ]
        csv_out = generate_csv_report(sample_records)
        self.assertIn("Alex Miller", csv_out)
        self.assertIn("EMP01", csv_out)

        pdf_buf = generate_pdf_report(sample_records, "2026-09-01", "2026-09-30")
        self.assertGreater(pdf_buf.getbuffer().nbytes, 1000)
        print("CSV and PDF generation tests passed!")

if __name__ == "__main__":
    unittest.main()
