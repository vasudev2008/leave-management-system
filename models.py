"""
Pydantic data schemas for request validation and response typing.
Ensures strict type checking and clean API contract.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class UserCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern="^(ADMIN|ENTRY USER|REPORT USER)$")


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    new_password: Optional[str] = None


class EmployeeCreateRequest(BaseModel):
    employee_name: str = Field(..., min_length=2, max_length=100)
    department: str = Field(..., min_length=1, max_length=100)
    designation: str = Field(..., min_length=1, max_length=100)
    date_of_joining: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
    leave_entitlement: float = Field(default=20.0, ge=0.0)
    opening_balance: float = Field(default=20.0, ge=0.0)
    status: str = Field(default="Active", pattern="^(Active|Inactive)$")
    remarks: Optional[str] = None


class EmployeeUpdateRequest(BaseModel):
    employee_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    date_of_joining: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
    leave_entitlement: Optional[float] = None
    opening_balance: Optional[float] = None
    status: Optional[str] = None
    remarks: Optional[str] = None
    confirmation_password: Optional[str] = None  # required if editing entitlement/opening balance


class SensitiveActionRequest(BaseModel):
    password: str
    reason: Optional[str] = None


class LeaveEntryRequest(BaseModel):
    employee_id: int
    leave_type_id: int
    from_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    to_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    days: float = Field(..., gt=0.0)
    reason: Optional[str] = None
    override_balance_check: Optional[bool] = False  # only admin can override if configured


class LeaveAdjustmentRequest(BaseModel):
    employee_id: int
    leave_type_id: int
    from_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    to_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    days: float = Field(..., gt=0.0)
    reason: str = Field(..., min_length=3)
    reference_tx_id: Optional[int] = None


class LeaveTypeCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    active: bool = True


class SettingUpdateRequest(BaseModel):
    key: str
    value: str
