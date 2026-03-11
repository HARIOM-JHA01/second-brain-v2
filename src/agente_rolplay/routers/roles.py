from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from src.agente_rolplay.database import get_db
from src.agente_rolplay.models import User, Profile, Organization, Role
from src.agente_rolplay.schemas import RoleResponse, RoleCreate
from src.agente_rolplay.auth import get_current_user

router = APIRouter(prefix="/api/roles", tags=["roles"])


def get_org_for_user(db: Session, user_id: UUID) -> Organization:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    org = db.query(Organization).filter(Organization.id == profile.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)
    roles = db.query(Role).filter(Role.org_id == org.id).all()
    return roles


@router.post("", response_model=RoleResponse)
def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)

    role = Role(
        org_id=org.id,
        name=role_data.name,
        permissions=role_data.permissions,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)

    role = db.query(Role).filter(Role.id == role_id, Role.org_id == org.id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: UUID,
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)

    role = db.query(Role).filter(Role.id == role_id, Role.org_id == org.id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    role.name = role_data.name
    role.permissions = role_data.permissions

    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}")
def delete_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)

    role = db.query(Role).filter(Role.id == role_id, Role.org_id == org.id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    db.delete(role)
    db.commit()
    return {"message": "Role deleted"}
