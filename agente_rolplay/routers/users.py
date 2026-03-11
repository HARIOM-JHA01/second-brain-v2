from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import User, Profile, Organization, Role
from agente_rolplay.db.schemas import (
    ProfileResponse,
    ProfileCreate,
    ProfileUpdate,
    ProfileWithUser,
    RoleResponse,
)
from agente_rolplay.db.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


def get_org_for_user(db: Session, user_id: UUID) -> Organization:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    org = db.query(Organization).filter(Organization.id == profile.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("", response_model=List[ProfileWithUser])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    users = db.query(Profile).filter(Profile.org_id == profile.org_id).all()

    result = []
    for p in users:
        user = db.query(User).filter(User.id == p.user_id).first()
        role = (
            db.query(Role).filter(Role.id == p.role_id).first() if p.role_id else None
        )

        profile_data = ProfileWithUser(
            id=p.id,
            user_id=p.user_id,
            org_id=p.org_id,
            username=p.username,
            whatsapp_number=p.whatsapp_number,
            role_id=p.role_id,
            is_active=p.is_active,
            created_at=p.created_at,
            user=UserResponse(id=user.id, email=user.email, created_at=user.created_at)
            if user
            else None,
            role=RoleResponse(
                id=role.id,
                org_id=role.org_id,
                name=role.name,
                permissions=role.permissions,
                created_at=role.created_at,
            )
            if role
            else None,
        )
        result.append(profile_data)

    return result


@router.post("", response_model=ProfileResponse)
def create_user(
    user_data: ProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)

    existing = (
        db.query(Profile)
        .filter(
            Profile.org_id == org.id,
            Profile.whatsapp_number == user_data.whatsapp_number,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="WhatsApp number already exists in organization"
        )

    profile = Profile(
        user_id=user_data.user_id,
        org_id=org.id,
        username=user_data.username,
        whatsapp_number=user_data.whatsapp_number,
        role_id=user_data.role_id,
        is_active=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{user_id}", response_model=ProfileWithUser)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)

    profile = (
        db.query(Profile)
        .filter(Profile.id == user_id, Profile.org_id == org.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    user = db.query(User).filter(User.id == profile.user_id).first()
    role = (
        db.query(Role).filter(Role.id == profile.role_id).first()
        if profile.role_id
        else None
    )

    return ProfileWithUser(
        id=profile.id,
        user_id=profile.user_id,
        org_id=profile.org_id,
        username=profile.username,
        whatsapp_number=profile.whatsapp_number,
        role_id=profile.role_id,
        is_active=profile.is_active,
        created_at=profile.created_at,
        user=UserResponse(id=user.id, email=user.email, created_at=user.created_at)
        if user
        else None,
        role=RoleResponse(
            id=role.id,
            org_id=role.org_id,
            name=role.name,
            permissions=role.permissions,
            created_at=role.created_at,
        )
        if role
        else None,
    )


@router.put("/{user_id}", response_model=ProfileResponse)
def update_user(
    user_id: UUID,
    user_data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)

    profile = (
        db.query(Profile)
        .filter(Profile.id == user_id, Profile.org_id == org.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.username is not None:
        profile.username = user_data.username
    if user_data.whatsapp_number is not None:
        profile.whatsapp_number = user_data.whatsapp_number
    if user_data.role_id is not None:
        profile.role_id = user_data.role_id
    if user_data.is_active is not None:
        profile.is_active = user_data.is_active

    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{user_id}")
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)

    profile = (
        db.query(Profile)
        .filter(Profile.id == user_id, Profile.org_id == org.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    profile.is_active = False
    db.commit()
    return {"message": "User access revoked"}


@router.post("/{user_id}/reactivate", response_model=ProfileResponse)
def reactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)

    profile = (
        db.query(Profile)
        .filter(Profile.id == user_id, Profile.org_id == org.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    profile.is_active = True
    db.commit()
    db.refresh(profile)
    return profile
