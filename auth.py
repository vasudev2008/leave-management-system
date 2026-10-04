"""
Authentication, session management, and role authorization module.
Supports PBKDF2 password verification, secure session tokens, brute-force protection, and role checks.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Security, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import get_db_connection, verify_password, hash_password
from app.audit import log_audit

# Active sessions store in-memory (and can persist or fall back to DB)
# session_id -> { "user_id": str, "role": str, "full_name": str, "expires_at": datetime }
SESSIONS: Dict[str, Dict[str, Any]] = {}

SESSION_TIMEOUT_MINUTES = int(os.environ.get("SESSION_TIMEOUT_MINUTES", "120"))

# Brute-force protection tracking
FAILED_LOGINS: Dict[str, List[datetime]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

security_bearer = HTTPBearer(auto_error=False)


def check_brute_force(identifier: str):
    """Checks if the user_id or IP is locked out due to multiple failed login attempts."""
    now = datetime.now()
    attempts = FAILED_LOGINS.get(identifier, [])
    attempts = [t for t in attempts if (now - t).total_seconds() < LOCKOUT_MINUTES * 60]
    FAILED_LOGINS[identifier] = attempts
    if len(attempts) >= MAX_FAILED_ATTEMPTS:
        oldest = attempts[0]
        remaining_secs = int((LOCKOUT_MINUTES * 60) - (now - oldest).total_seconds())
        remaining_mins = max(1, (remaining_secs + 59) // 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Security lock in place. Please wait {remaining_mins} minute(s) before trying again."
        )


def record_login_failure(identifier: str):
    """Records a failed login attempt for brute-force tracking."""
    now = datetime.now()
    attempts = FAILED_LOGINS.get(identifier, [])
    attempts = [t for t in attempts if (now - t).total_seconds() < LOCKOUT_MINUTES * 60]
    attempts.append(now)
    FAILED_LOGINS[identifier] = attempts


def record_login_success(identifier: str):
    """Clears failed login attempts after a successful authentication."""
    if identifier in FAILED_LOGINS:
        del FAILED_LOGINS[identifier]


def authenticate_user(user_id: str, password: str, client_ip: str = "unknown") -> Optional[Dict[str, Any]]:
    """Validates user credentials against database with brute force protection."""
    check_brute_force(user_id)
    if client_ip != "unknown":
        check_brute_force(client_ip)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, user_id, full_name, password_hash, salt, role, active
    FROM users
    WHERE user_id = ?;
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        record_login_failure(user_id)
        if client_ip != "unknown":
            record_login_failure(client_ip)
        return None

    if row["active"] != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is currently inactive. Please contact your system administrator."
        )

    if not verify_password(password, row["salt"], row["password_hash"]):
        record_login_failure(user_id)
        if client_ip != "unknown":
            record_login_failure(client_ip)
        return None

    record_login_success(user_id)
    if client_ip != "unknown":
        record_login_success(client_ip)

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "full_name": row["full_name"],
        "role": row["role"]
    }


def create_session(user_data: Dict[str, Any]) -> str:
    """Generates a secure random session token and stores it with configurable expiration."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    SESSIONS[token] = {
        "user_id": user_data["user_id"],
        "role": user_data["role"],
        "full_name": user_data["full_name"],
        "expires_at": expires
    }
    return token


def invalidate_session(token: str):
    """Removes a session upon logout."""
    if token in SESSIONS:
        del SESSIONS[token]


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> Dict[str, Any]:
    """
    Extracts session token from Bearer header or query/cookie and returns user context.
    Raises 401 if missing or expired.
    """
    token = None
    if credentials:
        token = credentials.credentials
    if not token:
        token = request.headers.get("X-Session-Token") or request.query_params.get("session_token")

    if not token or token not in SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication session expired or invalid. Please login again."
        )

    session = SESSIONS[token]
    if datetime.now() > session["expires_at"]:
        del SESSIONS[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please login again."
        )

    # Sliding session renewal on active requests
    session["expires_at"] = datetime.now() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    return {
        "user_id": session["user_id"],
        "role": session["role"],
        "full_name": session["full_name"],
        "token": token
    }


def require_role(allowed_roles: list[str]):
    """Dependency generator that verifies the current user has one of the allowed roles."""
    def role_checker(user: Dict[str, Any] = Security(get_current_user)) -> Dict[str, Any]:
        if user["role"] not in allowed_roles and user["role"] != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: This operation requires one of {allowed_roles} roles."
            )
        return user
    return role_checker


def verify_admin_password(user_id: str, password: str) -> bool:
    """Used for confirmation modals on sensitive master and database operations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt, role FROM users WHERE user_id = ?;", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    return verify_password(password, row["salt"], row["password_hash"])
