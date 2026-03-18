from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import Document, MessageLog, User, Profile, Organization, Role
from agente_rolplay.db.schemas import (
    ProfileResponse,
    ProfileCreate,
    ProfileUpdate,
    ProfileWithUser,
    RoleResponse,
    UserResponse,
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


# ── Literal routes MUST come before /{user_id} ───────────────────────────────

@router.get("/dashboard-stats", tags=["dashboard"])
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Org-scoped KPIs for the user dashboard."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    org_id = profile.org_id

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = db.query(func.count(Profile.id)).filter(Profile.org_id == org_id).scalar()
    active_users = db.query(func.count(Profile.id)).filter(
        Profile.org_id == org_id, Profile.is_active == True
    ).scalar()
    new_users_7d = db.query(func.count(Profile.id)).filter(
        Profile.org_id == org_id, Profile.created_at >= week_ago
    ).scalar()
    new_users_30d = db.query(func.count(Profile.id)).filter(
        Profile.org_id == org_id, Profile.created_at >= month_ago
    ).scalar()
    total_roles = db.query(func.count(Role.id)).filter(Role.org_id == org_id).scalar()
    total_docs = db.query(func.count(Document.id)).filter(Document.org_id == org_id).scalar()

    org = db.query(Organization).filter(Organization.id == org_id).first()

    # ── Usage KPIs from MessageLog (org-scoped via phone numbers) ─────────────
    # Get all whatsapp numbers in this org; include both normalized (+521...)
    # and stripped (521...) variants to match records written before the
    # normalize fix was applied.
    _raw_phones = [
        p.whatsapp_number
        for p in db.query(Profile.whatsapp_number)
        .filter(Profile.org_id == org_id, Profile.whatsapp_number.isnot(None))
        .all()
    ]
    org_phones = list({p for raw in _raw_phones for p in (raw, raw.lstrip("+"))})

    messages_7d = 0
    messages_30d = 0
    voice_notes_7d = 0
    truly_active_users_7d = 0
    avg_response_ms = None
    docs_uploaded_7d = 0
    docs_uploaded_30d = 0

    messages_chart = []
    message_types_breakdown = {"text": 0, "audio": 0, "image": 0, "document": 0}

    if org_phones:
        messages_7d = db.query(func.count(MessageLog.id)).filter(
            MessageLog.created_at >= week_ago,
            MessageLog.phone_number.in_(org_phones),
        ).scalar() or 0
        messages_30d = db.query(func.count(MessageLog.id)).filter(
            MessageLog.created_at >= month_ago,
            MessageLog.phone_number.in_(org_phones),
        ).scalar() or 0
        voice_notes_7d = db.query(func.count(MessageLog.id)).filter(
            MessageLog.created_at >= week_ago,
            MessageLog.is_voice_note == True,
            MessageLog.phone_number.in_(org_phones),
        ).scalar() or 0
        truly_active_users_7d = db.query(func.count(distinct(MessageLog.phone_number))).filter(
            MessageLog.created_at >= week_ago,
            MessageLog.phone_number.in_(org_phones),
        ).scalar() or 0
        avg_ms_row = db.query(func.avg(MessageLog.response_time_ms)).filter(
            MessageLog.created_at >= month_ago,
            MessageLog.phone_number.in_(org_phones),
            MessageLog.response_time_ms.isnot(None),
            MessageLog.is_error == False,
        ).scalar()
        avg_response_ms = int(avg_ms_row) if avg_ms_row else None

        # Messages per day (last 30 days) for chart
        rows = (
            db.query(
                func.date(MessageLog.created_at).label("day"),
                func.count(MessageLog.id).label("count"),
            )
            .filter(
                MessageLog.created_at >= month_ago,
                MessageLog.phone_number.in_(org_phones),
            )
            .group_by(func.date(MessageLog.created_at))
            .order_by(func.date(MessageLog.created_at))
            .all()
        )
        messages_chart = [{"day": str(r.day), "count": r.count} for r in rows]

        # Message type breakdown (last 30 days)
        for msg_type in ("text", "audio", "image", "document"):
            cnt = db.query(func.count(MessageLog.id)).filter(
                MessageLog.created_at >= month_ago,
                MessageLog.phone_number.in_(org_phones),
                MessageLog.message_type == msg_type,
            ).scalar() or 0
            message_types_breakdown[msg_type] = cnt

    docs_uploaded_7d = db.query(func.count(Document.id)).filter(
        Document.org_id == org_id,
        Document.created_at >= week_ago,
    ).scalar() or 0
    docs_uploaded_30d = db.query(func.count(Document.id)).filter(
        Document.org_id == org_id,
        Document.created_at >= month_ago,
    ).scalar() or 0

    # Signups per day (last 30 days) for chart
    signup_rows = (
        db.query(
            func.date(Profile.created_at).label("day"),
            func.count(Profile.id).label("count"),
        )
        .filter(Profile.org_id == org_id, Profile.created_at >= month_ago)
        .group_by(func.date(Profile.created_at))
        .order_by(func.date(Profile.created_at))
        .all()
    )
    signups_chart = [{"day": str(r.day), "count": r.count} for r in signup_rows]

    return {
        "org_name": org.name if org else None,
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "new_users_7d": new_users_7d,
        "new_users_30d": new_users_30d,
        "total_roles": total_roles,
        "total_docs": total_docs,
        # Usage KPIs
        "messages_7d": messages_7d,
        "messages_30d": messages_30d,
        "voice_notes_7d": voice_notes_7d,
        "truly_active_users_7d": truly_active_users_7d,
        "avg_response_ms": avg_response_ms,
        "docs_uploaded_7d": docs_uploaded_7d,
        "docs_uploaded_30d": docs_uploaded_30d,
        # Chart data
        "messages_chart": messages_chart,
        "signups_chart": signups_chart,
        "message_types_breakdown": message_types_breakdown,
    }


@router.get("/documents", tags=["documents"])
def list_org_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List documents belonging to the current user's org, enriched with Cloudinary metadata."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    docs = (
        db.query(Document)
        .filter(Document.org_id == profile.org_id)
        .order_by(Document.created_at.desc())
        .all()
    )

    cloudinary_meta: dict = {}
    if docs:
        try:
            import cloudinary.api
            for resource_type in ("image", "raw"):
                result = cloudinary.api.resources(
                    type="upload",
                    resource_type=resource_type,
                    prefix="knowledgebase/",
                    max_results=500,
                )
                for r in result.get("resources", []):
                    cloudinary_meta[r["public_id"]] = r
        except Exception:
            pass

    result = []
    for doc in docs:
        cloud = cloudinary_meta.get(doc.drive_file_id or "", {})
        result.append({
            "id": str(doc.id),
            "name": doc.name,
            "public_id": doc.drive_file_id,
            "secure_url": cloud.get("secure_url"),
            "resource_type": cloud.get("resource_type"),
            "format": cloud.get("format"),
            "bytes": cloud.get("bytes"),
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        })
    return result


# ── CRUD (parameterized routes) ───────────────────────────────────────────────

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
            full_name=p.full_name,
            job_title=p.job_title,
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
    import secrets
    from agente_rolplay.db.auth import get_password_hash

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

    phone_clean = (user_data.whatsapp_number or "").strip().lstrip("+").replace(" ", "")
    placeholder_email = f"wa_{phone_clean}@{org.id}.internal"

    new_user = db.query(User).filter(User.email == placeholder_email).first()
    if not new_user:
        new_user = User(
            email=placeholder_email,
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
        )
        db.add(new_user)
        db.flush()

    profile = Profile(
        user_id=new_user.id,
        org_id=org.id,
        username=user_data.username,
        full_name=user_data.full_name,
        job_title=user_data.job_title,
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
        full_name=profile.full_name,
        job_title=profile.job_title,
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
    if user_data.full_name is not None:
        profile.full_name = user_data.full_name
    if user_data.job_title is not None:
        profile.job_title = user_data.job_title
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
