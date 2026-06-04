from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import DocumentStatus, UserRole


# ----- Auth -----
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.assistant


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ForgotPasswordIn(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None


class ResetPasswordIn(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    code: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime


class RegisterOut(BaseModel):
    message: str
    email: EmailStr


class VerifyEmailIn(BaseModel):
    email: EmailStr
    code: str


class ResendVerificationIn(BaseModel):
    email: EmailStr


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshIn(BaseModel):
    refresh_token: str


# ----- Project -----
class ProjectCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    company_role: str = Field(min_length=1, max_length=255)
    activity_sector: str = Field(min_length=1, max_length=255)
    product: str = Field(min_length=1, max_length=255)
    market: str = Field(min_length=1, max_length=255)
    standards: str = ""
    progress: int = Field(default=0, ge=0, le=100)
    member_ids: list[int] = []


class ProjectUpdate(BaseModel):
    company_name: Optional[str] = None
    company_role: Optional[str] = None
    activity_sector: Optional[str] = None
    product: Optional[str] = None
    market: Optional[str] = None
    standards: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    member_ids: Optional[list[int]] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_name: str
    company_role: str
    activity_sector: str
    product: str
    market: str
    standards: str
    owner_id: int
    is_validated: bool = False
    progress: int = 0
    validated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    member_ids: list[int] = []


# ----- Process -----
class ProcessSheetFields(BaseModel):
    process_owner: str = ""
    objective: str = ""
    inputs: str = ""
    outputs: str = ""
    activities: str = ""
    resources: str = ""
    kpis: str = ""
    risks_opportunities: str = ""
    related_documents: str = ""


class ProcessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    version: str = "1.0"
    progress: int = Field(default=0, ge=0, le=100)


class ProcessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    process_owner: Optional[str] = None
    objective: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    activities: Optional[str] = None
    resources: Optional[str] = None
    kpis: Optional[str] = None
    risks_opportunities: Optional[str] = None
    related_documents: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)


class ProcessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    description: str
    version: str
    file_url: Optional[str]
    file_name: Optional[str]
    process_owner: str = ""
    objective: str = ""
    inputs: str = ""
    outputs: str = ""
    activities: str = ""
    resources: str = ""
    kpis: str = ""
    risks_opportunities: str = ""
    related_documents: str = ""
    progress: int = 0
    created_at: datetime
    updated_at: datetime
    validated_at: Optional[datetime] = None


# ----- Document -----
class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    process_id: int
    title: str
    description: str
    status: DocumentStatus
    current_version: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    validated_at: Optional[datetime] = None


class DocumentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: int
    version: str
    file_url: str
    file_name: str
    status: DocumentStatus
    note: str
    uploaded_by: int
    created_at: datetime


class DocumentStatusUpdate(BaseModel):
    status: DocumentStatus


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


# ----- Messages -----
class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_url: str
    file_name: str
    content_type: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: int
    user_id: int
    body: str
    created_at: datetime
    attachments: list[AttachmentOut] = []


# ----- Notifications -----
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    body: str
    link: str
    read: bool
    created_at: datetime


# ----- Upload -----
class UploadUrlOut(BaseModel):
    upload_url: str
    file_url: str
    file_key: str


# ----- Dashboard -----
class DashboardStats(BaseModel):
    total_projects: int
    total_processes: int
    total_documents: int
    documents_to_validate: int
    unread_notifications: int
