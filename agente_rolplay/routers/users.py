import csv
import io
import json
import re
import secrets
from datetime import datetime, timedelta

import redis as redis_lib
from fastapi import APIRouter, Body, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Any, Dict, List

from agente_rolplay.db.auth import get_current_user, get_password_hash
from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import (
    BroadcastSchedule,
    CoachingScenario,
    Document,
    Group,
    GroupMember,
    MessageLog,
    MessageTemplate,
    User,
    Profile,
    Organization,
    Role,
    WhatsAppMessage,
)
from agente_rolplay.db.schemas import (
    ProfileResponse,
    ProfileCreate,
    ProfileUpdate,
    ProfileWithUser,
    RoleResponse,
    UserResponse,
)
from agente_rolplay.db.whatsapp_auth import normalize_whatsapp_number
from agente_rolplay.agent.provider_adapter import create_message
from agente_rolplay.config import redis_connection_kwargs, HAIKU_MODEL_NAME

router = APIRouter(prefix="/api/users", tags=["users"])

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_ALLOWED_FONT_FAMILIES = {"inter", "poppins", "manrope", "source_sans_3"}
_ALLOWED_FONT_SCALES = {"small", "medium", "large"}
_ALLOWED_THEME_MODES = {"dark", "light"}
_ALLOWED_LANGUAGES = {"es", "en"}
_CUSTOMIZE_DEFAULTS = {
    "primary_color": "#dc2626",
    "secondary_color": "#991b1b",
    "tertiary_color": "#fca5a5",
    "font_family": "inter",
    "font_scale": "medium",
    "theme_mode": "dark",
    "language": "es",
}


def _normalize_customize_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    def _get_str(key: str, default: str) -> str:
        value = payload.get(key, default)
        return str(value).strip() if value is not None else default

    normalized = {
        "primary_color": _get_str(
            "primary_color", _CUSTOMIZE_DEFAULTS["primary_color"]
        ),
        "secondary_color": _get_str(
            "secondary_color", _CUSTOMIZE_DEFAULTS["secondary_color"]
        ),
        "tertiary_color": _get_str(
            "tertiary_color", _CUSTOMIZE_DEFAULTS["tertiary_color"]
        ),
        "font_family": _get_str("font_family", _CUSTOMIZE_DEFAULTS["font_family"]),
        "font_scale": _get_str("font_scale", _CUSTOMIZE_DEFAULTS["font_scale"]),
        "theme_mode": _get_str("theme_mode", _CUSTOMIZE_DEFAULTS["theme_mode"]),
        "language": _get_str("language", _CUSTOMIZE_DEFAULTS["language"]),
    }
    return normalized


def _validate_customize_payload(payload: Dict[str, str]) -> None:
    for color_key in ("primary_color", "secondary_color", "tertiary_color"):
        if not _HEX_COLOR_RE.match(payload[color_key]):
            raise HTTPException(
                status_code=400,
                detail=f"{color_key} must be a valid hex color in #RRGGBB format",
            )
    if payload["font_family"] not in _ALLOWED_FONT_FAMILIES:
        raise HTTPException(
            status_code=400,
            detail=f"font_family must be one of: {', '.join(sorted(_ALLOWED_FONT_FAMILIES))}",
        )
    if payload["font_scale"] not in _ALLOWED_FONT_SCALES:
        raise HTTPException(
            status_code=400,
            detail=f"font_scale must be one of: {', '.join(sorted(_ALLOWED_FONT_SCALES))}",
        )
    if payload["theme_mode"] not in _ALLOWED_THEME_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"theme_mode must be one of: {', '.join(sorted(_ALLOWED_THEME_MODES))}",
        )
    if payload["language"] not in _ALLOWED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"language must be one of: {', '.join(sorted(_ALLOWED_LANGUAGES))}",
        )


def _extract_customization(profile: Profile) -> Dict[str, Any]:
    settings = profile.settings if isinstance(profile.settings, dict) else {}
    raw_customize = settings.get("customize", {})
    if not isinstance(raw_customize, dict):
        raw_customize = {}

    normalized = _normalize_customize_payload(raw_customize)
    try:
        _validate_customize_payload(normalized)
    except HTTPException:
        normalized = dict(_CUSTOMIZE_DEFAULTS)
    response = {**normalized}

    updated_at = raw_customize.get("updated_at")
    if isinstance(updated_at, str) and updated_at.strip():
        response["updated_at"] = updated_at.strip()
    return response


def get_org_for_user(db: Session, user_id: UUID) -> Organization:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    org = db.query(Organization).filter(Organization.id == profile.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


# ── Literal routes MUST come before /{user_id} ───────────────────────────────


@router.get("/customization")
def get_customization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _extract_customization(profile)


@router.put("/customization")
def update_customization(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    normalized = _normalize_customize_payload(payload)
    _validate_customize_payload(normalized)

    settings = profile.settings if isinstance(profile.settings, dict) else {}
    settings = dict(settings)
    settings["customize"] = {
        **normalized,
        "updated_at": datetime.utcnow().isoformat(),
    }
    profile.settings = settings
    db.commit()
    db.refresh(profile)
    return _extract_customization(profile)


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

    total_users = (
        db.query(func.count(Profile.id)).filter(Profile.org_id == org_id).scalar()
    )
    active_users = (
        db.query(func.count(Profile.id))
        .filter(Profile.org_id == org_id, Profile.is_active == True)
        .scalar()
    )
    new_users_7d = (
        db.query(func.count(Profile.id))
        .filter(Profile.org_id == org_id, Profile.created_at >= week_ago)
        .scalar()
    )
    new_users_30d = (
        db.query(func.count(Profile.id))
        .filter(Profile.org_id == org_id, Profile.created_at >= month_ago)
        .scalar()
    )
    total_roles = db.query(func.count(Role.id)).filter(Role.org_id == org_id).scalar()
    total_docs = (
        db.query(func.count(Document.id)).filter(Document.org_id == org_id).scalar()
    )

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
        messages_7d = (
            db.query(func.count(MessageLog.id))
            .filter(
                MessageLog.created_at >= week_ago,
                MessageLog.phone_number.in_(org_phones),
            )
            .scalar()
            or 0
        )
        messages_30d = (
            db.query(func.count(MessageLog.id))
            .filter(
                MessageLog.created_at >= month_ago,
                MessageLog.phone_number.in_(org_phones),
            )
            .scalar()
            or 0
        )
        voice_notes_7d = (
            db.query(func.count(MessageLog.id))
            .filter(
                MessageLog.created_at >= week_ago,
                MessageLog.is_voice_note == True,
                MessageLog.phone_number.in_(org_phones),
            )
            .scalar()
            or 0
        )
        truly_active_users_7d = (
            db.query(func.count(distinct(MessageLog.phone_number)))
            .filter(
                MessageLog.created_at >= week_ago,
                MessageLog.phone_number.in_(org_phones),
            )
            .scalar()
            or 0
        )
        avg_ms_row = (
            db.query(func.avg(MessageLog.response_time_ms))
            .filter(
                MessageLog.created_at >= month_ago,
                MessageLog.phone_number.in_(org_phones),
                MessageLog.response_time_ms.isnot(None),
                MessageLog.is_error == False,
            )
            .scalar()
        )
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
            cnt = (
                db.query(func.count(MessageLog.id))
                .filter(
                    MessageLog.created_at >= month_ago,
                    MessageLog.phone_number.in_(org_phones),
                    MessageLog.message_type == msg_type,
                )
                .scalar()
                or 0
            )
            message_types_breakdown[msg_type] = cnt

    docs_uploaded_7d = (
        db.query(func.count(Document.id))
        .filter(
            Document.org_id == org_id,
            Document.created_at >= week_ago,
        )
        .scalar()
        or 0
    )
    docs_uploaded_30d = (
        db.query(func.count(Document.id))
        .filter(
            Document.org_id == org_id,
            Document.created_at >= month_ago,
        )
        .scalar()
        or 0
    )

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


@router.get("/conversation-insights", tags=["dashboard"])
def get_conversation_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    refresh: int = 0,
):
    """
    Returns AI-generated summary of what org WhatsApp users are discussing,
    plus the top 5 representative messages. Cached in Redis for 1 hour.
    Pass ?refresh=1 to invalidate the cache and regenerate.
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    org_id = profile.org_id

    # Cache check
    r = redis_lib.Redis(**redis_connection_kwargs())
    cache_key = f"insights:{org_id}"
    if refresh:
        r.delete(cache_key)
    else:
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)

    # Fetch last 7 days of user messages for this org
    week_ago = datetime.utcnow() - timedelta(days=7)
    messages = (
        db.query(WhatsAppMessage)
        .filter(
            WhatsAppMessage.org_id == org_id,
            WhatsAppMessage.role == "user",
            WhatsAppMessage.created_at >= week_ago,
        )
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(200)
        .all()
    )

    if not messages:
        return {
            "summary": None,
            "top_messages": [],
            "generated_at": None,
            "message_count": 0,
        }

    # Build prompt for Haiku
    messages_text = "\n".join(f"- {m.content}" for m in messages)
    prompt = (
        "You are analyzing WhatsApp messages sent by employees to an AI assistant.\n\n"
        f"Messages (most recent first, last 7 days):\n{messages_text}\n\n"
        "Respond in JSON with exactly this structure:\n"
        '{"summary": "<2-3 sentence summary of main topics>", '
        '"top_messages": ["<msg1>", "<msg2>", "<msg3>", "<msg4>", "<msg5>"]}\n'
        "The top_messages should be the 5 most representative or frequently appearing "
        "questions/requests. Keep each top message under 100 characters. "
        "Respond only with valid JSON, no markdown."
    )

    try:
        raw = create_message(
            provider="anthropic",
            model=HAIKU_MODEL_NAME,
            system="You are a data analyst. Return only valid JSON, no markdown code blocks.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
        )
        # Strip markdown code fences if model adds them despite instructions
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(clean)
    except Exception as e:
        print(f"[conversation-insights] AI call failed: {e!r}")
        parsed = {
            "summary": "Could not generate insights at this time.",
            "top_messages": [],
        }

    result = {
        "summary": parsed.get("summary"),
        "top_messages": parsed.get("top_messages", [])[:5],
        "generated_at": datetime.utcnow().isoformat(),
        "message_count": len(messages),
    }

    r.set(cache_key, json.dumps(result), ex=3600)
    return result


@router.get("/documents", tags=["documents"])
def list_org_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents for the current user's org (both Data Store and Knowledge Base)."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    docs = (
        db.query(Document)
        .filter(Document.org_id == profile.org_id)
        .order_by(Document.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(doc.id),
            "name": doc.name,
            "public_id": doc.drive_file_id,
            "secure_url": doc.cloudinary_url,
            "resource_type": doc.resource_type,
            "format": doc.file_type,
            "bytes": doc.file_size,
            "location": doc.location,
            "uploaded_by": doc.uploaded_by,
            "upload_source": doc.upload_source,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in docs
    ]


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


@router.get("/import-template")
def download_import_template(current_user: User = Depends(get_current_user)):
    """Return a downloadable CSV template with the expected column headers."""
    content = "whatsapp_number,full_name,username,job_title,role_name\n"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_import_template.csv"},
    )


@router.post("/import")
def import_users_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk-import users from a CSV file.

    Required column: whatsapp_number
    Optional columns: full_name, username, job_title, role_name

    Returns a per-row summary of created / skipped / failed rows.
    """
    if not (
        (file.content_type or "").startswith("text/csv")
        or (file.filename or "").lower().endswith(".csv")
    ):
        raise HTTPException(status_code=400, detail="File must be a CSV (.csv)")

    raw = file.file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or "whatsapp_number" not in [
        f.strip() for f in reader.fieldnames
    ]:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain a 'whatsapp_number' column header",
        )

    org = get_org_for_user(db, current_user.id)

    # Pre-load org roles for fast name → id lookup
    org_roles = db.query(Role).filter(Role.org_id == org.id).all()
    role_map = {r.name.lower(): r.id for r in org_roles}

    # Pre-load existing phone numbers in this org to detect DB duplicates
    existing_phones = {
        p.whatsapp_number
        for p in db.query(Profile.whatsapp_number).filter(Profile.org_id == org.id).all()
        if p.whatsapp_number
    }

    results = []
    seen_in_batch: set = set()
    created_count = skipped_count = failed_count = 0

    # Normalize fieldnames to strip surrounding whitespace
    rows = list(reader)

    for row_num, row in enumerate(rows, start=2):  # row 1 is the header
        raw_phone = (row.get("whatsapp_number") or "").strip()

        if not raw_phone:
            results.append(
                {"row": row_num, "status": "failed", "whatsapp_number": "", "reason": "whatsapp_number is required"}
            )
            failed_count += 1
            continue

        normalized = normalize_whatsapp_number(raw_phone)

        if normalized in seen_in_batch:
            results.append(
                {"row": row_num, "status": "failed", "whatsapp_number": raw_phone, "reason": "Duplicate in this file"}
            )
            failed_count += 1
            continue

        if normalized in existing_phones:
            results.append(
                {"row": row_num, "status": "skipped", "whatsapp_number": raw_phone, "reason": "Already exists in organization"}
            )
            skipped_count += 1
            seen_in_batch.add(normalized)
            continue

        seen_in_batch.add(normalized)

        # Resolve role by name (case-insensitive)
        role_name_raw = (row.get("role_name") or "").strip()
        role_id = role_map.get(role_name_raw.lower()) if role_name_raw else None

        phone_clean = normalized.lstrip("+").replace(" ", "")
        placeholder_email = f"wa_{phone_clean}@{org.id}.internal"

        try:
            savepoint = db.begin_nested()
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
                username=(row.get("username") or "").strip() or None,
                full_name=(row.get("full_name") or "").strip() or None,
                job_title=(row.get("job_title") or "").strip() or None,
                whatsapp_number=normalized,
                role_id=role_id,
                is_active=True,
            )
            db.add(profile)
            db.flush()
            savepoint.commit()

            existing_phones.add(normalized)
            results.append({"row": row_num, "status": "created", "whatsapp_number": raw_phone})
            created_count += 1

        except Exception as exc:
            savepoint.rollback()
            results.append(
                {"row": row_num, "status": "failed", "whatsapp_number": raw_phone, "reason": str(exc)}
            )
            failed_count += 1
            continue

    db.commit()

    return {
        "total": len(rows),
        "created": created_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "results": results,
    }


@router.post("", response_model=ProfileResponse)
def create_user(
    user_data: ProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)

    normalized_number = (
        normalize_whatsapp_number(user_data.whatsapp_number)
        if user_data.whatsapp_number
        else user_data.whatsapp_number
    )

    existing = (
        db.query(Profile)
        .filter(
            Profile.org_id == org.id,
            Profile.whatsapp_number == normalized_number,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="WhatsApp number already exists in organization"
        )

    phone_clean = (normalized_number or "").strip().lstrip("+").replace(" ", "")
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
        whatsapp_number=normalized_number,
        role_id=user_data.role_id,
        is_active=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{user_id:uuid}", response_model=ProfileWithUser)
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


@router.put("/{user_id:uuid}", response_model=ProfileResponse)
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
        from agente_rolplay.db.whatsapp_auth import normalize_whatsapp_number

        profile.whatsapp_number = normalize_whatsapp_number(user_data.whatsapp_number)
    if user_data.role_id is not None:
        profile.role_id = user_data.role_id
    if user_data.is_active is not None:
        profile.is_active = user_data.is_active

    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{user_id:uuid}")
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


@router.delete("/{user_id:uuid}/hard-delete")
def hard_delete_user(
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

    if profile.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    target_user_id = profile.user_id

    # If this user is set as org owner, clear the reference before deletion.
    db.query(Organization).filter(Organization.owner_id == target_user_id).update(
        {"owner_id": None}, synchronize_session=False
    )

    db.delete(profile)
    db.flush()

    remaining_profiles = (
        db.query(Profile).filter(Profile.user_id == target_user_id).first()
    )
    if not remaining_profiles:
        user = db.query(User).filter(User.id == target_user_id).first()
        if user:
            db.delete(user)

    db.commit()
    return {"message": "User deleted permanently"}


# ── Scenarios CRUD (org-scoped) ───────────────────────────────────────────────

scenarios_router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@scenarios_router.get("")
def list_scenarios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = get_org_for_user(db, current_user.id)
    scenarios = (
        db.query(CoachingScenario)
        .filter(CoachingScenario.org_id == org.id)
        .order_by(CoachingScenario.created_at.desc())
        .all()
    )
    from agente_rolplay.db.models import CoachingSession

    result = []
    for s in scenarios:
        session_count = (
            db.query(func.count(CoachingSession.id))
            .filter(CoachingSession.scenario_id == s.id)
            .scalar()
            or 0
        )
        result.append(
            {
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "session_count": session_count,
            }
        )
    return result


@router.post("/{user_id:uuid}/reactivate", response_model=ProfileResponse)
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


# ── Groups (org-scoped) ─────────────────────────────────────────────────────


def _extract_template_variables(content: str) -> list[str]:
    """Extract {{1}}, {{2}}, etc. from template content."""
    import re

    matches = re.findall(r"\{\{(\d+)\}\}", content)
    return sorted(set(matches), key=lambda x: int(x))


@router.get("/groups")
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all groups for the user's organization."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    groups = (
        db.query(Group)
        .filter(Group.org_id == profile.org_id)
        .order_by(Group.created_at.desc())
        .all()
    )
    result = []
    for g in groups:
        member_count = (
            db.query(func.count(GroupMember.id))
            .filter(GroupMember.group_id == g.id)
            .scalar()
            or 0
        )
        result.append(
            {
                "id": str(g.id),
                "name": g.name,
                "member_count": member_count,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "created_by_id": str(g.created_by_id) if g.created_by_id else None,
            }
        )
    return result


@router.post("/groups")
def create_group(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new group in the user's organization."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    group = Group(
        org_id=profile.org_id,
        name=name,
        created_by_id=current_user.id,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return {
        "id": str(group.id),
        "name": group.name,
        "member_count": 0,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "created_by_id": str(group.created_by_id) if group.created_by_id else None,
    }


@router.patch("/groups/{group_id}")
def update_group(
    group_id: str,
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a group name."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.org_id == profile.org_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if name:
        group.name = name
    db.commit()
    db.refresh(group)
    return {"id": str(group.id), "name": group.name}


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a group."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.org_id == profile.org_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by_id and group.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the group creator can delete this group")

    db.delete(group)
    db.commit()
    return {"deleted": group_id}


# ── Group Members ──────────────────────────────────────────────────────────


@router.get("/groups/{group_id}/members")
def list_group_members(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List members of a group."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.org_id == profile.org_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    result = []
    for m in members:
        member_profile = db.query(Profile).filter(Profile.id == m.profile_id).first()
        result.append(
            {
                "id": str(m.id),
                "user_id": str(m.user_id),
                "profile_id": str(m.profile_id) if m.profile_id else None,
                "full_name": member_profile.full_name if member_profile else None,
                "whatsapp_number": member_profile.whatsapp_number
                if member_profile
                else None,
            }
        )
    return result


@router.post("/groups/{group_id}/members")
def add_group_members(
    group_id: str,
    profile_ids: List[str] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add multiple users to a group."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.org_id == profile.org_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by_id and group.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the group creator can manage members")

    added = []
    for pid in profile_ids:
        p = (
            db.query(Profile)
            .filter(Profile.id == pid, Profile.org_id == profile.org_id)
            .first()
        )
        if p:
            existing = (
                db.query(GroupMember)
                .filter(GroupMember.group_id == group_id, GroupMember.profile_id == pid)
                .first()
            )
            if not existing:
                member = GroupMember(
                    group_id=group.id,
                    user_id=p.user_id,
                    profile_id=p.id,
                )
                db.add(member)
                added.append(pid)

    db.commit()
    return {"added": added}


@router.delete("/groups/{group_id}/members/{profile_id}")
def remove_group_member(
    group_id: str,
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a user from a group."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.org_id == profile.org_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by_id and group.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the group creator can manage members")

    member = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id, GroupMember.profile_id == profile_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()
    return {"removed": profile_id}


@router.get("/org-users")
def list_org_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all users in the organization (for group assignment)."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profiles = (
        db.query(Profile)
        .filter(Profile.org_id == profile.org_id, Profile.is_active == True)
        .all()
    )
    return [
        {
            "id": str(p.id),
            "full_name": p.full_name,
            "whatsapp_number": p.whatsapp_number,
            "job_title": p.job_title,
        }
        for p in profiles
    ]


# ── Message Templates (org-scoped) ───────────────────────────────────────────────


@router.get("/templates")
def list_org_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List templates available to the organization."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    templates = (
        db.query(MessageTemplate)
        .filter(
            (MessageTemplate.org_id == profile.org_id)
            | (MessageTemplate.org_id == None)
        )
        .filter(MessageTemplate.is_active == True)
        .order_by(MessageTemplate.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(t.id),
            "name": t.name,
            "content": t.content,
            "variables": t.variables or [],
        }
        for t in templates
    ]


# ── Broadcast Schedules ────────────────────────────────────────────────────


@router.get("/broadcasts")
def list_broadcasts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List broadcast schedules for the organization."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    broadcasts = (
        db.query(BroadcastSchedule)
        .filter(BroadcastSchedule.org_id == profile.org_id)
        .order_by(BroadcastSchedule.scheduled_at.desc())
        .all()
    )

    result = []
    for b in broadcasts:
        template = (
            db.query(MessageTemplate)
            .filter(MessageTemplate.id == b.template_id)
            .first()
            if b.template_id
            else None
        )
        group = (
            db.query(Group).filter(Group.id == b.group_id).first()
            if b.group_id
            else None
        )
        result.append(
            {
                "id": str(b.id),
                "template_id": str(b.template_id) if b.template_id else None,
                "template_name": template.name if template else None,
                "group_id": str(b.group_id) if b.group_id else None,
                "group_name": group.name if group else None,
                "scheduled_at": b.scheduled_at.isoformat() if b.scheduled_at else None,
                "variable_values": b.variable_values or {},
                "status": b.status,
                "sent_count": b.sent_count,
                "failed_count": b.failed_count,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
        )
    return result


@router.post("/broadcasts")
def create_broadcast(
    template_id: str,
    group_id: str,
    scheduled_at: str,
    variable_values: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Schedule a new broadcast."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    template = (
        db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.org_id == profile.org_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    from datetime import datetime

    try:
        scheduled_dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    except ValueError:
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid scheduled_at format")

    if scheduled_dt <= datetime.utcnow():
        raise HTTPException(
            status_code=400, detail="scheduled_at must be in the future"
        )

    broadcast = BroadcastSchedule(
        org_id=profile.org_id,
        template_id=template.id,
        group_id=group.id,
        scheduled_at=scheduled_dt,
        variable_values=variable_values or {},
        created_by_id=current_user.id,
    )
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)
    return {
        "id": str(broadcast.id),
        "template_id": str(broadcast.template_id),
        "group_id": str(broadcast.group_id),
        "scheduled_at": broadcast.scheduled_at.isoformat(),
        "variable_values": broadcast.variable_values or {},
        "status": broadcast.status,
    }


@router.delete("/broadcasts/{broadcast_id}")
def cancel_broadcast(
    broadcast_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending broadcast."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    broadcast = (
        db.query(BroadcastSchedule)
        .filter(
            BroadcastSchedule.id == broadcast_id,
            BroadcastSchedule.org_id == profile.org_id,
        )
        .first()
    )
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")

    if broadcast.status != "pending":
        raise HTTPException(
            status_code=400, detail="Only pending broadcasts can be cancelled"
        )

    db.delete(broadcast)
    db.commit()
    return {"deleted": broadcast_id}
