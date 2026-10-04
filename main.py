"""
Main FastAPI Application for Locktite India Pvt Ltd - Employee Leave Management System.
Provides RESTful APIs, static file serving, and offline office management workflows.
"""

import os
import shutil
import sqlite3
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, Query, Request, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, Response, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

APP_URL = os.environ.get("APP_URL", "https://leave.locktiteindia.com").rstrip("/")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")
CORS_ORIGINS_RAW = os.environ.get("CORS_ORIGINS", "*")
CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()]

from app.database import (
    init_db, get_db_connection, DB_PATH, BACKUP_DIR, IS_POSTGRES,
    generate_next_employee_number, get_employee_balance_summary,
    hash_password, verify_password
)
from app.auth import (
    authenticate_user, create_session, invalidate_session,
    get_current_user, require_role, verify_admin_password
)
from app.models import (
    LoginRequest, ChangePasswordRequest, UserCreateRequest, UserUpdateRequest,
    EmployeeCreateRequest, EmployeeUpdateRequest, SensitiveActionRequest,
    LeaveEntryRequest, LeaveAdjustmentRequest, LeaveTypeCreateRequest, SettingUpdateRequest
)
from app.reports import (
    generate_individual_statement_pdf, generate_all_employees_summary_pdf,
    generate_all_employees_excel, generate_individual_statement_excel,
    generate_csv_data
)
from app.audit import log_audit

# Initialize database on startup
init_db()

app = FastAPI(
    title="Locktite India Pvt Ltd - Employee Leave Management System",
    description="Official Employee Leave Management System for Locktite India Pvt Ltd",
    version="1.0.0"
)

# Enable CORS for production and desktop clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if "*" not in CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def production_security_middleware(request: Request, call_next):
    # Enforce HTTPS redirect behind production reverse proxies
    proto = request.headers.get("x-forwarded-proto")
    if proto == "http" and ENVIRONMENT == "production":
        https_url = request.url.replace(scheme="https")
        return RedirectResponse(url=str(https_url), status_code=status.HTTP_301_MOVED_PERMANENTLY)

    response = await call_next(request)

    # Security HTTP headers
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https:; img-src 'self' data: blob: https:;"
    return response


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "API endpoint not found."})
    html_content = """<!DOCTYPE html>
    <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>404 - Page Not Found | Locktite India Pvt Ltd</title>
    <style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;background:#0f172a;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
    .card{background:#1e293b;padding:36px;border-radius:12px;text-align:center;max-width:480px;border:1px solid #334155;box-shadow:0 10px 25px rgba(0,0,0,0.5);}
    h1{color:#38bdf8;font-size:22px;margin:0 0 8px;}h2{font-size:16px;color:#e2e8f0;margin:0 0 16px;}p{color:#94a3b8;font-size:14px;line-height:1.6;}
    a{color:#fff;background:#2563eb;padding:10px 22px;text-decoration:none;border-radius:6px;display:inline-block;margin-top:20px;font-weight:600;font-size:14px;}
    a:hover{background:#1d4ed8;}</style></head>
    <body><div class="card"><h1>LOCKTITE INDIA PVT LTD</h1><h2>404 — Page Not Found</h2>
    <p>The requested page or resource could not be found. Please return to the official application dashboard.</p>
    <a href="/">Return to Dashboard</a></div></body></html>"""
    return HTMLResponse(status_code=404, content=html_content)


@app.exception_handler(500)
async def custom_500_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=500, content={"detail": "Internal server error. Please try again later or contact the administrator."})
    html_content = """<!DOCTYPE html>
    <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>500 - Server Error | Locktite India Pvt Ltd</title>
    <style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;background:#0f172a;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
    .card{background:#1e293b;padding:36px;border-radius:12px;text-align:center;max-width:480px;border:1px solid #334155;box-shadow:0 10px 25px rgba(0,0,0,0.5);}
    h1{color:#ef4444;font-size:22px;margin:0 0 8px;}h2{font-size:16px;color:#e2e8f0;margin:0 0 16px;}p{color:#94a3b8;font-size:14px;line-height:1.6;}
    a{color:#fff;background:#2563eb;padding:10px 22px;text-decoration:none;border-radius:6px;display:inline-block;margin-top:20px;font-weight:600;font-size:14px;}
    a:hover{background:#1d4ed8;}</style></head>
    <body><div class="card"><h1>LOCKTITE INDIA PVT LTD</h1><h2>500 — System Notice</h2>
    <p>Something went wrong on the server. Please try again later or contact your system administrator.</p>
    <a href="/">Return to Dashboard</a></div></body></html>"""
    return HTMLResponse(status_code=500, content=html_content)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------
# HEALTH CHECK & SEO ROUTES
# ---------------------------------------------------------
@app.get("/health")
@app.get("/api/health")
async def health_check():
    db_type = "PostgreSQL" if IS_POSTGRES else "SQLite"
    db_status = "connected"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        conn.close()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if "error" not in db_status else "degraded",
        "company": "Locktite India Pvt Ltd",
        "service": "Employee Leave Management System",
        "database": {
            "type": db_type,
            "status": db_status
        },
        "environment": ENVIRONMENT,
        "app_url": APP_URL,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/robots.txt", response_class=Response)
async def robots_txt():
    content = "User-agent: *\nDisallow: /api/\nDisallow: /admin\nAllow: /\n"
    return Response(content=content, media_type="text/plain")


# ---------------------------------------------------------
# ROOT & UI ROUTE
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Locktite India Pvt Ltd - Leave Management System</h1><p>UI loading...</p>"


# ---------------------------------------------------------
# AUTHENTICATION ROUTES
# ---------------------------------------------------------
@app.post("/api/auth/login")
async def login(req: LoginRequest, request: Request):
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip() or
        (request.client.host if request.client else "unknown")
    )
    user = authenticate_user(req.user_id, req.password, client_ip=client_ip)
    if not user:
        log_audit(req.user_id, None, "LOGIN_FAILED", "SECURITY", f"Failed login attempt from IP {client_ip}.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid User ID or Password. Please try again."
        )

    token = create_session(user)
    log_audit(user["user_id"], user["full_name"], "LOGIN_SUCCESS", "SECURITY", f"User logged in with role {user['role']} from IP {client_ip}.")

    return {
        "success": True,
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "role": user["role"]
        },
        "company_name": "Locktite India Pvt Ltd",
        "app_url": APP_URL
    }



@app.post("/api/auth/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    invalidate_session(current_user["token"])
    log_audit(current_user["user_id"], current_user["full_name"], "LOGOUT", "SECURITY", "User logged out.")
    return {"success": True, "message": "Logged out successfully."}


@app.get("/api/auth/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {"user": current_user, "company_name": "Locktite India Pvt Ltd"}


@app.post("/api/auth/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt FROM users WHERE user_id = ?;", (current_user["user_id"],))
    row = cursor.fetchone()

    if not row or not verify_password(req.current_password, row["salt"], row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    new_hash, new_salt = hash_password(req.new_password)
    cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE user_id = ?;", (new_hash, new_salt, current_user["user_id"]))
    conn.commit()
    conn.close()

    log_audit(current_user["user_id"], current_user["full_name"], "CHANGE_PASSWORD", "SECURITY", "User changed their password.")
    return {"success": True, "message": "Password changed successfully."}


# ---------------------------------------------------------
# DASHBOARD METRICS
# ---------------------------------------------------------
@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Total Employees & Active Employees
    cursor.execute("SELECT COUNT(*) FROM employees;")
    total_employees = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM employees WHERE status = 'Active';")
    active_employees = cursor.fetchone()[0]

    # 2. Employees on leave today
    today_str = date.today().strftime("%Y-%m-%d")
    # For today, check active ADD leave transactions where today falls within from_date and to_date
    cursor.execute("""
    SELECT DISTINCT e.employee_number, e.employee_name, e.department, lt.name as leave_type, t.from_date, t.to_date
    FROM leave_transactions t
    JOIN employees e ON t.employee_id = e.id
    JOIN leave_types lt ON t.leave_type_id = lt.id
    WHERE t.transaction_type = 'ADD'
      AND ? BETWEEN t.from_date AND t.to_date
      AND e.status = 'Active';
    """, (today_str,))
    on_leave_today_rows = cursor.fetchall()
    on_leave_today_list = [dict(r) for r in on_leave_today_rows]
    on_leave_today_count = len(on_leave_today_list)

    # 3. Total Leave Taken across organization
    cursor.execute("""
    SELECT COALESCE(SUM(CASE WHEN transaction_type = 'ADD' THEN days WHEN transaction_type = 'LESS' THEN -days ELSE 0 END), 0)
    FROM leave_transactions;
    """)
    total_leave_taken = float(cursor.fetchone()[0])

    # 4. Employees with low leave balance (<= threshold)
    cursor.execute("SELECT value FROM settings WHERE key = 'low_balance_threshold';")
    thresh_row = cursor.fetchone()
    threshold = float(thresh_row[0]) if thresh_row else 3.0

    cursor.execute("""
    SELECT 
        e.id, e.employee_number, e.employee_name, e.department, e.designation,
        e.leave_entitlement, e.opening_balance,
        COALESCE(SUM(CASE WHEN t.transaction_type = 'ADD' THEN t.days WHEN t.transaction_type = 'LESS' THEN -t.days ELSE 0 END), 0) as taken
    FROM employees e
    LEFT JOIN leave_transactions t ON e.id = t.employee_id
    WHERE e.status = 'Active'
    GROUP BY e.id
    HAVING (e.opening_balance - taken) <= ?;
    """, (threshold,))
    low_balance_rows = cursor.fetchall()
    low_balance_list = []
    for r in low_balance_rows:
        bal = float(r["opening_balance"]) - float(r["taken"])
        low_balance_list.append({
            "id": r["id"],
            "employee_number": r["employee_number"],
            "employee_name": r["employee_name"],
            "department": r["department"],
            "designation": r["designation"],
            "opening_balance": float(r["opening_balance"]),
            "leave_taken": float(r["taken"]),
            "current_balance": bal
        })

    # 5. Recent 8 transactions
    cursor.execute("""
    SELECT 
        t.id, t.transaction_type, t.from_date, t.to_date, t.days, t.reason, t.created_by, t.created_at,
        e.employee_number, e.employee_name, e.department,
        lt.name as leave_type_name
    FROM leave_transactions t
    JOIN employees e ON t.employee_id = e.id
    JOIN leave_types lt ON t.leave_type_id = lt.id
    ORDER BY t.id DESC
    LIMIT 8;
    """)
    recent_txs = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "company_name": "Locktite India Pvt Ltd",
        "current_date": today_str,
        "total_employees": total_employees,
        "active_employees": active_employees,
        "employees_on_leave_today": on_leave_today_count,
        "on_leave_today_list": on_leave_today_list,
        "total_leave_taken": total_leave_taken,
        "low_balance_count": len(low_balance_list),
        "low_balance_employees": low_balance_list,
        "recent_transactions": recent_txs,
        "low_balance_threshold": threshold
    }


# ---------------------------------------------------------
# MASTER — EMPLOYEE MANAGEMENT
# ---------------------------------------------------------
@app.get("/api/employees/next-number")
async def get_next_employee_number(current_user: Dict[str, Any] = Depends(get_current_user)):
    next_num = generate_next_employee_number()
    return {"next_employee_number": next_num}


@app.get("/api/employees")
async def list_employees(
    query: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = """
    SELECT 
        e.id, e.employee_number, e.employee_name, e.department, e.designation,
        e.date_of_joining, e.mobile, e.email, e.address, e.date_of_birth,
        e.leave_entitlement, e.opening_balance, e.status, e.remarks, e.created_at,
        COALESCE(SUM(CASE WHEN t.transaction_type = 'ADD' THEN t.days WHEN t.transaction_type = 'LESS' THEN -t.days ELSE 0 END), 0) as leave_taken
    FROM employees e
    LEFT JOIN leave_transactions t ON e.id = t.employee_id
    WHERE 1=1
    """
    params = []

    if query:
        q_wild = f"%{query.strip()}%"
        sql += " AND (e.employee_number LIKE ? OR e.employee_name LIKE ? OR e.department LIKE ?)"
        params.extend([q_wild, q_wild, q_wild])

    if department and department != "All":
        sql += " AND e.department = ?"
        params.append(department)

    if status and status != "All":
        sql += " AND e.status = ?"
        params.append(status)

    sql += " GROUP BY e.id ORDER BY e.employee_number ASC;"

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    employees = []
    for r in rows:
        d = dict(r)
        d["leave_entitlement"] = float(d["leave_entitlement"])
        d["opening_balance"] = float(d["opening_balance"])
        d["leave_taken"] = float(d["leave_taken"])
        d["current_balance"] = d["opening_balance"] - d["leave_taken"]
        employees.append(d)

    return {"employees": employees}


@app.post("/api/employees")
async def create_employee(
    req: EmployeeCreateRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN", "ENTRY USER"]))
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Automatically generate the next employee number
    emp_number = generate_next_employee_number()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor.execute("""
        INSERT INTO employees (
            employee_number, employee_name, department, designation, date_of_joining,
            mobile, email, address, date_of_birth, leave_entitlement, opening_balance,
            status, remarks, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            emp_number, req.employee_name.strip(), req.department.strip(), req.designation.strip(),
            req.date_of_joining, req.mobile, req.email, req.address, req.date_of_birth,
            req.leave_entitlement, req.opening_balance, req.status, req.remarks, now_str, now_str
        ))
        emp_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")

    conn.close()

    log_audit(
        current_user["user_id"], current_user["full_name"], "ADD_EMPLOYEE", "MASTER",
        f"Created employee {emp_number} ({req.employee_name}) with entitlement {req.leave_entitlement} days.",
        employee_number=emp_number
    )

    return {
        "success": True,
        "message": f"Employee {emp_number} ({req.employee_name}) created successfully.",
        "employee_id": emp_id,
        "employee_number": emp_number
    }


@app.get("/api/employees/{id}")
async def get_employee_details(
    id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id = ?;", (id,))
    emp_row = cursor.fetchone()

    if not emp_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp_data = dict(emp_row)

    # Calculate leave taken & balance
    cursor.execute("""
    SELECT COALESCE(SUM(CASE WHEN transaction_type = 'ADD' THEN days WHEN transaction_type = 'LESS' THEN -days ELSE 0 END), 0)
    FROM leave_transactions WHERE employee_id = ?;
    """, (id,))
    leave_taken = float(cursor.fetchone()[0])
    emp_data["leave_taken"] = leave_taken
    emp_data["current_balance"] = float(emp_data["opening_balance"]) - leave_taken

    # Get employee leave transactions
    cursor.execute("""
    SELECT 
        t.id, t.transaction_type, t.from_date, t.to_date, t.days, t.reason,
        t.created_by, t.created_at, lt.name as leave_type_name
    FROM leave_transactions t
    JOIN leave_types lt ON t.leave_type_id = lt.id
    WHERE t.employee_id = ?
    ORDER BY t.from_date DESC, t.id DESC;
    """, (id,))
    transactions = [dict(r) for r in cursor.fetchall()]
    emp_data["transactions"] = transactions

    conn.close()
    return {"employee": emp_data}


@app.put("/api/employees/{id}")
async def update_employee(
    id: int,
    req: EmployeeUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id = ?;", (id,))
    emp_row = cursor.fetchone()

    if not emp_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Employee not found.")

    old_data = dict(emp_row)

    # Check if sensitive fields (leave_entitlement, opening_balance) are modified
    is_entitlement_changed = (
        (req.leave_entitlement is not None and float(req.leave_entitlement) != float(old_data["leave_entitlement"])) or
        (req.opening_balance is not None and float(req.opening_balance) != float(old_data["opening_balance"]))
    )

    if is_entitlement_changed:
        if not req.confirmation_password:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="Changing Leave Entitlement or Opening Balance is sensitive and requires your administrator password."
            )
        if not verify_admin_password(current_user["user_id"], req.confirmation_password):
            conn.close()
            raise HTTPException(status_code=403, detail="Invalid administrator confirmation password.")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build dynamic update query
    update_fields = []
    params = []

    fields_map = {
        "employee_name": req.employee_name,
        "department": req.department,
        "designation": req.designation,
        "date_of_joining": req.date_of_joining,
        "mobile": req.mobile,
        "email": req.email,
        "address": req.address,
        "date_of_birth": req.date_of_birth,
        "leave_entitlement": req.leave_entitlement,
        "opening_balance": req.opening_balance,
        "status": req.status,
        "remarks": req.remarks
    }

    for col, val in fields_map.items():
        if val is not None:
            update_fields.append(f"{col} = ?")
            params.append(val)

    update_fields.append("updated_at = ?")
    params.append(now_str)
    params.append(id)

    query = f"UPDATE employees SET {', '.join(update_fields)} WHERE id = ?;"
    cursor.execute(query, params)
    conn.commit()
    conn.close()

    emp_number = old_data["employee_number"]
    log_audit(
        current_user["user_id"], current_user["full_name"], "EDIT_EMPLOYEE", "MASTER",
        f"Updated details for employee {emp_number} ({old_data['employee_name']}).",
        employee_number=emp_number
    )

    return {"success": True, "message": f"Employee {emp_number} updated successfully."}


@app.post("/api/employees/{id}/toggle-status")
async def toggle_employee_status(
    id: int,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, employee_number, employee_name, status FROM employees WHERE id = ?;", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Employee not found.")

    new_status = "Inactive" if row["status"] == "Active" else "Active"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE employees SET status = ?, updated_at = ? WHERE id = ?;", (new_status, now_str, id))
    conn.commit()
    conn.close()

    log_audit(
        current_user["user_id"], current_user["full_name"], "CHANGE_STATUS", "MASTER",
        f"Changed status of {row['employee_number']} ({row['employee_name']}) to {new_status}.",
        employee_number=row["employee_number"]
    )

    return {"success": True, "message": f"Employee {row['employee_number']} is now {new_status}.", "status": new_status}


@app.delete("/api/employees/{id}")
async def delete_employee(
    id: int,
    req: SensitiveActionRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    # Verify administrator password
    if not verify_admin_password(current_user["user_id"], req.password):
        raise HTTPException(status_code=403, detail="Invalid administrator confirmation password.")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT employee_number, employee_name FROM employees WHERE id = ?;", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp_number = row["employee_number"]
    emp_name = row["employee_name"]

    # Check if leave records exist
    cursor.execute("SELECT COUNT(*) FROM leave_transactions WHERE employee_id = ?;", (id,))
    tx_count = cursor.fetchone()[0]

    if tx_count > 0:
        # Prompt: "Employees should preferably be deactivated instead of permanently deleted."
        # If deleted, must handle or block
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete employee {emp_number} because {tx_count} leave transactions exist. Please deactivate this employee instead to preserve official audit records."
        )

    cursor.execute("DELETE FROM employees WHERE id = ?;", (id,))
    conn.commit()
    conn.close()

    log_audit(
        current_user["user_id"], current_user["full_name"], "DELETE_EMPLOYEE", "MASTER",
        f"Permanently deleted employee {emp_number} ({emp_name}). Reason: {req.reason or 'Not specified'}.",
        employee_number=emp_number
    )

    return {"success": True, "message": f"Employee {emp_number} deleted successfully."}


# ---------------------------------------------------------
# ENTRY — LEAVE MANAGEMENT (ADD & LESS)
# ---------------------------------------------------------
@app.get("/api/leave/types")
async def get_leave_types(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, active FROM leave_types WHERE active = 1 ORDER BY name ASC;")
    types = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"leave_types": types}


@app.get("/api/leave/balance/{employee_id}")
async def get_employee_balance(
    employee_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    summary = get_employee_balance_summary(employee_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Employee not found.")
    return {"balance_summary": summary}


@app.post("/api/leave/entry")
async def add_leave(
    req: LeaveEntryRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN", "ENTRY USER"]))
):
    """
    ADD LEAVE function:
    - Validates from_date <= to_date
    - Validates days > 0
    - Validates employee exists & is Active
    - Validates balance sufficiency
    - Saves transaction permanently
    - Logs to audit trail
    """
    if req.from_date > req.to_date:
        raise HTTPException(status_code=400, detail="From Date cannot be after To Date.")

    if req.days <= 0:
        raise HTTPException(status_code=400, detail="Number of leave days must be greater than zero.")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, employee_number, employee_name, status, opening_balance FROM employees WHERE id = ?;", (req.employee_id,))
    emp_row = cursor.fetchone()
    if not emp_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Employee not found.")

    if emp_row["status"] != "Active":
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Employee {emp_row['employee_number']} is currently Inactive. Inactive employees cannot receive new leave."
        )

    # Check leave balance
    cursor.execute("""
    SELECT COALESCE(SUM(CASE WHEN transaction_type = 'ADD' THEN days WHEN transaction_type = 'LESS' THEN -days ELSE 0 END), 0)
    FROM leave_transactions WHERE employee_id = ?;
    """, (req.employee_id,))
    taken = float(cursor.fetchone()[0])
    opening = float(emp_row["opening_balance"])
    available_balance = opening - taken

    # Check setting: allow negative balance
    cursor.execute("SELECT value FROM settings WHERE key = 'allow_negative_balance';")
    allow_neg_row = cursor.fetchone()
    allow_negative = (allow_neg_row and allow_neg_row[0] == "1")

    if (available_balance - req.days) < 0 and not (allow_negative or (req.override_balance_check and current_user["role"] == "ADMIN")):
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Leave balance is insufficient. Available balance: {available_balance:.1f} days. Requested: {req.days:.1f} days."
        )

    # Check for potential exact duplicate entry
    cursor.execute("""
    SELECT id FROM leave_transactions
    WHERE employee_id = ? AND leave_type_id = ? AND from_date = ? AND to_date = ? AND transaction_type = 'ADD';
    """, (req.employee_id, req.leave_type_id, req.from_date, req.to_date))
    duplicate = cursor.fetchone()
    if duplicate:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"An identical leave entry (LTX-{duplicate[0]:04d}) already exists for this employee for these exact dates."
        )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO leave_transactions (
        employee_id, leave_type_id, transaction_type, from_date, to_date, days,
        reason, created_by, created_at, updated_by, updated_at
    ) VALUES (?, ?, 'ADD', ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        req.employee_id, req.leave_type_id, req.from_date, req.to_date, req.days,
        req.reason, current_user["user_id"], now_str, current_user["user_id"], now_str
    ))
    tx_id = cursor.lastrowid
    conn.commit()

    # Get leave type name for log
    cursor.execute("SELECT name FROM leave_types WHERE id = ?;", (req.leave_type_id,))
    lt_name = cursor.fetchone()[0]
    conn.close()

    new_balance = available_balance - req.days
    log_audit(
        current_user["user_id"], current_user["full_name"], "ADD_LEAVE", "ENTRY",
        f"Added {req.days:.1f} days {lt_name} for {emp_row['employee_number']} ({emp_row['employee_name']}) from {req.from_date} to {req.to_date}. New Balance: {new_balance:.1f} days.",
        employee_number=emp_row["employee_number"]
    )

    return {
        "success": True,
        "message": f"Leave entry saved successfully for {emp_row['employee_name']} ({emp_row['employee_number']}).",
        "transaction_id": f"LTX-{tx_id:04d}",
        "new_balance": new_balance
    }


@app.post("/api/leave/adjustment")
async def adjust_leave(
    req: LeaveAdjustmentRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN", "ENTRY USER"]))
):
    """
    LESS / CANCEL LEAVE function:
    - Creates a LESS transaction (maintains full transaction history)
    - Validates days > 0
    - Credits back to employee balance
    - Records user, reason, timestamp
    """
    if req.from_date > req.to_date:
        raise HTTPException(status_code=400, detail="From Date cannot be after To Date.")

    if req.days <= 0:
        raise HTTPException(status_code=400, detail="Number of leave days must be greater than zero.")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, employee_number, employee_name, opening_balance FROM employees WHERE id = ?;", (req.employee_id,))
    emp_row = cursor.fetchone()
    if not emp_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Employee not found.")

    # Calculate current taken
    cursor.execute("""
    SELECT COALESCE(SUM(CASE WHEN transaction_type = 'ADD' THEN days WHEN transaction_type = 'LESS' THEN -days ELSE 0 END), 0)
    FROM leave_transactions WHERE employee_id = ?;
    """, (req.employee_id,))
    current_taken = float(cursor.fetchone()[0])

    if req.days > current_taken:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel/less {req.days:.1f} days. Total leave taken by employee is currently {current_taken:.1f} days."
        )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO leave_transactions (
        employee_id, leave_type_id, transaction_type, from_date, to_date, days,
        reason, reference_tx_id, created_by, created_at, updated_by, updated_at
    ) VALUES (?, ?, 'LESS', ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        req.employee_id, req.leave_type_id, req.from_date, req.to_date, req.days,
        req.reason, req.reference_tx_id, current_user["user_id"], now_str, current_user["user_id"], now_str
    ))
    tx_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT name FROM leave_types WHERE id = ?;", (req.leave_type_id,))
    lt_name = cursor.fetchone()[0]
    conn.close()

    new_taken = current_taken - req.days
    new_balance = float(emp_row["opening_balance"]) - new_taken

    log_audit(
        current_user["user_id"], current_user["full_name"], "LESS_LEAVE", "ADJUSTMENT",
        f"Adjusted/Cancelled {req.days:.1f} days {lt_name} for {emp_row['employee_number']} ({emp_row['employee_name']}). Reason: {req.reason}. New Balance: {new_balance:.1f} days.",
        employee_number=emp_row["employee_number"]
    )

    return {
        "success": True,
        "message": f"Leave adjustment completed successfully for {emp_row['employee_name']} ({emp_row['employee_number']}).",
        "transaction_id": f"LTX-{tx_id:04d}",
        "new_balance": new_balance,
        "new_taken": new_taken
    }


@app.get("/api/leave/history")
async def get_leave_history(
    employee_id: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    leave_type_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = """
    SELECT 
        t.id, t.employee_id, t.transaction_type, t.from_date, t.to_date, t.days, t.reason,
        t.reference_tx_id, t.created_by, t.created_at,
        e.employee_number, e.employee_name, e.department,
        lt.name as leave_type_name
    FROM leave_transactions t
    JOIN employees e ON t.employee_id = e.id
    JOIN leave_types lt ON t.leave_type_id = lt.id
    WHERE 1=1
    """
    params = []

    if employee_id:
        sql += " AND t.employee_id = ?"
        params.append(employee_id)

    if from_date:
        sql += " AND t.from_date >= ?"
        params.append(from_date)

    if to_date:
        sql += " AND t.to_date <= ?"
        params.append(to_date)

    if transaction_type and transaction_type != "All":
        sql += " AND t.transaction_type = ?"
        params.append(transaction_type)

    if leave_type_id and leave_type_id > 0:
        sql += " AND t.leave_type_id = ?"
        params.append(leave_type_id)

    sql += " ORDER BY t.from_date DESC, t.id DESC;"

    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {"history": rows}


# ---------------------------------------------------------
# REPORTS MODULE
# ---------------------------------------------------------
def _fetch_all_employees_summary(department: str = "All", status: str = "All"):
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = """
    SELECT 
        e.id, e.employee_number, e.employee_name, e.department, e.designation,
        e.date_of_joining, e.mobile, e.email, e.leave_entitlement, e.opening_balance, e.status,
        COALESCE(SUM(CASE WHEN t.transaction_type = 'ADD' THEN t.days WHEN t.transaction_type = 'LESS' THEN -t.days ELSE 0 END), 0) as leave_taken
    FROM employees e
    LEFT JOIN leave_transactions t ON e.id = t.employee_id
    WHERE 1=1
    """
    params = []
    if department and department != "All":
        sql += " AND e.department = ?"
        params.append(department)
    if status and status != "All":
        sql += " AND e.status = ?"
        params.append(status)

    sql += " GROUP BY e.id ORDER BY e.employee_number ASC;"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    summary = []
    for r in rows:
        d = dict(r)
        d["leave_entitlement"] = float(d["leave_entitlement"])
        d["opening_balance"] = float(d["opening_balance"])
        d["leave_taken"] = float(d["leave_taken"])
        d["current_balance"] = d["opening_balance"] - d["leave_taken"]
        summary.append(d)
    return summary


@app.get("/api/reports/all-employees")
async def report_all_employees(
    department: str = Query("All"),
    status: str = Query("All"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    data = _fetch_all_employees_summary(department, status)
    return {
        "company_name": "Locktite India Pvt Ltd",
        "title": "All Employees Leave Summary Report",
        "department": department,
        "status": status,
        "data": data
    }


@app.get("/api/reports/all-employees/pdf")
async def report_all_employees_pdf(
    department: str = Query("All"),
    status: str = Query("All"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    data = _fetch_all_employees_summary(department, status)
    pdf_bytes = generate_all_employees_summary_pdf(
        summary_data=data,
        generated_by=f"{current_user['full_name']} ({current_user['role']})",
        department_filter=department,
        status_filter=status
    )
    filename = f"Locktite_Leave_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    log_audit(current_user["user_id"], current_user["full_name"], "EXPORT_PDF", "REPORTS", "Exported All Employees Leave Summary PDF.")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/reports/all-employees/excel")
async def report_all_employees_excel(
    department: str = Query("All"),
    status: str = Query("All"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    data = _fetch_all_employees_summary(department, status)
    excel_bytes = generate_all_employees_excel(
        summary_data=data,
        generated_by=f"{current_user['full_name']} ({current_user['role']})"
    )
    filename = f"Locktite_Leave_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    log_audit(current_user["user_id"], current_user["full_name"], "EXPORT_EXCEL", "REPORTS", "Exported All Employees Leave Summary Excel.")
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/reports/all-employees/csv")
async def report_all_employees_csv(
    department: str = Query("All"),
    status: str = Query("All"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    data = _fetch_all_employees_summary(department, status)
    column_map = {
        "employee_number": "Employee No",
        "employee_name": "Employee Name",
        "department": "Department",
        "designation": "Designation",
        "date_of_joining": "Joining Date",
        "mobile": "Contact Mobile",
        "email": "Email",
        "leave_entitlement": "Leave Entitlement",
        "opening_balance": "Opening Balance",
        "status": "Status",
        "leave_taken": "Leave Taken",
        "current_balance": "Current Balance"
    }
    csv_text = generate_csv_data(data, column_rename_map=column_map)
    filename = f"Locktite_Leave_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(content=csv_text, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})



def _fetch_individual_statement(employee_id: int, from_date: Optional[str] = None, to_date: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM employees WHERE id = ?;", (employee_id,))
    emp_row = cursor.fetchone()
    if not emp_row:
        conn.close()
        return None, None

    emp = dict(emp_row)

    # Balance summary
    cursor.execute("""
    SELECT COALESCE(SUM(CASE WHEN transaction_type = 'ADD' THEN days WHEN transaction_type = 'LESS' THEN -days ELSE 0 END), 0)
    FROM leave_transactions WHERE employee_id = ?;
    """, (employee_id,))
    emp["leave_taken"] = float(cursor.fetchone()[0])
    emp["current_balance"] = float(emp["opening_balance"]) - emp["leave_taken"]

    # Filtered transactions
    sql = """
    SELECT 
        t.id, t.transaction_type, t.from_date, t.to_date, t.days, t.reason,
        t.created_by, t.created_at, lt.name as leave_type_name
    FROM leave_transactions t
    JOIN leave_types lt ON t.leave_type_id = lt.id
    WHERE t.employee_id = ?
    """
    params = [employee_id]
    if from_date:
        sql += " AND t.from_date >= ?"
        params.append(from_date)
    if to_date:
        sql += " AND t.to_date <= ?"
        params.append(to_date)

    sql += " ORDER BY t.from_date ASC, t.id ASC;"
    cursor.execute(sql, params)
    txs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return emp, txs


@app.get("/api/reports/individual/{employee_id}")
async def report_individual(
    employee_id: int,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    emp, txs = _fetch_individual_statement(employee_id, from_date, to_date)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    return {
        "company_name": "Locktite India Pvt Ltd",
        "title": "Employee Leave Statement",
        "employee": emp,
        "transactions": txs
    }


@app.get("/api/reports/individual/{employee_id}/pdf")
async def report_individual_pdf(
    employee_id: int,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    emp, txs = _fetch_individual_statement(employee_id, from_date, to_date)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    period = f"{from_date or 'Start'} to {to_date or 'Present'}" if (from_date or to_date) else "All Time"
    pdf_bytes = generate_individual_statement_pdf(
        employee=emp,
        transactions=txs,
        generated_by=f"{current_user['full_name']} ({current_user['role']})",
        date_range=period
    )
    filename = f"Locktite_Statement_{emp['employee_number']}_{datetime.now().strftime('%Y%m%d')}.pdf"
    log_audit(
        current_user["user_id"], current_user["full_name"], "EXPORT_PDF", "REPORTS",
        f"Exported leave statement PDF for {emp['employee_number']}.",
        employee_number=emp["employee_number"]
    )
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/reports/individual/{employee_id}/excel")
async def report_individual_excel(
    employee_id: int,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    emp, txs = _fetch_individual_statement(employee_id, from_date, to_date)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    excel_bytes = generate_individual_statement_excel(
        employee=emp,
        transactions=txs,
        generated_by=f"{current_user['full_name']} ({current_user['role']})"
    )
    filename = f"Locktite_Statement_{emp['employee_number']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ---------------------------------------------------------
# ADMINISTRATION & AUDIT & BACKUP
# ---------------------------------------------------------
@app.get("/api/admin/users")
async def list_users(current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, full_name, role, active, created_at FROM users ORDER BY id ASC;")
    users = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"users": users}


@app.post("/api/admin/users")
async def create_user(
    req: UserCreateRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    h, s = hash_password(req.password)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor.execute("""
        INSERT INTO users (user_id, full_name, password_hash, salt, role, active, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?);
        """, (req.user_id.strip(), req.full_name.strip(), h, s, req.role, now_str))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="User ID already exists. Please choose another.")

    conn.close()
    log_audit(current_user["user_id"], current_user["full_name"], "CREATE_USER", "ADMINISTRATION", f"Created system user {req.user_id} ({req.role}).")
    return {"success": True, "message": f"User {req.user_id} created successfully."}


@app.put("/api/admin/users/{id}")
async def update_user(
    id: int,
    req: UserUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, full_name FROM users WHERE id = ?;", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found.")

    target_user_id = row["user_id"]

    updates = []
    params = []
    if req.full_name:
        updates.append("full_name = ?")
        params.append(req.full_name)
    if req.role:
        updates.append("role = ?")
        params.append(req.role)
    if req.active is not None:
        updates.append("active = ?")
        params.append(1 if req.active else 0)
    if req.new_password:
        h, s = hash_password(req.new_password)
        updates.append("password_hash = ?")
        params.append(h)
        updates.append("salt = ?")
        params.append(s)

    if updates:
        params.append(id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?;", params)
        conn.commit()

    conn.close()
    log_audit(current_user["user_id"], current_user["full_name"], "UPDATE_USER", "ADMINISTRATION", f"Updated user settings for {target_user_id}.")
    return {"success": True, "message": f"User {target_user_id} updated successfully."}


@app.get("/api/admin/leave-types")
async def list_all_leave_types(current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, active FROM leave_types ORDER BY id ASC;")
    types = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"leave_types": types}


@app.post("/api/admin/leave-types")
async def create_leave_type(
    req: LeaveTypeCreateRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO leave_types (name, description, active) VALUES (?, ?, ?);", (req.name.strip(), req.description, 1 if req.active else 0))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Leave type with this name already exists.")
    conn.close()
    log_audit(current_user["user_id"], current_user["full_name"], "CREATE_LEAVE_TYPE", "ADMINISTRATION", f"Created leave type '{req.name}'.")
    return {"success": True, "message": f"Leave type '{req.name}' created."}


@app.put("/api/admin/leave-types/{id}")
async def update_leave_type(
    id: int,
    req: LeaveTypeCreateRequest,
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leave_types SET name = ?, description = ?, active = ? WHERE id = ?;", (req.name.strip(), req.description, 1 if req.active else 0, id))
    conn.commit()
    conn.close()
    log_audit(current_user["user_id"], current_user["full_name"], "UPDATE_LEAVE_TYPE", "ADMINISTRATION", f"Updated leave type #{id} to '{req.name}'.")
    return {"success": True, "message": "Leave type updated successfully."}


@app.get("/api/admin/audit-logs")
async def get_audit_logs(
    module: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "SELECT id, user_id, user_name, action, module, employee_number, description, created_at FROM audit_logs WHERE 1=1"
    params = []
    if module and module != "All":
        sql += " AND module = ?"
        params.append(module)
    if user_id and user_id != "All":
        sql += " AND user_id = ?"
        params.append(user_id)

    sql += " ORDER BY id DESC LIMIT ?;"
    params.append(limit)

    cursor.execute(sql, params)
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"audit_logs": logs}


@app.get("/api/admin/audit-logs/csv")
async def export_audit_logs_csv(current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, created_at, user_id, user_name, module, action, employee_number, description FROM audit_logs ORDER BY id DESC;")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    csv_data = generate_csv_data(rows)
    filename = f"Locktite_Audit_Log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ---------------------------------------------------------
# BACKUP & RESTORE
# ---------------------------------------------------------
@app.get("/api/admin/backups")
async def list_backups(current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))):
    files = []
    if os.path.exists(BACKUP_DIR):
        for f in os.listdir(BACKUP_DIR):
            if f.endswith(".db") or f.endswith(".json"):
                p = os.path.join(BACKUP_DIR, f)
                size_kb = round(os.path.getsize(p) / 1024, 2)
                mtime = datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S")
                files.append({"filename": f, "size_kb": size_kb, "created_at": mtime})

    files.sort(key=lambda x: x["created_at"], reverse=True)
    return {"backups": files, "database_mode": "PostgreSQL" if IS_POSTGRES else "SQLite"}


@app.post("/api/admin/backup")
async def create_backup(current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))):
    """
    Creates a verified, transaction-safe backup of the database (JSON snapshot for PostgreSQL, online backup API for SQLite).
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if IS_POSTGRES:
        import json
        backup_filename = f"locktite_pg_backup_{timestamp}.json"
        backup_filepath = os.path.join(BACKUP_DIR, backup_filename)
        conn = get_db_connection()
        cursor = conn.cursor()
        backup_data = {}
        tables = ["users", "employees", "leave_types", "leave_transactions", "audit_logs", "settings"]
        for tbl in tables:
            cursor.execute(f"SELECT * FROM {tbl};")
            backup_data[tbl] = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        with open(backup_filepath, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, default=str, indent=2)
            
        size_kb = round(os.path.getsize(backup_filepath) / 1024, 2)
        log_audit(
            current_user["user_id"], current_user["full_name"], "BACKUP_DATABASE", "ADMINISTRATION",
            f"Created PostgreSQL data snapshot '{backup_filename}' ({size_kb} KB)."
        )
        return {
            "success": True,
            "message": f"Database snapshot '{backup_filename}' created successfully.",
            "filename": backup_filename,
            "size_kb": size_kb
        }

    backup_filename = f"locktite_leave_backup_{timestamp}.db"
    backup_filepath = os.path.join(BACKUP_DIR, backup_filename)

    src_conn = get_db_connection()
    dst_conn = sqlite3.connect(backup_filepath)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()

    size_kb = round(os.path.getsize(backup_filepath) / 1024, 2)
    log_audit(
        current_user["user_id"], current_user["full_name"], "BACKUP_DATABASE", "ADMINISTRATION",
        f"Created SQLite database backup '{backup_filename}' ({size_kb} KB)."
    )

    return {
        "success": True,
        "message": f"Database backup '{backup_filename}' created successfully.",
        "filename": backup_filename,
        "size_kb": size_kb
    }


@app.get("/api/admin/backup/download/{filename}")
async def download_backup(
    filename: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    file_path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Backup file not found.")

    media_type = "application/json" if filename.endswith(".json") else "application/x-sqlite3"
    return FileResponse(file_path, filename=filename, media_type=media_type)


@app.post("/api/admin/restore")
async def restore_database(
    filename: str = Query(...),
    password: str = Query(...),
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    """
    Restores the database from a backup file.
    Strictly verifies admin password.
    Creates an automatic safety backup of current state before restoring.
    """
    if not verify_admin_password(current_user["user_id"], password):
        raise HTTPException(status_code=403, detail="Invalid administrator password. Database restore aborted.")

    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    backup_filepath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(backup_filepath):
        raise HTTPException(status_code=404, detail="Specified backup file not found.")

    if IS_POSTGRES:
        raise HTTPException(
            status_code=400,
            detail="In production managed PostgreSQL, database restores are managed via Cloud Console point-in-time recovery to maintain strict replica integrity."
        )

    # 1. Take safety snapshot of current database
    pre_restore_snapshot = os.path.join(BACKUP_DIR, f"pre_restore_safety_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    curr_conn = get_db_connection()
    snap_conn = sqlite3.connect(pre_restore_snapshot)
    curr_conn.backup(snap_conn)
    snap_conn.close()
    curr_conn.close()

    # 2. Restore from target backup
    restore_src = sqlite3.connect(backup_filepath)
    main_dst = get_db_connection()
    restore_src.backup(main_dst)
    main_dst.close()
    restore_src.close()

    log_audit(
        current_user["user_id"], current_user["full_name"], "RESTORE_DATABASE", "ADMINISTRATION",
        f"Restored database from backup file '{filename}'. Pre-restore safety copy saved as '{os.path.basename(pre_restore_snapshot)}'."
    )

    return {
        "success": True,
        "message": f"Database successfully restored from '{filename}'. Safety snapshot preserved."
    }



# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------
@app.get("/api/admin/settings")
async def get_settings(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings;")
    settings = {r["key"]: r["value"] for r in cursor.fetchall()}
    conn.close()
    return {"settings": settings}


@app.post("/api/admin/settings")
async def update_settings(
    settings_dict: Dict[str, str],
    current_user: Dict[str, Any] = Depends(require_role(["ADMIN"]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    for k, v in settings_dict.items():
        cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?;", (k, str(v), str(v)))
    conn.commit()
    conn.close()
    log_audit(current_user["user_id"], current_user["full_name"], "UPDATE_SETTINGS", "ADMINISTRATION", "Updated system settings configuration.")
    return {"success": True, "message": "Settings saved successfully."}
