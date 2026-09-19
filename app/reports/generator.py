import io
import csv
import datetime
from typing import List, Dict, Any, Tuple
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.database import mongo
from app.compliance.service import list_compliance_requirements
from app.violations.service import list_violations
from app.inspections.service import list_inspections
from app.incidents.service import list_incidents
from app.contractors.service import list_contractors


def generate_csv_report(report_type: str, mine_id: str = None) -> Tuple[str, str]:
    """Generates a CSV formatted report and returns (csv_string, filename)."""
    output = io.StringIO()
    writer = csv.writer(output)
    now_str = datetime.date.today().strftime("%Y%m%d")

    if report_type == "compliance":
        filename = f"compliance_report_{now_str}.csv"
        writer.writerow(["Requirement ID", "Title", "Category", "Mine ID", "Status", "Due Date", "Frequency"])
        items = list_compliance_requirements(mine_id=mine_id)
        for i in items:
            writer.writerow([
                str(i.get("_id")),
                i.get("title"),
                i.get("category"),
                i.get("applicable_mine"),
                i.get("status"),
                str(i.get("due_date", ""))[:10],
                i.get("frequency")
            ])

    elif report_type == "violation":
        filename = f"violation_report_{now_str}.csv"
        writer.writerow(["Violation ID", "Mine ID", "Zone", "Category", "Severity", "Status", "Deadline", "Description"])
        items = list_violations(mine_id=mine_id)
        for v in items:
            writer.writerow([
                str(v.get("_id")),
                v.get("mine_id"),
                v.get("zone"),
                v.get("category"),
                v.get("severity"),
                v.get("status"),
                str(v.get("deadline", ""))[:19],
                v.get("description")
            ])

    elif report_type == "inspection":
        filename = f"inspection_report_{now_str}.csv"
        writer.writerow(["Inspection ID", "Mine ID", "Officer ID", "Type", "Status", "Severity", "Scheduled Date"])
        items = list_inspections(mine_id=mine_id)
        for ins in items:
            writer.writerow([
                str(ins.get("_id")),
                ins.get("mine_id"),
                ins.get("officer_id"),
                ins.get("inspection_type"),
                ins.get("status"),
                ins.get("severity"),
                str(ins.get("scheduled_date", ""))[:10]
            ])

    elif report_type == "incident":
        filename = f"incident_report_{now_str}.csv"
        writer.writerow(["Incident ID", "Mine ID", "Type", "Severity", "Status", "Reported At", "Description"])
        items = list_incidents(mine_id=mine_id)
        for inc in items:
            writer.writerow([
                str(inc.get("_id")),
                inc.get("mine_id"),
                inc.get("incident_type"),
                inc.get("severity"),
                inc.get("investigation_status"),
                str(inc.get("reported_at", ""))[:19],
                inc.get("description")
            ])

    elif report_type == "contractor":
        filename = f"contractor_report_{now_str}.csv"
        writer.writerow(["Contractor ID", "Company Name", "Mine ID", "Workers", "Compliance Status", "Risk Score", "Risk Level"])
        items = list_contractors(mine_id=mine_id)
        for c in items:
            writer.writerow([
                str(c.get("_id")),
                c.get("company_name"),
                c.get("mine_id"),
                c.get("workers_count"),
                c.get("compliance_status"),
                c.get("risk_score"),
                c.get("risk_level")
            ])

    else:
        # Monthly Governance Report Default
        filename = f"monthly_governance_report_{now_str}.csv"
        writer.writerow(["Category", "Metric", "Value", "Date Generated"])
        writer.writerow(["Governance", "Active Mines", mongo.mines.count_documents({}), now_str])
        writer.writerow(["Safety", "Open Violations", mongo.violations.count_documents({"status": {"$ne": "CLOSED"}}), now_str])
        writer.writerow(["Compliance", "Statutory Requirements", mongo.compliance_requirements.count_documents({}), now_str])
        writer.writerow(["Incidents", "Total Incidents Recorded", mongo.incidents.count_documents({}), now_str])

    return output.getvalue(), filename


def generate_pdf_report(report_type: str, mine_id: str = None) -> Tuple[bytes, str]:
    """Generates an executive PDF report with tables and styles."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = []
    now_str = datetime.date.today().strftime("%d-%b-%Y")

    # Header title
    title_style = ParagraphStyle(
        name="TitleStyle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e293b")
    )
    subtitle_style = ParagraphStyle(
        name="SubStyle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b")
    )

    elements.append(Paragraph(f"CoalGov-AI: Statutory {report_type.upper()} Governance Report", title_style))
    elements.append(Paragraph(f"Generated on {now_str} | Ministry of Coal & DGMS Compliance Monitoring", subtitle_style))
    elements.append(Spacer(1, 16))

    data_table = []
    if report_type == "violation":
        filename = f"violation_report_{now_str}.pdf"
        headers = ["ID", "Mine", "Category", "Severity", "Status", "Deadline"]
        data_table.append(headers)
        items = list_violations(mine_id=mine_id)[:20]
        for v in items:
            data_table.append([
                str(v.get("_id"))[:8],
                str(v.get("mine_id"))[:10],
                str(v.get("category"))[:18],
                v.get("severity", "MED"),
                v.get("status", "OPEN")[:12],
                str(v.get("deadline", ""))[:10]
            ])
    elif report_type == "compliance":
        filename = f"compliance_report_{now_str}.pdf"
        headers = ["ID", "Title", "Category", "Mine", "Status", "Due Date"]
        data_table.append(headers)
        items = list_compliance_requirements(mine_id=mine_id)[:20]
        for c in items:
            data_table.append([
                str(c.get("_id"))[:8],
                c.get("title")[:20],
                c.get("category")[:12],
                str(c.get("applicable_mine"))[:8],
                c.get("status")[:12],
                str(c.get("due_date", ""))[:10]
            ])
    else:
        filename = f"monthly_governance_{now_str}.pdf"
        headers = ["Metric Category", "Description", "Value"]
        data_table.append(headers)
        data_table.append(["Mines Operations", "Total Active Coal Mines", str(mongo.mines.count_documents({}))])
        data_table.append(["Statutory Safety", "Open Safety Violations", str(mongo.violations.count_documents({"status": {"$ne": "CLOSED"}}))])
        data_table.append(["Inspections", "Total Inspections Completed", str(mongo.inspections.count_documents({"status": "CLOSED"}))])
        data_table.append(["Contractor Governance", "Registered Mine Contractors", str(mongo.contractors.count_documents({}))])

    t = Table(data_table, colWidths=[65, 110, 110, 75, 80, 90] if len(data_table[0]) == 6 else [150, 230, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])
    ]))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue(), filename
