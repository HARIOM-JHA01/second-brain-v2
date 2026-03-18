from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationBase(BaseModel):
    name: str


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: UUID
    owner_id: Optional[UUID] = None
    settings: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str
    permissions: List[Dict[str, Any]] = []


class RoleCreate(RoleBase):
    org_id: Optional[UUID] = None


class RoleResponse(RoleBase):
    id: UUID
    org_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileBase(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    whatsapp_number: Optional[str] = None
    role_id: Optional[UUID] = None


class ProfileCreate(ProfileBase):
    user_id: UUID
    org_id: Optional[UUID] = None


class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    whatsapp_number: Optional[str] = None
    role_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class ProfileResponse(ProfileBase):
    id: UUID
    user_id: UUID
    org_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileWithUser(ProfileResponse):
    user: Optional[UserResponse] = None
    role: Optional[RoleResponse] = None


class DocumentBase(BaseModel):
    name: Optional[str] = None
    drive_file_id: Optional[str] = None


class DocumentCreate(DocumentBase):
    org_id: UUID


class DocumentResponse(DocumentBase):
    id: UUID
    org_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    user_id: Optional[UUID] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    organization_name: str
    full_name: str
    whatsapp_number: str
    job_title: str
