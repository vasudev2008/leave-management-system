"""
Database module for Locktite India Pvt Ltd - Employee Leave Management System.
Supports both PostgreSQL (for production managed cloud deployment) and SQLite (for local/offline use).
Uses connection pooling, foreign keys, transaction handling, and auto-seeding.
"""

import os
import re
import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "locktite_leave.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_POSTGRES = DATABASE_URL.startswith("postgresql://")

# PostgreSQL connection pool if configured
PG_POOL = None
if IS_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
        from psycopg2 import pool
        PG_POOL = pool.SimpleConnectionPool(1, 20, DATABASE_URL)
        print("[INFO] Successfully connected to PostgreSQL production database.")
    except Exception as e:
        print(f"[WARN] Failed to initialize PostgreSQL pool: {e}. Falling back to SQLite.")
        IS_POSTGRES = False


class PostgresCursorWrapper:
    """Wraps psycopg2 DictCursor to provide SQLite-compatible lastrowid and ? parameter syntax."""
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, query, params=None):
        converted_query = query.replace("?", "%s")
        # Handle SQLite-specific syntax
        if "INSERT OR IGNORE INTO settings" in converted_query:
            converted_query = converted_query.replace(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (%s, %s);",
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING;"
            )
        
        # Capture last inserted ID if inserting into a primary-key table
        is_insert = converted_query.strip().upper().startswith("INSERT")
        if is_insert and "RETURNING" not in converted_query.upper():
            table_match = re.search(r"INSERT\s+INTO\s+([a-zA-Z0-9_]+)", converted_query, re.IGNORECASE)
            if table_match and table_match.group(1).lower() in ["employees", "leave_transactions", "users", "leave_types", "audit_logs"]:
                converted_query = converted_query.rstrip("; ") + " RETURNING id;"
                self._cursor.execute(converted_query, params or ())
                row = self._cursor.fetchone()
                if row:
                    self.lastrowid = row[0]
                return self

        self._cursor.execute(converted_query, params or ())
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


class PostgresConnectionWrapper:
    """Wraps a psycopg2 connection to mimic sqlite3 connection behavior."""
    def __init__(self, conn, pool_instance=None):
        self._conn = conn
        self._pool = pool_instance

    def cursor(self):
        import psycopg2.extras
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return PostgresCursorWrapper(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._pool:
            self._pool.putconn(self._conn)
        else:
            self._conn.close()

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur


def get_db_connection():
    """Returns an active database connection (PostgreSQL in production, SQLite locally)."""
    global IS_POSTGRES, PG_POOL
    if IS_POSTGRES and PG_POOL:
        conn = PG_POOL.getconn()
        return PostgresConnectionWrapper(conn, PG_POOL)
    
    # SQLite fallback
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hashes a password with PBKDF2-HMAC-SHA256 and unique salt."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Verifies a password against the stored salt and hash."""
    calc_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(calc_hash, expected_hash)


def init_db():
    """Initializes tables, indexes, settings, and default seed data for PostgreSQL or SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if IS_POSTGRES:
        # PostgreSQL Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) UNIQUE NOT NULL,
            full_name VARCHAR(200) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            salt VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at VARCHAR(100) NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            employee_number VARCHAR(50) UNIQUE NOT NULL,
            employee_name VARCHAR(200) NOT NULL,
            department VARCHAR(100) NOT NULL,
            designation VARCHAR(100) NOT NULL,
            date_of_joining VARCHAR(50) NOT NULL,
            mobile VARCHAR(50),
            email VARCHAR(100),
            address TEXT,
            date_of_birth VARCHAR(50),
            leave_entitlement DOUBLE PRECISION NOT NULL DEFAULT 20.0,
            opening_balance DOUBLE PRECISION NOT NULL DEFAULT 20.0,
            status VARCHAR(50) NOT NULL DEFAULT 'Active',
            remarks TEXT,
            created_at VARCHAR(100) NOT NULL,
            updated_at VARCHAR(100) NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_types (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_transactions (
            id SERIAL PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
            leave_type_id INTEGER NOT NULL REFERENCES leave_types(id),
            transaction_type VARCHAR(20) NOT NULL,
            from_date VARCHAR(50) NOT NULL,
            to_date VARCHAR(50) NOT NULL,
            days DOUBLE PRECISION NOT NULL,
            reason TEXT,
            reference_tx_id INTEGER REFERENCES leave_transactions(id),
            created_by VARCHAR(100) NOT NULL,
            created_at VARCHAR(100) NOT NULL,
            updated_by VARCHAR(100),
            updated_at VARCHAR(100)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            user_name VARCHAR(200),
            action VARCHAR(100) NOT NULL,
            module VARCHAR(100) NOT NULL,
            employee_number VARCHAR(50),
            description TEXT NOT NULL,
            created_at VARCHAR(100) NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)
    else:
        # SQLite Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_number TEXT UNIQUE NOT NULL,
            employee_name TEXT NOT NULL,
            department TEXT NOT NULL,
            designation TEXT NOT NULL,
            date_of_joining TEXT NOT NULL,
            mobile TEXT,
            email TEXT,
            address TEXT,
            date_of_birth TEXT,
            leave_entitlement REAL NOT NULL DEFAULT 20.0,
            opening_balance REAL NOT NULL DEFAULT 20.0,
            status TEXT NOT NULL DEFAULT 'Active',
            remarks TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
            leave_type_id INTEGER NOT NULL REFERENCES leave_types(id),
            transaction_type TEXT NOT NULL,
            from_date TEXT NOT NULL,
            to_date TEXT NOT NULL,
            days REAL NOT NULL,
            reason TEXT,
            reference_tx_id INTEGER REFERENCES leave_transactions(id),
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_by TEXT,
            updated_at TEXT
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            user_name TEXT,
            action TEXT NOT NULL,
            module TEXT NOT NULL,
            employee_number TEXT,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp_num ON employees(employee_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp_dept ON employees(department);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp_status ON employees(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_emp ON leave_transactions(employee_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_dates ON leave_transactions(from_date, to_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);")

    # Seed Default Settings
    default_settings = [
        ("company_name", "Locktite India Pvt Ltd"),
        ("app_title", "Employee Leave Management System"),
        ("allow_negative_balance", "0"),
        ("low_balance_threshold", "3.0"),
        ("financial_year_start", "01-01")
    ]
    for k, v in default_settings:
        if IS_POSTGRES:
            cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO NOTHING;", (k, v))
        else:
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?);", (k, v))

    # Seed Default Users
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().isoformat()
        
        # Admin
        h, s = hash_password("admin123")
        cursor.execute("""
        INSERT INTO users (user_id, full_name, password_hash, salt, role, active, created_at)
        VALUES ('admin', 'System Administrator', ?, ?, 'ADMIN', 1, ?);
        """, (h, s, now_str))

        # Entry User
        h, s = hash_password("entry123")
        cursor.execute("""
        INSERT INTO users (user_id, full_name, password_hash, salt, role, active, created_at)
        VALUES ('entry1', 'Sunita Rao (Leave Entry Clerk)', ?, ?, 'ENTRY USER', 1, ?);
        """, (h, s, now_str))

        # Report User
        h, s = hash_password("report123")
        cursor.execute("""
        INSERT INTO users (user_id, full_name, password_hash, salt, role, active, created_at)
        VALUES ('report1', 'Karthik Menon (Reports & Audit)', ?, ?, 'REPORT USER', 1, ?);
        """, (h, s, now_str))

        cursor.execute("""
        INSERT INTO audit_logs (user_id, user_name, action, module, employee_number, description, created_at)
        VALUES ('SYSTEM', 'Setup', 'INITIALIZE', 'SYSTEM', NULL, 'Database schema initialized with default admin and staff roles.', ?);
        """, (now_str,))

    # Seed Default Leave Types
    cursor.execute("SELECT COUNT(*) FROM leave_types;")
    if cursor.fetchone()[0] == 0:
        default_leave_types = [
            ("Casual Leave", "Annual casual leave for urgent personal matters"),
            ("Sick Leave", "Medical leave for health-related absence"),
            ("Earned Leave", "Privilege/Earned leave accumulated through service"),
            ("Maternity Leave", "Statutory maternity benefit leave"),
            ("Paternity Leave", "Paternity leave for new fathers"),
            ("Compensatory Off", "Leave credited for working on scheduled holidays/weekends"),
            ("Other Leave", "Special or unclassified official sanctioned leave")
        ]
        for name, desc in default_leave_types:
            cursor.execute("INSERT INTO leave_types (name, description, active) VALUES (?, ?, 1);", (name, desc))

    # Seed Initial Demo Employees
    cursor.execute("SELECT COUNT(*) FROM employees;")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().isoformat()
        sample_employees = [
            ("EMP0001", "Ravi Kumar", "Administration", "Admin Officer", "2024-01-15", "9876543210", "ravi.kumar@locktite.in", "Plot 12, Industrial Estate, Phase 1", "1992-05-12", 20.0, 20.0, "Active", "Office Admin Head"),
            ("EMP0002", "Priya Sharma", "Accounts", "Senior Accountant", "2023-06-01", "9876543211", "priya.s@locktite.in", "Flat 4B, Lotus Enclave", "1990-11-20", 22.0, 22.0, "Active", "Handles payroll and audits"),
            ("EMP0003", "Rajesh Patel", "Production", "Plant Supervisor", "2022-03-10", "9876543212", "rajesh.p@locktite.in", "Sector 7, Near Plant Gate 2", "1988-08-14", 24.0, 24.0, "Active", "Shift A operations supervisor"),
            ("EMP0004", "Ananya Sen", "Human Resources", "HR Executive", "2024-08-01", "9876543213", "ananya.sen@locktite.in", "304 Green Valley Apartments", "1995-02-18", 20.0, 20.0, "Active", "Recruitment and onboarding"),
            ("EMP0005", "Vikram Singh", "Quality Assurance", "QA Engineer", "2025-02-15", "9876543214", "vikram.singh@locktite.in", "Block C, Metro View", "1994-09-30", 18.0, 18.0, "Active", "ISO compliance and testing"),
            ("EMP0006", "Meera Nair", "Logistics", "Logistics Coordinator", "2025-05-10", "9876543215", "meera.nair@locktite.in", "House 55, Lake View Road", "1996-07-22", 20.0, 20.0, "Active", "Low leave balance demonstration")
        ]
        for emp in sample_employees:
            cursor.execute("""
            INSERT INTO employees (
                employee_number, employee_name, department, designation, date_of_joining,
                mobile, email, address, date_of_birth, leave_entitlement, opening_balance,
                status, remarks, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (*emp, now_str, now_str))

        cursor.execute("SELECT id FROM employees WHERE employee_number = 'EMP0001';")
        emp1_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM leave_types WHERE name = 'Casual Leave';")
        cl_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM leave_types WHERE name = 'Sick Leave';")
        sl_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM leave_types WHERE name = 'Earned Leave';")
        el_id = cursor.fetchone()[0]

        cursor.execute("""
        INSERT INTO leave_transactions (employee_id, leave_type_id, transaction_type, from_date, to_date, days, reason, created_by, created_at)
        VALUES (?, ?, 'ADD', '2026-10-01', '2026-10-02', 2.0, 'Personal family commitment', 'admin', '2026-10-01 09:30:00');
        """, (emp1_id, cl_id))
        
        cursor.execute("""
        INSERT INTO leave_transactions (employee_id, leave_type_id, transaction_type, from_date, to_date, days, reason, created_by, created_at)
        VALUES (?, ?, 'ADD', '2026-10-10', '2026-10-10', 1.0, 'Medical treatment / doctor appointment', 'entry1', '2026-10-01 10:15:00');
        """, (emp1_id, sl_id))

        cursor.execute("""
        INSERT INTO leave_transactions (employee_id, leave_type_id, transaction_type, from_date, to_date, days, reason, created_by, created_at)
        VALUES (?, ?, 'LESS', '2026-10-02', '2026-10-02', 1.0, 'Cancelled second day - reported to office', 'admin', '2026-10-01 11:00:00');
        """, (emp1_id, cl_id))

        cursor.execute("SELECT id FROM employees WHERE employee_number = 'EMP0006';")
        emp6_id = cursor.fetchone()[0]
        cursor.execute("""
        INSERT INTO leave_transactions (employee_id, leave_type_id, transaction_type, from_date, to_date, days, reason, created_by, created_at)
        VALUES (?, ?, 'ADD', '2026-08-01', '2026-08-18', 18.0, 'Annual planned family event', 'admin', '2026-08-01 09:00:00');
        """, (emp6_id, el_id))

    conn.commit()
    conn.close()


def generate_next_employee_number() -> str:
    """
    Generates the next sequential employee number in EMP0001, EMP0002... format.
    Checks all existing employee numbers and takes max + 1.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT employee_number FROM employees WHERE employee_number LIKE 'EMP%';")
    rows = cursor.fetchall()
    conn.close()

    max_num = 0
    for r in rows:
        val = r["employee_number"]
        digits = val[3:]
        if digits.isdigit():
            num = int(digits)
            if num > max_num:
                max_num = num

    next_num = max_num + 1
    return f"EMP{next_num:04d}"


def get_employee_balance_summary(emp_id: int) -> Dict[str, Any]:
    """Calculates entitlement, opening balance, leave taken, and current balance for an employee."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        e.id, e.employee_number, e.employee_name, e.department, e.designation,
        e.leave_entitlement, e.opening_balance, e.status,
        COALESCE(SUM(CASE WHEN t.transaction_type = 'ADD' THEN t.days WHEN t.transaction_type = 'LESS' THEN -t.days ELSE 0 END), 0) as total_taken
    FROM employees e
    LEFT JOIN leave_transactions t ON e.id = t.employee_id
    WHERE e.id = ?
    GROUP BY e.id, e.employee_number, e.employee_name, e.department, e.designation, e.leave_entitlement, e.opening_balance, e.status;
    """, (emp_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {}

    entitlement = float(row["leave_entitlement"])
    opening = float(row["opening_balance"])
    taken = float(row["total_taken"])
    balance = opening - taken

    return {
        "id": row["id"],
        "employee_number": row["employee_number"],
        "employee_name": row["employee_name"],
        "department": row["department"],
        "designation": row["designation"],
        "leave_entitlement": entitlement,
        "opening_balance": opening,
        "leave_taken": taken,
        "current_balance": balance,
        "status": row["status"]
    }
