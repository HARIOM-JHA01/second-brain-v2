"""
Rolplay Super-Admin API
Access: session-based (ADMIN_EMAIL / ADMIN_PASSWORD from env).
All routes under /admin/api/* require is_admin=True in session.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from agente_rolplay.config import ADMIN_EMAIL, ADMIN_PASSWORD
from agente_rolplay.db.auth import get_password_hash
from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import Document, MessageLog, Organization, Profile, Role, User

router = APIRouter(prefix="/admin/api", tags=["admin"])


# ── Auth guard ────────────────────────────────────────────────────────────────

def require_admin(request: Request):
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


# ── Login / Logout ────────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def admin_login(body: AdminLoginRequest, request: Request):
    if body.email != ADMIN_EMAIL or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    request.session["is_admin"] = True
    return {"ok": True}


@router.post("/logout")
async def admin_logout(request: Request):
    request.session.pop("is_admin", None)
    return {"ok": True}


# ── Stats / KPIs ──────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(request: Request, db: Session = Depends(get_db)):
    require_admin(request)

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_orgs = db.query(func.count(Organization.id)).scalar()
    total_users = db.query(func.count(Profile.id)).scalar()
    active_users = db.query(func.count(Profile.id)).filter(Profile.is_active == True).scalar()
    inactive_users = total_users - active_users

    new_orgs_7d = db.query(func.count(Organization.id)).filter(Organization.created_at >= week_ago).scalar()
    new_orgs_30d = db.query(func.count(Organization.id)).filter(Organization.created_at >= month_ago).scalar()
    new_users_7d = db.query(func.count(Profile.id)).filter(Profile.created_at >= week_ago).scalar()
    new_users_30d = db.query(func.count(Profile.id)).filter(Profile.created_at >= month_ago).scalar()

    total_documents = db.query(func.count(Document.id)).scalar()
    total_roles = db.query(func.count(Role.id)).scalar()

    avg_users_per_org = round(total_users / total_orgs, 1) if total_orgs else 0

    # ── MessageLog KPIs ───────────────────────────────────────────────────────
    messages_7d = db.query(func.count(MessageLog.id)).filter(MessageLog.created_at >= week_ago).scalar()
    messages_30d = db.query(func.count(MessageLog.id)).filter(MessageLog.created_at >= month_ago).scalar()
    voice_notes_7d = db.query(func.count(MessageLog.id)).filter(
        MessageLog.created_at >= week_ago, MessageLog.is_voice_note == True
    ).scalar()
    voice_notes_30d = db.query(func.count(MessageLog.id)).filter(
        MessageLog.created_at >= month_ago, MessageLog.is_voice_note == True
    ).scalar()
    rag_queries_7d = db.query(func.count(MessageLog.id)).filter(
        MessageLog.created_at >= week_ago, MessageLog.is_rag_query == True
    ).scalar()
    errors_7d = db.query(func.count(MessageLog.id)).filter(
        MessageLog.created_at >= week_ago, MessageLog.is_error == True
    ).scalar()
    truly_active_users_7d = db.query(func.count(distinct(MessageLog.phone_number))).filter(
        MessageLog.created_at >= week_ago
    ).scalar()

    avg_response_ms_row = db.query(func.avg(MessageLog.response_time_ms)).filter(
        MessageLog.created_at >= month_ago,
        MessageLog.response_time_ms.isnot(None),
        MessageLog.is_error == False,
    ).scalar()
    avg_response_ms = int(avg_response_ms_row) if avg_response_ms_row else None

    # Documents uploaded this period (from Document table)
    docs_uploaded_7d = db.query(func.count(Document.id)).filter(Document.created_at >= week_ago).scalar()
    docs_uploaded_30d = db.query(func.count(Document.id)).filter(Document.created_at >= month_ago).scalar()

    # Messages per day (last 30 days) for chart
    messages_by_day = (
        db.query(
            func.date(MessageLog.created_at).label("day"),
            func.count(MessageLog.id).label("count"),
        )
        .filter(MessageLog.created_at >= month_ago)
        .group_by(func.date(MessageLog.created_at))
        .order_by(func.date(MessageLog.created_at))
        .all()
    )
    messages_chart = [{"day": str(r.day), "count": r.count} for r in messages_by_day]

    # Pinecone vector count (best-effort)
    pinecone_vector_count = None
    try:
        from agente_rolplay.storage.pinecone_client import get_pinecone_index
        idx = get_pinecone_index()
        if idx:
            stats = idx.describe_index_stats()
            pinecone_vector_count = (
                stats.get("total_vector_count")
                or sum(ns.get("vector_count", 0) for ns in stats.get("namespaces", {}).values())
            )
    except Exception:
        pass

    # Signups per day last 30 days
    signups_by_day = (
        db.query(
            func.date(Profile.created_at).label("day"),
            func.count(Profile.id).label("count"),
        )
        .filter(Profile.created_at >= month_ago)
        .group_by(func.date(Profile.created_at))
        .order_by(func.date(Profile.created_at))
        .all()
    )
    signups_chart = [{"day": str(r.day), "count": r.count} for r in signups_by_day]

    return {
        "total_orgs": total_orgs,
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "new_orgs_7d": new_orgs_7d,
        "new_orgs_30d": new_orgs_30d,
        "new_users_7d": new_users_7d,
        "new_users_30d": new_users_30d,
        "total_documents": total_documents,
        "total_roles": total_roles,
        "avg_users_per_org": avg_users_per_org,
        "signups_chart": signups_chart,
        # Usage KPIs
        "messages_7d": messages_7d,
        "messages_30d": messages_30d,
        "voice_notes_7d": voice_notes_7d,
        "voice_notes_30d": voice_notes_30d,
        "rag_queries_7d": rag_queries_7d,
        "errors_7d": errors_7d,
        "truly_active_users_7d": truly_active_users_7d,
        "avg_response_ms": avg_response_ms,
        "docs_uploaded_7d": docs_uploaded_7d,
        "docs_uploaded_30d": docs_uploaded_30d,
        "messages_chart": messages_chart,
        "pinecone_vector_count": pinecone_vector_count,
    }


# ── Organizations ─────────────────────────────────────────────────────────────

@router.get("/organizations")
def list_organizations(request: Request, db: Session = Depends(get_db)):
    require_admin(request)

    orgs = db.query(Organization).order_by(Organization.created_at.desc()).all()
    result = []
    for org in orgs:
        user_count = db.query(func.count(Profile.id)).filter(Profile.org_id == org.id).scalar()
        active_count = db.query(func.count(Profile.id)).filter(
            Profile.org_id == org.id, Profile.is_active == True
        ).scalar()
        doc_count = db.query(func.count(Document.id)).filter(Document.org_id == org.id).scalar()
        owner = db.query(User).filter(User.id == org.owner_id).first() if org.owner_id else None
        result.append({
            "id": str(org.id),
            "name": org.name,
            "owner_email": owner.email if owner else None,
            "user_count": user_count,
            "active_user_count": active_count,
            "document_count": doc_count,
            "created_at": org.created_at.isoformat(),
        })
    return result


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_all_users(request: Request, db: Session = Depends(get_db)):
    require_admin(request)

    profiles = db.query(Profile).order_by(Profile.created_at.desc()).all()
    result = []
    for p in profiles:
        user = db.query(User).filter(User.id == p.user_id).first()
        org = db.query(Organization).filter(Organization.id == p.org_id).first()
        role = db.query(Role).filter(Role.id == p.role_id).first() if p.role_id else None
        result.append({
            "profile_id": str(p.id),
            "user_id": str(p.user_id),
            "email": user.email if user else None,
            "full_name": p.full_name,
            "job_title": p.job_title,
            "whatsapp_number": p.whatsapp_number,
            "org_id": str(p.org_id),
            "org_name": org.name if org else None,
            "role_name": role.name if role else None,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat(),
        })
    return result


# ── Set password ──────────────────────────────────────────────────────────────

class SetPasswordRequest(BaseModel):
    new_password: str


@router.post("/users/{user_id}/set-password")
def set_user_password(
    user_id: str,
    body: SetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request)

    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = get_password_hash(body.new_password)
    db.commit()
    return {"ok": True}


# ── Toggle active ─────────────────────────────────────────────────────────────

@router.patch("/users/{profile_id}/active")
def toggle_user_active(profile_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin(request)

    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.is_active = not profile.is_active
    db.commit()
    return {"is_active": profile.is_active}
