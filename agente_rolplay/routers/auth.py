from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import ValidationError
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta

from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import User, Organization, Profile, Role
from agente_rolplay.db.schemas import (
    SignupRequest,
    LoginRequest,
    Token,
    UserResponse,
    OrganizationResponse,
)
from agente_rolplay.db.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])

templates = Jinja2Templates(directory="agente_rolplay/templates")

DEFAULT_ROLES = [
    {
        "name": "Admin",
        "permissions": [
            {"query:financial": True},
            {"query:strategic": True},
            {"query:sensitive": True},
            {"document:read": True},
            {"document:upload": True},
            {"user:manage": True},
        ],
    },
    {
        "name": "Manager",
        "permissions": [
            {"query:financial": True},
            {"query:strategic": False},
            {"query:sensitive": False},
            {"document:read": True},
            {"document:upload": True},
            {"user:manage": False},
        ],
    },
    {
        "name": "Employee",
        "permissions": [
            {"query:financial": False},
            {"query:strategic": False},
            {"query:sensitive": False},
            {"document:read": True},
            {"document:upload": False},
            {"user:manage": False},
        ],
    },
    {
        "name": "Intern",
        "permissions": [
            {"query:financial": False},
            {"query:strategic": False},
            {"query:sensitive": False},
            {"document:read": False},
            {"document:upload": False},
            {"user:manage": False},
        ],
    },
]


def _coerce_request_payload(request: Request, raw_body: bytes):
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        return request.json()

    if "application/x-www-form-urlencoded" in content_type:
        return request.form()

    # Fallback for clients that post urlencoded payloads with missing/wrong content-type.
    body_text = raw_body.decode("utf-8", errors="ignore")
    if "=" in body_text and "&" in body_text:
        parsed = parse_qs(body_text, keep_blank_values=True)
        return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

    return None


async def _parse_model_from_request(model_cls, request: Request):
    raw_body = await request.body()
    payload = _coerce_request_payload(request, raw_body)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request body must be valid JSON or form-urlencoded data",
        )

    if hasattr(payload, "multi_items"):
        payload = dict(payload)
    elif hasattr(payload, "__await__"):
        payload = await payload
        if hasattr(payload, "multi_items"):
            payload = dict(payload)

    try:
        return model_cls.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc


@router.post("/signup", response_model=dict)
async def signup(request: Request, db: Session = Depends(get_db)):
    signup_request = await _parse_model_from_request(SignupRequest, request)

    existing_user = db.query(User).filter(User.email == signup_request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=signup_request.email,
        password_hash=get_password_hash(signup_request.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    organization = Organization(
        name=signup_request.organization_name,
        owner_id=user.id,
    )
    db.add(organization)
    db.commit()
    db.refresh(organization)

    admin_role = Role(
        org_id=organization.id,
        name="Admin",
        permissions=DEFAULT_ROLES[0]["permissions"],
    )
    db.add(admin_role)
    db.commit()
    db.refresh(admin_role)

    for role_data in DEFAULT_ROLES[1:]:
        role = Role(
            org_id=organization.id,
            name=role_data["name"],
            permissions=role_data["permissions"],
        )
        db.add(role)
    db.commit()

    profile = Profile(
        user_id=user.id,
        org_id=organization.id,
        username=signup_request.username or signup_request.email.split("@")[0],
        role_id=admin_role.id,
        is_active=True,
    )
    db.add(profile)
    db.commit()

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "organization_id": str(organization.id),
    }


@router.post("/login", response_model=Token)
async def login(request: Request, db: Session = Depends(get_db)):
    login_request = await _parse_model_from_request(LoginRequest, request)

    user = db.query(User).filter(User.email == login_request.email).first()
    if not user or not verify_password(login_request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    request.session["user_id"] = str(user.id)

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="access_token")
    return response
