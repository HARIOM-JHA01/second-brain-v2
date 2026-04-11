"""
Rolplay Super-Admin API
Access: session-based (ADMIN_EMAIL / ADMIN_PASSWORD from env).
All routes under /admin/api/* require is_admin=True in session.
"""

import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from agente_rolplay.config import ADMIN_EMAIL, ADMIN_PASSWORD
from agente_rolplay.db.auth import get_password_hash
from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import (
    CoachingScenario,
    CoachingScenarioReferenceFile,
    CoachingSession,
    Document,
    MessageLog,
    Organization,
    Profile,
    Role,
    User,
)
from agente_rolplay.storage.file_processor import (
    SUPPORTED_TYPES,
    extract_text_from_file,
)

router = APIRouter(prefix="/admin/api", tags=["admin"])
MAX_SCENARIO_REFERENCE_CHARS = 50000


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
                "created_at": org.created_at.isoformat(),
            }
        )
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

    scenario = CoachingScenario(
        org_id=org.id,
        name=name,
        description=(body.get("description") or "").strip() or None,
        system_prompt=system_prompt,
        is_active=_to_bool(body.get("is_active"), default=True),
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
