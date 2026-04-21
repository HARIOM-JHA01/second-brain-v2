"""
Rolplay Super-Admin API
Access: session-based (ADMIN_EMAIL / ADMIN_PASSWORD from env).
All routes under /admin/api/* require is_admin=True in session.
"""

import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from agente_rolplay.config import ADMIN_EMAIL, ADMIN_PASSWORD, INTERNAL_API_TOKEN
from agente_rolplay.db.auth import get_password_hash
from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import (
    BroadcastSchedule,
    CoachingScenario,
    CoachingScenarioReferenceFile,
    CoachingSession,
    Document,
    Group,
    GroupMember,
    MessageLog,
    MessageTemplate,
    Organization,
    Profile,
    Role,
    User,
    WhatsAppMessage,
)
from agente_rolplay.storage.file_processor import (
    SUPPORTED_TYPES,
    extract_text_from_file,
)

import json as _json
import redis as _redis_lib
from agente_rolplay.config import redis_connection_kwargs

router = APIRouter(prefix="/admin/api", tags=["admin"])
MAX_SCENARIO_REFERENCE_CHARS = 50000

MENU_OPTIONS_KEY = "admin:menu_options"
_ALL_MENU_OPTIONS = {"1", "2", "3", "4"}


def _get_redis():
    return _redis_lib.Redis(**redis_connection_kwargs())


def _default_menu_options() -> dict[str, bool]:
    return {k: True for k in _ALL_MENU_OPTIONS}


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_mime_type(filename: str, incoming_mime: str | None) -> str:
    if incoming_mime and incoming_mime in SUPPORTED_TYPES.values():
        return incoming_mime
    ext = Path(filename or "").suffix.lower().lstrip(".")
    return SUPPORTED_TYPES.get(ext, incoming_mime or "")


async def _parse_scenario_request(request: Request) -> tuple[dict[str, Any], list[Any]]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        reference_files = form.getlist("reference_files")
        return (
            {
                "name": form.get("name"),
                "system_prompt": form.get("system_prompt"),
                "org_id": form.get("org_id"),
                "description": form.get("description"),
                "is_active": form.get("is_active"),
                "clear_reference_file": form.get("clear_reference_file"),
                "usecase_api_id": form.get("usecase_api_id"),
            },
            reference_files,
        )
    body = await request.json()
    files = body.pop("reference_files", None)
    return body, files if files else []


async def _extract_reference_file(upload_file) -> tuple[str, str]:
    if not upload_file or not getattr(upload_file, "filename", None):
        raise HTTPException(status_code=400, detail="No file provided")

    mime_type = _resolve_mime_type(
        upload_file.filename, getattr(upload_file, "content_type", None)
    )
    if mime_type not in SUPPORTED_TYPES.values():
        allowed = ", ".join(sorted(set(SUPPORTED_TYPES.keys())))
        raise HTTPException(
            status_code=400, detail=f"Unsupported file type. Allowed: {allowed}"
        )

    suffix = Path(upload_file.filename).suffix or ".tmp"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await upload_file.read())
            tmp_path = tmp.name

        extraction = extract_text_from_file(tmp_path, mime_type)
        if not extraction.get("success"):
            detail = extraction.get("error") or "Could not extract text from file"
            if detail == "password_protected":
                detail = (
                    "The uploaded file is password-protected and cannot be processed."
                )
            raise HTTPException(status_code=400, detail=detail)

        text = (extraction.get("text") or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Extracted file text is empty")

        # Keep prompt payload bounded and stable.
        text = text[:MAX_SCENARIO_REFERENCE_CHARS]
        return upload_file.filename, text
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── Auth guard ────────────────────────────────────────────────────────────────


def require_admin(request: Request):
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def require_internal_token(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not INTERNAL_API_TOKEN or token != INTERNAL_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# ── Login / Logout ────────────────────────────────────────────────────────────


class AdminLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def admin_login(body: AdminLoginRequest, request: Request):
    if body.email != ADMIN_EMAIL or body.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
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
    active_users = (
        db.query(func.count(Profile.id)).filter(Profile.is_active == True).scalar()
    )
    inactive_users = total_users - active_users

    new_orgs_7d = (
        db.query(func.count(Organization.id))
        .filter(Organization.created_at >= week_ago)
        .scalar()
    )
    new_orgs_30d = (
        db.query(func.count(Organization.id))
        .filter(Organization.created_at >= month_ago)
        .scalar()
    )
    new_users_7d = (
        db.query(func.count(Profile.id)).filter(Profile.created_at >= week_ago).scalar()
    )
    new_users_30d = (
        db.query(func.count(Profile.id))
        .filter(Profile.created_at >= month_ago)
        .scalar()
    )

    total_documents = db.query(func.count(Document.id)).scalar()
    total_roles = db.query(func.count(Role.id)).scalar()

    avg_users_per_org = round(total_users / total_orgs, 1) if total_orgs else 0

    # ── MessageLog KPIs ───────────────────────────────────────────────────────
    messages_7d = (
        db.query(func.count(MessageLog.id))
        .filter(MessageLog.created_at >= week_ago)
        .scalar()
    )
    messages_30d = (
        db.query(func.count(MessageLog.id))
        .filter(MessageLog.created_at >= month_ago)
        .scalar()
    )
    voice_notes_7d = (
        db.query(func.count(MessageLog.id))
        .filter(MessageLog.created_at >= week_ago, MessageLog.is_voice_note == True)
        .scalar()
    )
    voice_notes_30d = (
        db.query(func.count(MessageLog.id))
        .filter(MessageLog.created_at >= month_ago, MessageLog.is_voice_note == True)
        .scalar()
    )
    rag_queries_7d = (
        db.query(func.count(MessageLog.id))
        .filter(MessageLog.created_at >= week_ago, MessageLog.is_rag_query == True)
        .scalar()
    )
    errors_7d = (
        db.query(func.count(MessageLog.id))
        .filter(MessageLog.created_at >= week_ago, MessageLog.is_error == True)
        .scalar()
    )
    truly_active_users_7d = (
        db.query(func.count(distinct(MessageLog.phone_number)))
        .filter(MessageLog.created_at >= week_ago)
        .scalar()
    )

    avg_response_ms_row = (
        db.query(func.avg(MessageLog.response_time_ms))
        .filter(
            MessageLog.created_at >= month_ago,
            MessageLog.response_time_ms.isnot(None),
            MessageLog.is_error == False,
        )
        .scalar()
    )
    avg_response_ms = int(avg_response_ms_row) if avg_response_ms_row else None

    # Documents uploaded this period (from Document table)
    docs_uploaded_7d = (
        db.query(func.count(Document.id))
        .filter(Document.created_at >= week_ago)
        .scalar()
    )
    docs_uploaded_30d = (
        db.query(func.count(Document.id))
        .filter(Document.created_at >= month_ago)
        .scalar()
    )

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
            pinecone_vector_count = stats.get("total_vector_count") or sum(
                ns.get("vector_count", 0) for ns in stats.get("namespaces", {}).values()
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
        user_count = (
            db.query(func.count(Profile.id)).filter(Profile.org_id == org.id).scalar()
        )
        active_count = (
            db.query(func.count(Profile.id))
            .filter(Profile.org_id == org.id, Profile.is_active == True)
            .scalar()
        )
        doc_count = (
            db.query(func.count(Document.id)).filter(Document.org_id == org.id).scalar()
        )
        owner = (
            db.query(User).filter(User.id == org.owner_id).first()
            if org.owner_id
            else None
        )
        result.append(
            {
                "id": str(org.id),
                "name": org.name,
                "owner_email": owner.email if owner else None,
                "user_count": user_count,
                "active_user_count": active_count,
                "document_count": doc_count,
                "twilio_number": org.twilio_number,
                "created_at": org.created_at.isoformat(),
            }
        )
    return result


class UpdateOrganizationRequest(BaseModel):
    name: Optional[str] = None
    twilio_number: Optional[str] = None


@router.get("/organizations/full-profile")
def get_org_full_profile(
    admin_email: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_internal_token(request)

    user = db.query(User).filter(User.email == admin_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found with that email")

    # Prefer the profile where the user has an Admin role; fall back to first profile
    profiles_for_user = db.query(Profile).filter(Profile.user_id == user.id).all()
    if not profiles_for_user:
        raise HTTPException(status_code=404, detail="No organization found for this user")

    target_profile = None
    for p in profiles_for_user:
        if p.role_id:
            role = db.query(Role).filter(Role.id == p.role_id).first()
            if role and role.name.lower() == "admin":
                target_profile = p
                break
    if target_profile is None:
        target_profile = profiles_for_user[0]

    org = db.query(Organization).filter(Organization.id == target_profile.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org_id = org.id

    # ── Members ──────────────────────────────────────────────────────────────
    all_profiles = db.query(Profile).filter(Profile.org_id == org_id).all()
    members = []
    for p in all_profiles:
        u = db.query(User).filter(User.id == p.user_id).first()
        role = db.query(Role).filter(Role.id == p.role_id).first() if p.role_id else None
        members.append(
            {
                "profile_id": str(p.id),
                "user_id": str(p.user_id),
                "email": u.email if u else None,
                "username": p.username,
                "full_name": p.full_name,
                "job_title": p.job_title,
                "whatsapp_number": p.whatsapp_number,
                "role_name": role.name if role else None,
                "permissions": role.permissions if role else [],
                "is_active": p.is_active,
                "settings": p.settings,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
        )

    # ── Roles ─────────────────────────────────────────────────────────────────
    all_roles = db.query(Role).filter(Role.org_id == org_id).all()
    roles = []
    for r in all_roles:
        member_count = (
            db.query(func.count(Profile.id))
            .filter(Profile.role_id == r.id)
            .scalar()
        )
        roles.append(
            {
                "id": str(r.id),
                "name": r.name,
                "permissions": r.permissions,
                "member_count": member_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )

    # ── Documents ─────────────────────────────────────────────────────────────
    all_docs = db.query(Document).filter(Document.org_id == org_id).all()
    documents = [
        {
            "id": str(d.id),
            "name": d.name,
            "location": d.location,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "cloudinary_url": d.cloudinary_url,
            "vector_id": d.vector_id,
            "uploaded_by": d.uploaded_by,
            "upload_source": d.upload_source,
            "drive_file_id": d.drive_file_id,
            "resource_type": d.resource_type,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in all_docs
    ]

    # ── Knowledge Base Summary ────────────────────────────────────────────────
    kb_docs = [d for d in all_docs if d.location == "knowledgebase"]
    kb_total_size = sum(d.file_size or 0 for d in kb_docs)
    _kb_known_types = {"pdf", "docx", "pptx", "xlsx"}
    kb_by_type: dict = {}
    for d in kb_docs:
        ft = (d.file_type or "").lower()
        bucket = ft if ft in _kb_known_types else "other"
        kb_by_type[bucket] = kb_by_type.get(bucket, 0) + 1

    kb_uploads_by_day_rows = (
        db.query(
            func.date(Document.created_at).label("day"),
            func.count(Document.id).label("count"),
        )
        .filter(Document.org_id == org_id, Document.location == "knowledgebase")
        .group_by(func.date(Document.created_at))
        .order_by(func.date(Document.created_at))
        .all()
    )
    kb_uploads_over_time = [
        {"date": str(r.day), "count": r.count} for r in kb_uploads_by_day_rows
    ]

    knowledge_base_summary = {
        "total_count": len(kb_docs),
        "total_size_bytes": kb_total_size,
        "by_file_type": kb_by_type,
        "uploads_over_time": kb_uploads_over_time,
    }

    # ── Coaching Scenarios ────────────────────────────────────────────────────
    all_scenarios = (
        db.query(CoachingScenario).filter(CoachingScenario.org_id == org_id).all()
    )
    coaching_scenarios = []
    for s in all_scenarios:
        session_count = (
            db.query(func.count(CoachingSession.id))
            .filter(CoachingSession.scenario_id == s.id)
            .scalar()
            or 0
        )
        ref_files = (
            db.query(CoachingScenarioReferenceFile)
            .filter(CoachingScenarioReferenceFile.scenario_id == s.id)
            .all()
        )
        coaching_scenarios.append(
            {
                "id": str(s.id),
                "name": s.name,
                "description": getattr(s, "description", None),
                "system_prompt": s.system_prompt,
                "is_active": s.is_active,
                "usecase_api_id": s.usecase_api_id,
                "session_count": session_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "reference_files": [
                    {"id": str(f.id), "file_name": f.file_name} for f in ref_files
                ],
            }
        )

    # ── Coaching Sessions ─────────────────────────────────────────────────────
    all_sessions = (
        db.query(CoachingSession).filter(CoachingSession.org_id == org_id).all()
    )
    coaching_sessions = [
        {
            "id": str(s.id),
            "phone_number": s.phone_number,
            "scenario_name": s.scenario_name,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "report_text": s.report_text,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in all_sessions
    ]

    # ── Groups ────────────────────────────────────────────────────────────────
    all_groups = db.query(Group).filter(Group.org_id == org_id).all()
    groups = []
    for g in all_groups:
        member_count = (
            db.query(func.count(GroupMember.id))
            .filter(GroupMember.group_id == g.id)
            .scalar()
        )
        groups.append(
            {
                "id": str(g.id),
                "name": g.name,
                "member_count": member_count,
                "created_by_id": str(g.created_by_id) if g.created_by_id else None,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
        )

    # ── Message Templates ─────────────────────────────────────────────────────
    all_templates = (
        db.query(MessageTemplate).filter(MessageTemplate.org_id == org_id).all()
    )
    message_templates = [
        {
            "id": str(t.id),
            "name": t.name,
            "content": t.content,
            "variables": t.variables,
            "media_url": t.media_url,
            "is_active": t.is_active,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in all_templates
    ]

    # ── Broadcast Schedules ───────────────────────────────────────────────────
    all_broadcasts = (
        db.query(BroadcastSchedule).filter(BroadcastSchedule.org_id == org_id).all()
    )
    broadcast_schedules = []
    for b in all_broadcasts:
        tmpl = (
            db.query(MessageTemplate).filter(MessageTemplate.id == b.template_id).first()
            if b.template_id
            else None
        )
        grp = (
            db.query(Group).filter(Group.id == b.group_id).first()
            if b.group_id
            else None
        )
        broadcast_schedules.append(
            {
                "id": str(b.id),
                "template_name": tmpl.name if tmpl else None,
                "group_name": grp.name if grp else None,
                "scheduled_at": b.scheduled_at.isoformat() if b.scheduled_at else None,
                "status": b.status,
                "sent_count": b.sent_count,
                "failed_count": b.failed_count,
                "sent_at": b.sent_at.isoformat() if b.sent_at else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
        )

    # ── Message Logs (aggregates) ─────────────────────────────────────────────
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    ml_total = (
        db.query(func.count(MessageLog.id)).filter(MessageLog.org_id == org_id).scalar()
    )
    ml_recent = (
        db.query(func.count(MessageLog.id))
        .filter(MessageLog.org_id == org_id, MessageLog.created_at >= thirty_days_ago)
        .scalar()
    )
    ml_rag = (
        db.query(func.count(MessageLog.id))
        .filter(MessageLog.org_id == org_id, MessageLog.is_rag_query == True)
        .scalar()
    )
    ml_errors = (
        db.query(func.count(MessageLog.id))
        .filter(MessageLog.org_id == org_id, MessageLog.is_error == True)
        .scalar()
    )
    ml_type_rows = (
        db.query(MessageLog.message_type, func.count(MessageLog.id).label("cnt"))
        .filter(MessageLog.org_id == org_id)
        .group_by(MessageLog.message_type)
        .all()
    )
    ml_by_type = {r.message_type: r.cnt for r in ml_type_rows}

    message_logs = {
        "total": ml_total,
        "recent_30_days": ml_recent,
        "rag_queries": ml_rag,
        "errors": ml_errors,
        "by_type": ml_by_type,
    }

    # ── WhatsApp Messages (aggregates + sample) ───────────────────────────────
    wm_total = (
        db.query(func.count(WhatsAppMessage.id))
        .filter(WhatsAppMessage.org_id == org_id)
        .scalar()
    )
    wm_role_rows = (
        db.query(WhatsAppMessage.role, func.count(WhatsAppMessage.id).label("cnt"))
        .filter(WhatsAppMessage.org_id == org_id)
        .group_by(WhatsAppMessage.role)
        .all()
    )
    wm_by_role = {r.role: r.cnt for r in wm_role_rows}
    wm_recent = (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.org_id == org_id)
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(5)
        .all()
    )
    wm_sample = [
        {
            "phone_number": m.phone_number,
            "role": m.role,
            "content_preview": m.content[:200] if m.content else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in wm_recent
    ]

    whatsapp_messages = {
        "total": wm_total,
        "by_role": wm_by_role,
        "sample_recent": wm_sample,
    }

    # ── Redis State (per member) ──────────────────────────────────────────────
    redis_members = []
    phone_numbers = [p["whatsapp_number"] for p in members if p["whatsapp_number"]]
    if phone_numbers:
        r = _get_redis()
        pipe = r.pipeline(transaction=False)
        for phone in phone_numbers:
            pipe.llen(f"fp-chatHistory:{phone}")
            pipe.get(f"session_facts:{phone}")
            pipe.get(f"user:lang:{phone}")
            pipe.exists(f"coaching:session:{phone}")
            pipe.get(f"rate_limit:{phone}")
        results = pipe.execute()
        for i, phone in enumerate(phone_numbers):
            base = i * 5
            raw_facts = results[base + 1]
            try:
                facts = _json.loads(raw_facts) if raw_facts else []
            except Exception:
                facts = []
            redis_members.append(
                {
                    "whatsapp_number": phone,
                    "chat_history_length": results[base] or 0,
                    "session_facts": facts,
                    "language_preference": (results[base + 2] or b"").decode() or None,
                    "has_active_coaching_session": bool(results[base + 3]),
                    "rate_limit_count": int(results[base + 4]) if results[base + 4] else 0,
                }
            )

    redis_state = {"members": redis_members}

    # ── Stats Summary ─────────────────────────────────────────────────────────
    stats = {
        "total_members": len(all_profiles),
        "active_members": sum(1 for p in all_profiles if p.is_active),
        "total_documents": len(all_docs),
        "knowledgebase_docs": len(kb_docs),
        "datastore_docs": len([d for d in all_docs if d.location == "datastore"]),
        "total_roles": len(all_roles),
        "total_groups": len(all_groups),
        "total_coaching_scenarios": len(all_scenarios),
        "total_coaching_sessions": len(all_sessions),
        "total_message_logs": ml_total,
        "total_whatsapp_messages": wm_total,
        "total_broadcasts": len(all_broadcasts),
    }

    owner_user = (
        db.query(User).filter(User.id == org.owner_id).first() if org.owner_id else None
    )

    return {
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "owner_email": owner_user.email if owner_user else None,
            "twilio_number": org.twilio_number,
            "settings": org.settings,
            "created_at": org.created_at.isoformat() if org.created_at else None,
        },
        "stats": stats,
        "members": members,
        "roles": roles,
        "documents": documents,
        "knowledge_base_summary": knowledge_base_summary,
        "coaching_scenarios": coaching_scenarios,
        "coaching_sessions": coaching_sessions,
        "groups": groups,
        "message_templates": message_templates,
        "broadcast_schedules": broadcast_schedules,
        "message_logs": message_logs,
        "whatsapp_messages": whatsapp_messages,
        "redis_state": redis_state,
    }


@router.get("/organizations/{org_id}")
def get_organization(org_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin(request)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    owner = (
        db.query(User).filter(User.id == org.owner_id).first() if org.owner_id else None
    )
    return {
        "id": str(org.id),
        "name": org.name,
        "twilio_number": org.twilio_number,
        "owner_email": owner.email if owner else None,
        "created_at": org.created_at.isoformat(),
    }


@router.patch("/organizations/{org_id}")
def update_organization(
    org_id: str,
    body: UpdateOrganizationRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if body.name is not None:
        if not body.name.strip():
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        org.name = body.name.strip()

    if body.twilio_number is not None:
        cleaned = body.twilio_number.strip()
        if cleaned and not cleaned.startswith("whatsapp:+"):
            raise HTTPException(
                status_code=400,
                detail="twilio_number must be in format 'whatsapp:+<digits>' or empty to clear",
            )
        if cleaned:
            conflict = (
                db.query(Organization)
                .filter(
                    Organization.twilio_number == cleaned,
                    Organization.id != org.id,
                )
                .first()
            )
            if conflict:
                raise HTTPException(
                    status_code=409,
                    detail=f"Number already assigned to organization '{conflict.name}'",
                )
        org.twilio_number = cleaned or None

    db.commit()
    db.refresh(org)
    return {
        "id": str(org.id),
        "name": org.name,
        "twilio_number": org.twilio_number,
    }


# ── Users ─────────────────────────────────────────────────────────────────────


@router.get("/users")
def list_all_users(request: Request, db: Session = Depends(get_db)):
    require_admin(request)

    profiles = db.query(Profile).order_by(Profile.created_at.desc()).all()
    result = []
    for p in profiles:
        user = db.query(User).filter(User.id == p.user_id).first()
        org = db.query(Organization).filter(Organization.id == p.org_id).first()
        role = (
            db.query(Role).filter(Role.id == p.role_id).first() if p.role_id else None
        )
        result.append(
            {
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
            }
        )
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
        raise HTTPException(
            status_code=400, detail="Password must be at least 6 characters"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = get_password_hash(body.new_password)
    db.commit()
    return {"ok": True}


# ── Toggle active ─────────────────────────────────────────────────────────────


@router.patch("/users/{profile_id}/active")
def toggle_user_active(
    profile_id: str, request: Request, db: Session = Depends(get_db)
):
    require_admin(request)

    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.is_active = not profile.is_active
    db.commit()
    return {"is_active": profile.is_active}


# ── Delete user ────────────────────────────────────────────────────────────────


@router.delete("/users/{user_id}")
def delete_user(user_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin(request)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Clear owner_id references so org deletion isn't blocked
    db.query(Organization).filter(Organization.owner_id == user.id).update(
        {"owner_id": None}, synchronize_session=False
    )
    db.delete(user)  # cascades to Profile via relationship
    db.commit()
    return {"ok": True}


# ── Delete organization ────────────────────────────────────────────────────────


@router.delete("/organizations/{org_id}")
def delete_organization(org_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin(request)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Collect user_ids belonging solely to this org before cascade removes profiles
    profiles = db.query(Profile).filter(Profile.org_id == org.id).all()
    sole_user_ids = []
    for p in profiles:
        other = (
            db.query(Profile)
            .filter(Profile.user_id == p.user_id, Profile.org_id != org.id)
            .first()
        )
        if not other:
            sole_user_ids.append(p.user_id)

    db.delete(org)  # cascades to Profiles, Roles, Documents
    db.flush()

    # Delete users that no longer have any profile
    for uid in sole_user_ids:
        u = db.query(User).filter(User.id == uid).first()
        if u:
            db.delete(u)

    db.commit()
    return {"ok": True}


# ── Menu options toggle ───────────────────────────────────────────────────────


@router.get("/menu-options")
def get_menu_options(request: Request):
    require_admin(request)
    state = _default_menu_options()
    try:
        rc = _get_redis()
        raw = rc.get(MENU_OPTIONS_KEY)
        if raw:
            loaded = _json.loads(raw)
            if isinstance(loaded, dict):
                state = {k: bool(loaded.get(k, True)) for k in _ALL_MENU_OPTIONS}
    except (
        _redis_lib.exceptions.RedisError,
        _json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as e:
        print(f"get_menu_options redis fallback: {e}")
    return state


@router.post("/menu-options")
async def set_menu_options(request: Request):
    require_admin(request)
    body = await request.json()
    # Expect {"1": true/false, "2": true/false, ...}
    state = {k: bool(body.get(k, True)) for k in _ALL_MENU_OPTIONS}
    try:
        rc = _get_redis()
        rc.set(MENU_OPTIONS_KEY, _json.dumps(state))
    except _redis_lib.exceptions.RedisError as e:
        print(f"set_menu_options redis write skipped: {e}")
    return state


# ── AI Provider Config ────────────────────────────────────────────────────────

_AI_CONFIG_KEY = "admin:ai_config"
_VALID_PROVIDERS = {"anthropic", "openai", "google"}
_DEFAULT_AI_CONFIG = {"provider": "anthropic", "model": "claude-sonnet-4-6"}


@router.get("/ai-config")
def get_ai_config(request: Request):
    require_admin(request)
    config = _DEFAULT_AI_CONFIG.copy()
    try:
        rc = _get_redis()
        raw = rc.get(_AI_CONFIG_KEY)
        if raw:
            loaded = _json.loads(raw)
            if isinstance(loaded, dict) and "provider" in loaded and "model" in loaded:
                config = loaded
    except Exception as e:
        print(f"get_ai_config redis fallback: {e}")
    return config


@router.post("/ai-config")
async def set_ai_config(request: Request):
    require_admin(request)
    body = await request.json()
    provider = str(body.get("provider", "anthropic")).strip().lower()
    model = str(body.get("model", "")).strip()
    if provider not in _VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Choose from: {', '.join(sorted(_VALID_PROVIDERS))}",
        )
    if not model:
        raise HTTPException(status_code=400, detail="model cannot be empty")
    config = {"provider": provider, "model": model}
    try:
        _get_redis().set(_AI_CONFIG_KEY, _json.dumps(config))
    except Exception as e:
        print(f"set_ai_config redis skipped: {e}")
    return config


# ── Scenarios (superadmin view) ───────────────────────────────────────────────


@router.get("/scenarios")
def list_all_scenarios(request: Request, db: Session = Depends(get_db)):
    require_admin(request)

    scenarios = (
        db.query(CoachingScenario).order_by(CoachingScenario.created_at.desc()).all()
    )
    result = []
    for s in scenarios:
        org = db.query(Organization).filter(Organization.id == s.org_id).first()
        session_count = (
            db.query(func.count(CoachingSession.id))
            .filter(CoachingSession.scenario_id == s.id)
            .scalar()
            or 0
        )
        ref_files = (
            db.query(CoachingScenarioReferenceFile)
            .filter(CoachingScenarioReferenceFile.scenario_id == s.id)
            .all()
        )
        saved_files = [{"file_name": f.file_name, "id": str(f.id)} for f in ref_files]
        result.append(
            {
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "system_prompt": s.system_prompt,
                "reference_files": saved_files,
                "reference_files_count": len(saved_files),
                "is_active": s.is_active,
                "usecase_api_id": s.usecase_api_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "org_id": str(s.org_id),
                "org_name": org.name if org else None,
                "session_count": session_count,
            }
        )
    return result


@router.post("/scenarios")
async def admin_create_scenario(request: Request, db: Session = Depends(get_db)):
    require_admin(request)

    body, reference_files = await _parse_scenario_request(request)
    name = (body.get("name") or "").strip()
    system_prompt = (body.get("system_prompt") or "").strip()
    org_id = (body.get("org_id") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not system_prompt:
        raise HTTPException(status_code=400, detail="system_prompt is required")
    if not org_id:
        raise HTTPException(status_code=400, detail="org_id is required")
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    raw_api_id = body.get("usecase_api_id")
    usecase_api_id = int(raw_api_id) if raw_api_id else None

    scenario = CoachingScenario(
        org_id=org.id,
        name=name,
        description=(body.get("description") or "").strip() or None,
        system_prompt=system_prompt,
        is_active=_to_bool(body.get("is_active"), default=True),
        usecase_api_id=usecase_api_id,
    )
    db.add(scenario)
    db.flush()

    saved_files = []
    for ref_file in reference_files:
        if ref_file and getattr(ref_file, "filename", ""):
            file_name, file_text = await _extract_reference_file(ref_file)
            ref = CoachingScenarioReferenceFile(
                scenario_id=scenario.id,
                file_name=file_name,
                file_text=file_text,
            )
            db.add(ref)
            saved_files.append({"file_name": file_name, "id": str(ref.id)})

    db.commit()
    db.refresh(scenario)
    return {
        "id": str(scenario.id),
        "name": scenario.name,
        "description": scenario.description,
        "system_prompt": scenario.system_prompt,
        "reference_files": saved_files,
        "reference_files_count": len(saved_files),
        "is_active": scenario.is_active,
        "usecase_api_id": scenario.usecase_api_id,
        "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
        "org_id": str(scenario.org_id),
        "org_name": org.name,
        "session_count": 0,
    }


@router.patch("/scenarios/{scenario_id}")
async def admin_update_scenario(
    scenario_id: str, request: Request, db: Session = Depends(get_db)
):
    require_admin(request)

    body, reference_files = await _parse_scenario_request(request)
    scenario = (
        db.query(CoachingScenario).filter(CoachingScenario.id == scenario_id).first()
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if "name" in body and body["name"]:
        scenario.name = body["name"].strip()
    if "description" in body:
        scenario.description = (body["description"] or "").strip() or None
    if "system_prompt" in body and body["system_prompt"]:
        scenario.system_prompt = body["system_prompt"].strip()
    if _to_bool(body.get("clear_reference_file"), default=False):
        db.query(CoachingScenarioReferenceFile).filter(
            CoachingScenarioReferenceFile.scenario_id == scenario.id
        ).delete(synchronize_session=False)
    for ref_file in reference_files:
        if ref_file and getattr(ref_file, "filename", ""):
            file_name, file_text = await _extract_reference_file(ref_file)
            ref = CoachingScenarioReferenceFile(
                scenario_id=scenario.id,
                file_name=file_name,
                file_text=file_text,
            )
            db.add(ref)
    if "is_active" in body:
        scenario.is_active = _to_bool(body["is_active"], default=scenario.is_active)
    if "usecase_api_id" in body:
        val = body["usecase_api_id"]
        scenario.usecase_api_id = int(val) if val else None
    if "org_id" in body and body["org_id"]:
        org = db.query(Organization).filter(Organization.id == body["org_id"]).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        scenario.org_id = org.id
    db.commit()
    db.refresh(scenario)
    org = db.query(Organization).filter(Organization.id == scenario.org_id).first()

    ref_files = (
        db.query(CoachingScenarioReferenceFile)
        .filter(CoachingScenarioReferenceFile.scenario_id == scenario.id)
        .all()
    )
    saved_files = [{"file_name": f.file_name, "id": str(f.id)} for f in ref_files]
    return {
        "id": str(scenario.id),
        "name": scenario.name,
        "description": scenario.description,
        "system_prompt": scenario.system_prompt,
        "reference_files": saved_files,
        "reference_files_count": len(saved_files),
        "is_active": scenario.is_active,
        "usecase_api_id": scenario.usecase_api_id,
        "org_id": str(scenario.org_id),
        "org_name": org.name if org else None,
    }


@router.delete("/scenarios/{scenario_id}")
def admin_delete_scenario(
    scenario_id: str, request: Request, db: Session = Depends(get_db)
):
    require_admin(request)

    scenario = (
        db.query(CoachingScenario).filter(CoachingScenario.id == scenario_id).first()
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    db.delete(scenario)
    db.commit()
    return {"deleted": scenario_id}


@router.get("/scenarios/{scenario_id}/reference-files")
def list_scenario_reference_files(
    scenario_id: str, request: Request, db: Session = Depends(get_db)
):
    require_admin(request)

    scenario = (
        db.query(CoachingScenario).filter(CoachingScenario.id == scenario_id).first()
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    ref_files = (
        db.query(CoachingScenarioReferenceFile)
        .filter(CoachingScenarioReferenceFile.scenario_id == scenario.id)
        .all()
    )
    return [
        {
            "id": str(f.id),
            "file_name": f.file_name,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in ref_files
    ]


@router.delete("/scenarios/{scenario_id}/reference-files/{file_id}")
def delete_scenario_reference_file(
    scenario_id: str, file_id: str, request: Request, db: Session = Depends(get_db)
):
    require_admin(request)

    scenario = (
        db.query(CoachingScenario).filter(CoachingScenario.id == scenario_id).first()
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    ref_file = (
        db.query(CoachingScenarioReferenceFile)
        .filter(
            CoachingScenarioReferenceFile.id == file_id,
            CoachingScenarioReferenceFile.scenario_id == scenario.id,
        )
        .first()
    )
    if not ref_file:
        raise HTTPException(status_code=404, detail="Reference file not found")
    db.delete(ref_file)
    db.commit()
    return {"deleted": file_id}


import re


def _extract_template_variables(content: str) -> list[str]:
    """Extract {{1}}, {{2}}, etc. from template content."""
    matches = re.findall(r"\{\{(\d+)\}\}", content)
    return sorted(set(matches), key=lambda x: int(x))


# ── Message Templates (superadmin) ───────────────────────────────────────────


class CreateTemplateRequest(BaseModel):
    name: str
    content: str
    org_id: Optional[str] = None
    media_url: Optional[str] = None


@router.get("/templates")
def list_templates(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    templates = (
        db.query(MessageTemplate).order_by(MessageTemplate.created_at.desc()).all()
    )
    result = []
    for t in templates:
        org = (
            db.query(Organization).filter(Organization.id == t.org_id).first()
            if t.org_id
            else None
        )
        result.append(
            {
                "id": str(t.id),
                "name": t.name,
                "content": t.content,
                "variables": t.variables or [],
                "media_url": t.media_url,
                "is_active": t.is_active,
                "org_id": str(t.org_id) if t.org_id else None,
                "org_name": org.name if org else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
        )
    return result


@router.post("/templates")
def create_template(
    body: CreateTemplateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request)

    if not body.name:
        raise HTTPException(status_code=400, detail="name is required")
    if not body.content:
        raise HTTPException(status_code=400, detail="content is required")

    variables = _extract_template_variables(body.content)
    template = MessageTemplate(
        name=body.name,
        content=body.content,
        variables=variables,
        org_id=body.org_id,
        media_url=body.media_url,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {
        "id": str(template.id),
        "name": template.name,
        "content": template.content,
        "variables": template.variables or [],
        "media_url": template.media_url,
        "is_active": template.is_active,
        "org_id": str(template.org_id) if template.org_id else None,
        "created_at": template.created_at.isoformat() if template.created_at else None,
    }


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request)
    body = await request.json()

    template = (
        db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if "name" in body:
        template.name = body["name"]
    if "content" in body:
        template.content = body["content"]
        template.variables = _extract_template_variables(body["content"])
    if "is_active" in body:
        template.is_active = body["is_active"]
    if "media_url" in body:
        template.media_url = body["media_url"]  # accepts null to clear

    db.commit()
    db.refresh(template)
    return {
        "id": str(template.id),
        "name": template.name,
        "content": template.content,
        "variables": template.variables or [],
        "media_url": template.media_url,
        "is_active": template.is_active,
    }


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request)

    template = (
        db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()
    return {"deleted": template_id}
