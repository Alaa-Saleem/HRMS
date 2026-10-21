from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=512)
    new_password: str = Field(min_length=1, max_length=128)


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: Optional[str] = Field(None, max_length=32)


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    code: Optional[str] = None
    is_active: Optional[bool] = None


class EmployeeCreate(BaseModel):
    first: str
    last: str
    email: str
    phone: str = ""
    password: str
    role: str
    department_id: int
    title: str
    salary: float
    start: date
    manager_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    first: Optional[str] = None
    last: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None
    title: Optional[str] = None
    salary: Optional[float] = None
    start: Optional[date] = None
    manager_id: Optional[int] = None
    status: Optional[str] = None
    address: Optional[str] = None
    emergency: Optional[str] = None


class LeaveCreate(BaseModel):
    type: str
    start: date
    end: date
    reason: str = ""


class LeaveStatusUpdate(BaseModel):
    status: str  # approved | rejected


class TaskCreate(BaseModel):
    title: str
    assignee_id: int
    due: Optional[str] = None
    status: str = "todo"
    priority: Optional[str] = "medium"


class TaskMove(BaseModel):
    status: str


class ChatCreate(BaseModel):
    text: str


class EmployeeImportRow(BaseModel):
    """Single row from JSON import body."""

    email: str
    first: str
    last: str
    phone: str = ""
    role: str = "employee"
    department_id: int
    title: str = ""
    salary: float = 0
    start: Optional[str] = None
    manager_id: Optional[int] = None
    password: Optional[str] = None


class EmployeeImportResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[dict] = Field(default_factory=list)

