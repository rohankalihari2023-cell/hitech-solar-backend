from flask import Blueprint, request, Response, send_file
from app import database
from app.middleware.auth import admin_required
from app.services.report_service import generate_csv_report, generate_pdf_report

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("", methods=["GET"])
@admin_required
def get_reports_data():
    emp_id = request.args.get("employee_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    status = request.args.get("status")

    query = {}
    if emp_id:
        query["employee_id"] = emp_id.upper()
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    if status:
        query["status"] = status.upper()

    records = list(database.attendance_col.find(query).sort("date", -1))
    for r in records:
        r["id"] = str(r.pop("_id"))
    return {"success": True, "records": records}, 200

@reports_bp.route("/export/csv", methods=["GET"])
@admin_required
def export_csv():
    start_date = request.args.get("start_date", "2026-01-01")
    end_date = request.args.get("end_date", "2026-12-31")
    emp_id = request.args.get("employee_id")

    query = {"date": {"$gte": start_date, "$lte": end_date}}
    if emp_id:
        query["employee_id"] = emp_id.upper()

    records = list(database.attendance_col.find(query).sort("date", -1))
    csv_content = generate_csv_report(records)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=attendance_{start_date}_to_{end_date}.csv"}
    )

@reports_bp.route("/export/pdf", methods=["GET"])
@admin_required
def export_pdf():
    start_date = request.args.get("start_date", "2026-01-01")
    end_date = request.args.get("end_date", "2026-12-31")
    emp_id = request.args.get("employee_id")

    query = {"date": {"$gte": start_date, "$lte": end_date}}
    if emp_id:
        query["employee_id"] = emp_id.upper()

    records = list(database.attendance_col.find(query).sort("date", -1))
    pdf_buffer = generate_pdf_report(records, start_date, end_date)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"attendance_report_{start_date}_to_{end_date}.pdf"
    )
