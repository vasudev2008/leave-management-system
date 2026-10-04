"""
Reports generator for Locktite India Pvt Ltd - Employee Leave Management System.
Generates professional office-ready PDF documents (ReportLab) and Excel/CSV sheets (pandas/openpyxl).
"""

import io
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Adds professional header line, footer, date, and page numbering to each PDF page."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4A5568"))
        
        # Bottom footer line
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(36, 40, A4[0] - 36, 40)
        
        # Bottom footer text
        self.setFont("Helvetica", 8)
        footer_text = "Locktite India Pvt Ltd — Official Leave Management Record (Confidential)"
        self.drawString(36, 28, footer_text)
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 36, 28, page_str)
        self.restoreState()


def get_pdf_styles():
    styles = getSampleStyleSheet()
    
    company_style = ParagraphStyle(
        'CompanyHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        alignment=1,  # Center
        textColor=colors.HexColor("#0F172A")
    )
    
    sub_title_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        alignment=1,  # Center
        textColor=colors.HexColor("#2563EB")
    )
    
    report_title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=1,  # Center
        textColor=colors.HexColor("#1E293B")
    )
    
    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569")
    )
    
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )
    
    cell_bold_style = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A")
    )

    cell_add_style = ParagraphStyle(
        'CellAdd',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#DC2626")  # Red for ADD (taken leave)
    )

    cell_less_style = ParagraphStyle(
        'CellLess',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#16A34A")  # Green for LESS (cancelled/credited)
    )

    return {
        "company": company_style,
        "subtitle": sub_title_style,
        "report_title": report_title_style,
        "meta": meta_style,
        "cell": cell_style,
        "cell_bold": cell_bold_style,
        "cell_add": cell_add_style,
        "cell_less": cell_less_style
    }


def generate_individual_statement_pdf(
    employee: Dict[str, Any],
    transactions: List[Dict[str, Any]],
    generated_by: str,
    date_range: Optional[str] = "All Time"
) -> bytes:
    """Generates official Individual Employee Leave Statement PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=55
    )
    
    styles = get_pdf_styles()
    story = []

    # 1. Company Header
    story.append(Paragraph("LOCKTITE INDIA PVT LTD", styles["company"]))
    story.append(Spacer(1, 2))
    story.append(Paragraph("EMPLOYEE LEAVE MANAGEMENT SYSTEM", styles["subtitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("EMPLOYEE LEAVE STATEMENT", styles["report_title"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceBefore=2, spaceAfter=8))

    # 2. Metadata / Generation Info
    gen_time_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    meta_table_data = [
        [
            Paragraph(f"<b>Generated By:</b> {generated_by}", styles["meta"]),
            Paragraph(f"<b>Generation Date:</b> {gen_time_str}", styles["meta"]),
            Paragraph(f"<b>Period:</b> {date_range}", styles["meta"])
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[200, 180, 142])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 3. Employee Info & Leave Summary Card
    entitlement = float(employee.get("leave_entitlement", 20.0))
    opening = float(employee.get("opening_balance", 20.0))
    taken = float(employee.get("leave_taken", 0.0))
    balance = float(employee.get("current_balance", opening - taken))

    emp_details_data = [
        [
            Paragraph(f"<b>Employee No:</b> {employee.get('employee_number', 'N/A')}", styles["cell"]),
            Paragraph(f"<b>Department:</b> {employee.get('department', 'N/A')}", styles["cell"]),
            Paragraph(f"<b>Leave Entitlement:</b> <b>{entitlement:.1f} days</b>", styles["cell_bold"])
        ],
        [
            Paragraph(f"<b>Employee Name:</b> {employee.get('employee_name', 'N/A')}", styles["cell_bold"]),
            Paragraph(f"<b>Designation:</b> {employee.get('designation', 'N/A')}", styles["cell"]),
            Paragraph(f"<b>Opening Balance:</b> <b>{opening:.1f} days</b>", styles["cell_bold"])
        ],
        [
            Paragraph(f"<b>Date of Joining:</b> {employee.get('date_of_joining', 'N/A')}", styles["cell"]),
            Paragraph(f"<b>Status:</b> {employee.get('status', 'Active')}", styles["cell"]),
            Paragraph(f"<b>Total Leave Taken:</b> <font color='#DC2626'><b>{taken:.1f} days</b></font>", styles["cell_bold"])
        ],
        [
            Paragraph(f"<b>Mobile / Contact:</b> {employee.get('mobile', 'N/A')}", styles["cell"]),
            Paragraph(f"<b>Email:</b> {employee.get('email', 'N/A')}", styles["cell"]),
            Paragraph(f"<b>Current Balance:</b> <font color='#16A34A'><b>{balance:.1f} days</b></font>", styles["cell_bold"])
        ]
    ]

    emp_card = Table(emp_details_data, colWidths=[180, 180, 162])
    emp_card.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BFDBFE")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#DBEAFE")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(emp_card)
    story.append(Spacer(1, 14))

    # 4. Transactions Table Header
    tx_headers = [
        Paragraph("<b>Tx ID</b>", styles["cell_bold"]),
        Paragraph("<b>From Date</b>", styles["cell_bold"]),
        Paragraph("<b>To Date</b>", styles["cell_bold"]),
        Paragraph("<b>Leave Type</b>", styles["cell_bold"]),
        Paragraph("<b>Transaction</b>", styles["cell_bold"]),
        Paragraph("<b>Days</b>", styles["cell_bold"]),
        Paragraph("<b>Remarks / Reason</b>", styles["cell_bold"])
    ]
    
    tx_table_data = [tx_headers]
    
    total_add_days = 0.0
    total_less_days = 0.0

    for tx in transactions:
        tx_type = tx.get("transaction_type", "ADD")
        days = float(tx.get("days", 0.0))
        if tx_type == "ADD":
            total_add_days += days
            tx_type_p = Paragraph("ADD", styles["cell_add"])
        else:
            total_less_days += days
            tx_type_p = Paragraph("LESS", styles["cell_less"])

        tx_table_data.append([
            Paragraph(f"LTX-{tx.get('id', 0):04d}", styles["cell"]),
            Paragraph(tx.get("from_date", ""), styles["cell"]),
            Paragraph(tx.get("to_date", ""), styles["cell"]),
            Paragraph(tx.get("leave_type_name", tx.get("leave_type", "")), styles["cell"]),
            tx_type_p,
            Paragraph(f"{days:.1f}", styles["cell_bold"]),
            Paragraph(tx.get("reason", "") or "-", styles["cell"])
        ])

    if len(transactions) == 0:
        tx_table_data.append([
            Paragraph("No leave transactions recorded for this employee.", styles["cell"]),
            "", "", "", "", "", ""
        ])

    # Totals Row
    net_taken = total_add_days - total_less_days
    tx_table_data.append([
        Paragraph("<b>TOTALS</b>", styles["cell_bold"]),
        "", "", "",
        Paragraph(f"<b>+ADD: {total_add_days:.1f} | -LESS: {total_less_days:.1f}</b>", styles["cell_bold"]),
        Paragraph(f"<b>Net: {net_taken:.1f}</b>", styles["cell_bold"]),
        Paragraph(f"<b>Final Leave Balance: {opening - net_taken:.1f} days</b>", styles["cell_bold"])
    ])

    tx_table = Table(tx_table_data, colWidths=[55, 65, 65, 95, 60, 45, 137])
    table_style_commands = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('ALIGN', (5,0), (5,-1), 'RIGHT'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#F1F5F9")),
    ]
    if len(transactions) == 0:
        table_style_commands.append(('SPAN', (0,1), (6,1)))
        table_style_commands.append(('ALIGN', (0,1), (6,1), 'CENTER'))

    tx_table.setStyle(TableStyle(table_style_commands))
    story.append(tx_table)
    story.append(Spacer(1, 25))

    # 5. Official Signatures Block
    sig_data = [
        [
            Paragraph("____________________________<br/><b>Prepared By</b><br/>Office Staff / HR", styles["cell"]),
            Paragraph("____________________________<br/><b>Verified By</b><br/>Department Head", styles["cell"]),
            Paragraph("____________________________<br/><b>Authorized Signatory</b><br/>Locktite India Pvt Ltd", styles["cell"])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[174, 174, 174])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(KeepTogether(sig_table))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


def generate_all_employees_summary_pdf(
    summary_data: List[Dict[str, Any]],
    generated_by: str,
    department_filter: Optional[str] = "All",
    status_filter: Optional[str] = "All"
) -> bytes:
    """Generates official All Employees Leave Summary Report PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=55
    )
    
    styles = get_pdf_styles()
    story = []

    # 1. Company Header
    story.append(Paragraph("LOCKTITE INDIA PVT LTD", styles["company"]))
    story.append(Spacer(1, 2))
    story.append(Paragraph("EMPLOYEE LEAVE MANAGEMENT SYSTEM", styles["subtitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("ALL EMPLOYEES LEAVE SUMMARY REPORT", styles["report_title"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceBefore=2, spaceAfter=8))

    # 2. Metadata
    gen_time_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    meta_table_data = [
        [
            Paragraph(f"<b>Generated By:</b> {generated_by}", styles["meta"]),
            Paragraph(f"<b>Generation Date:</b> {gen_time_str}", styles["meta"]),
            Paragraph(f"<b>Department:</b> {department_filter} | <b>Status:</b> {status_filter}", styles["meta"])
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[180, 180, 162])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 3. Main Data Table
    headers = [
        Paragraph("<b>Emp No</b>", styles["cell_bold"]),
        Paragraph("<b>Employee Name</b>", styles["cell_bold"]),
        Paragraph("<b>Department</b>", styles["cell_bold"]),
        Paragraph("<b>Entitlement</b>", styles["cell_bold"]),
        Paragraph("<b>Opening</b>", styles["cell_bold"]),
        Paragraph("<b>Taken</b>", styles["cell_bold"]),
        Paragraph("<b>Balance</b>", styles["cell_bold"]),
        Paragraph("<b>Status</b>", styles["cell_bold"])
    ]
    table_rows = [headers]

    tot_ent = 0.0
    tot_op = 0.0
    tot_taken = 0.0
    tot_bal = 0.0

    for emp in summary_data:
        ent = float(emp.get("leave_entitlement", 0.0))
        op = float(emp.get("opening_balance", 0.0))
        tk = float(emp.get("leave_taken", 0.0))
        bl = float(emp.get("current_balance", 0.0))
        
        tot_ent += ent
        tot_op += op
        tot_taken += tk
        tot_bal += bl

        bal_color = "#DC2626" if bl <= 3.0 else "#16A34A"
        bal_p = Paragraph(f"<font color='{bal_color}'><b>{bl:.1f}</b></font>", styles["cell_bold"])

        table_rows.append([
            Paragraph(emp.get("employee_number", ""), styles["cell_bold"]),
            Paragraph(emp.get("employee_name", ""), styles["cell"]),
            Paragraph(emp.get("department", ""), styles["cell"]),
            Paragraph(f"{ent:.1f}", styles["cell"]),
            Paragraph(f"{op:.1f}", styles["cell"]),
            Paragraph(f"{tk:.1f}", styles["cell"]),
            bal_p,
            Paragraph(emp.get("status", "Active"), styles["cell"])
        ])

    # Totals Row
    table_rows.append([
        Paragraph("<b>TOTALS</b>", styles["cell_bold"]),
        Paragraph(f"<b>Total Count: {len(summary_data)}</b>", styles["cell_bold"]),
        "",
        Paragraph(f"<b>{tot_ent:.1f}</b>", styles["cell_bold"]),
        Paragraph(f"<b>{tot_op:.1f}</b>", styles["cell_bold"]),
        Paragraph(f"<b>{tot_taken:.1f}</b>", styles["cell_bold"]),
        Paragraph(f"<b>{tot_bal:.1f}</b>", styles["cell_bold"]),
        ""
    ])

    summary_table = Table(table_rows, colWidths=[65, 125, 95, 55, 50, 45, 45, 42])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#F1F5F9")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # Official Signatures Block
    sig_data = [
        [
            Paragraph("____________________________<br/><b>HR & Admin Head</b><br/>Locktite India Pvt Ltd", styles["cell"]),
            Paragraph("____________________________<br/><b>Operations Manager</b><br/>Locktite India Pvt Ltd", styles["cell"]),
            Paragraph("____________________________<br/><b>Managing Director</b><br/>Locktite India Pvt Ltd", styles["cell"])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[174, 174, 174])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(KeepTogether(sig_table))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


def generate_all_employees_excel(
    summary_data: List[Dict[str, Any]],
    generated_by: str
) -> bytes:
    """Generates styled Excel file (.xlsx) for All Employees Leave Report."""
    rows = []
    for emp in summary_data:
        rows.append({
            "Employee No": emp.get("employee_number"),
            "Employee Name": emp.get("employee_name"),
            "Department": emp.get("department"),
            "Designation": emp.get("designation"),
            "Date of Joining": emp.get("date_of_joining"),
            "Leave Entitlement": emp.get("leave_entitlement"),
            "Opening Balance": emp.get("opening_balance"),
            "Leave Taken": emp.get("leave_taken"),
            "Current Balance": emp.get("current_balance"),
            "Status": emp.get("status"),
            "Mobile": emp.get("mobile"),
            "Email": emp.get("email")
        })
    df = pd.DataFrame(rows)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Leave Summary', startrow=4)
        worksheet = writer.sheets['Leave Summary']
        
        # Add Company Header
        worksheet['A1'] = "LOCKTITE INDIA PVT LTD"
        worksheet['A2'] = "EMPLOYEE LEAVE MANAGEMENT SYSTEM - ALL EMPLOYEES REPORT"
        worksheet['A3'] = f"Generated By: {generated_by} | Date: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
        
        # Auto-adjust column widths
        for col in worksheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    return buffer.getvalue()


def generate_individual_statement_excel(
    employee: Dict[str, Any],
    transactions: List[Dict[str, Any]],
    generated_by: str
) -> bytes:
    """Generates styled Excel file (.xlsx) for Individual Employee Leave Statement."""
    rows = []
    for tx in transactions:
        rows.append({
            "Transaction ID": f"LTX-{tx.get('id', 0):04d}",
            "From Date": tx.get("from_date"),
            "To Date": tx.get("to_date"),
            "Leave Type": tx.get("leave_type_name", tx.get("leave_type")),
            "Type": tx.get("transaction_type"),
            "Days": tx.get("days"),
            "Reason": tx.get("reason"),
            "Created By": tx.get("created_by"),
            "Created Date": tx.get("created_at")
        })
    df = pd.DataFrame(rows)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Leave Statement', startrow=8)
        worksheet = writer.sheets['Leave Statement']
        
        worksheet['A1'] = "LOCKTITE INDIA PVT LTD"
        worksheet['A2'] = "EMPLOYEE LEAVE STATEMENT"
        worksheet['A3'] = f"Employee No: {employee.get('employee_number')} | Name: {employee.get('employee_name')} | Department: {employee.get('department')}"
        worksheet['A4'] = f"Entitlement: {employee.get('leave_entitlement')} | Opening Balance: {employee.get('opening_balance')} | Taken: {employee.get('leave_taken')} | Current Balance: {employee.get('current_balance')}"
        worksheet['A5'] = f"Generated By: {generated_by} | Date: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"

        for col in worksheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    return buffer.getvalue()


def generate_csv_data(data: List[Dict[str, Any]], column_rename_map: Optional[Dict[str, str]] = None) -> str:
    """Converts a list of dicts to CSV string with optional column renaming."""
    df = pd.DataFrame(data)
    if column_rename_map:
        df = df.rename(columns=column_rename_map)
    return df.to_csv(index=False)

