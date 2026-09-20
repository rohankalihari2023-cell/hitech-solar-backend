import io
import csv
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_csv_report(records: list) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Employee ID",
        "Employee Name",
        "Date",
        "Check In",
        "Check Out",
        "Working Hours",
        "Status",
        "Late Status",
        "Check In Coordinates",
        "Check Out Coordinates",
        "Device Info"
    ])
    
    for r in records:
        in_coords = f"{r.get('check_in_latitude', '')},{r.get('check_in_longitude', '')}" if r.get('check_in_latitude') else "N/A"
        out_coords = f"{r.get('check_out_latitude', '')},{r.get('check_out_longitude', '')}" if r.get('check_out_latitude') else "N/A"
        writer.writerow([
            r.get("employee_id", ""),
            r.get("employee_name", ""),
            r.get("date", ""),
            r.get("check_in_time", "N/A"),
            r.get("check_out_time", "N/A"),
            r.get("working_hours", 0.0),
            r.get("status", ""),
            r.get("late_status", "NO"),
            in_coords,
            out_coords,
            r.get("device_info", "Android App")
        ])
        
    return output.getvalue()

def generate_pdf_report(records: list, start_date: str, end_date: str) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'RepTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A')
    )
    sub_style = ParagraphStyle(
        'RepSub',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#64748B')
    )

    story.append(Paragraph("Employee Attendance System - Official Report", title_style))
    story.append(Paragraph(f"Reporting Range: {start_date} to {end_date} | Total Records: {len(records)}", sub_style))
    story.append(Spacer(1, 14))

    headers = ["Emp ID", "Employee Name", "Date", "Check In", "Check Out", "Hours", "Status", "Late"]
    table_data = [headers]
    for r in records:
        table_data.append([
            r.get("employee_id", ""),
            r.get("employee_name", ""),
            r.get("date", ""),
            r.get("check_in_time", "-"),
            r.get("check_out_time", "-"),
            str(r.get("working_hours", 0.0)),
            r.get("status", ""),
            r.get("late_status", "NO")
        ])

    t = Table(table_data, colWidths=[70, 160, 80, 80, 80, 60, 90, 60])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))

    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer
