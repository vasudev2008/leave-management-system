"""
Audit logging helper module for Locktite India Pvt Ltd.
Maintains comprehensive, immutable audit trail for compliance and tracking.
"""

from datetime import datetime
from typing import Optional
from app.database import get_db_connection


def log_audit(
    user_id: str,
    user_name: Optional[str],
    action: str,
    module: str,
    description: str,
    employee_number: Optional[str] = None
):
    """Inserts a new audit record into the audit_logs table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO audit_logs (user_id, user_name, action, module, employee_number, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (user_id, user_name or user_id, action, module, employee_number, description, now_str))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AUDIT ERROR] Failed to record audit log: {e}")
