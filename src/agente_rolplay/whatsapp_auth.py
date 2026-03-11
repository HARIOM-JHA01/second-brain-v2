import json
from typing import Optional, Dict, Any, List
from uuid import UUID
from anthropic import Anthropic

from src.agente_rolplay.config import ANTHROPIC_API_KEY
from src.agente_rolplay.database import SessionLocal
from src.agente_rolplay.models import Profile, Role, Organization

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)


def normalize_whatsapp_number(phone: str) -> str:
    """Normalize phone number to consistent format."""
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("521"):
        return "+" + digits
    elif digits.startswith("52"):
        return "+" + digits
    elif digits.startswith("1") and len(digits) == 11:
        return "+" + digits
    elif len(digits) == 10:
        return "+1" + digits
    return "+" + digits


def lookup_whatsapp_user(phone_number: str) -> Optional[Dict[str, Any]]:
    """Look up user by WhatsApp phone number."""
    normalized = normalize_whatsapp_number(phone_number)

    db = SessionLocal()
    try:
        profile = (
            db.query(Profile)
            .filter(Profile.whatsapp_number == normalized, Profile.is_active == True)
            .first()
        )

        if not profile:
            return None

        role = (
            db.query(Role).filter(Role.id == profile.role_id).first()
            if profile.role_id
            else None
        )
        org = db.query(Organization).filter(Organization.id == profile.org_id).first()

        return {
            "profile_id": str(profile.id),
            "user_id": str(profile.user_id),
            "org_id": str(profile.org_id),
            "org_name": org.name if org else None,
            "username": profile.username,
            "whatsapp_number": profile.whatsapp_number,
            "role_id": str(profile.role_id) if profile.role_id else None,
            "role_name": role.name if role else None,
            "permissions": role.permissions if role else [],
            "is_active": profile.is_active,
        }
    finally:
        db.close()


def has_permission(user_info: Dict[str, Any], permission: str) -> bool:
    """Check if user has a specific permission."""
    permissions = user_info.get("permissions", [])
    if not permissions:
        return False

    for perm in permissions:
        if isinstance(perm, dict) and perm.get(permission) is True:
            return True

    return False


QUERY_CLASSIFICATION_PROMPT = """Classify the following query into one of these categories:
- financial: questions about budgets, revenue, costs, salaries, financial data, money, expenses
- strategic: questions about CEO/CFO level topics, roadmap, M&A, strategy, high-level decisions
- sensitive: questions about personal data, confidential info, private matters
- general: everything else

Query: {query}

Reply with ONLY ONE WORD: financial, strategic, sensitive, or general"""


def classify_query(query: str) -> str:
    """Classify a query to determine its sensitivity level."""
    try:
        response = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[
                {
                    "role": "user",
                    "content": QUERY_CLASSIFICATION_PROMPT.format(query=query),
                }
            ],
        )

        classification = response.content[0].text.strip().lower()

        if classification in ["financial", "strategic", "sensitive", "general"]:
            return classification

        return "general"
    except Exception as e:
        print(f"Error classifying query: {e}")
        return "general"


def get_permission_for_query_type(query_type: str) -> str:
    """Get the permission string for a query type."""
    mapping = {
        "financial": "query:financial",
        "strategic": "query:strategic",
        "sensitive": "query:sensitive",
    }
    return mapping.get(query_type, "")


def check_query_permission(user_info: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Check if user can access the query. Returns dict with:
    - allowed: bool
    - reason: str (if blocked)
    - query_type: str
    """
    query_type = classify_query(query)

    if query_type == "general":
        return {"allowed": True, "query_type": query_type}

    permission = get_permission_for_query_type(query_type)

    if not permission:
        return {"allowed": True, "query_type": query_type}

    if has_permission(user_info, permission):
        return {"allowed": True, "query_type": query_type}

    return {
        "allowed": False,
        "reason": "I apologize, but this query is beyond your access level. Please contact your administrator for more information.",
        "query_type": query_type,
    }


BLOCKED_RESPONSE = "I apologize, but this query is beyond your access level. Please contact your administrator for more information."
