import asyncio
import re
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session
from agente_rolplay.db.database import SessionLocal
from agente_rolplay.db.models import (
    BroadcastSchedule,
    Group,
    GroupMember,
    MessageTemplate,
    Organization,
    Profile,
)

TWILIO_ACCOUNT_SID = None
TWILIO_AUTH_TOKEN = None
TWILIO_SANDBOX_NUMBER = None

try:
    from agente_rolplay.config import (
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN,
        TWILIO_SANDBOX_NUMBER,
    )
except ImportError:
    pass

_client = None


def _get_org_from_number(org_id) -> str:
    """Return the Twilio from-number for the given org_id, falling back to the global sandbox number."""
    if org_id:
        db = SessionLocal()
        try:
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if org and org.twilio_number:
                return org.twilio_number
        except Exception as e:
            print(f"[broadcast] Error looking up org number: {e}")
        finally:
            db.close()
    return TWILIO_SANDBOX_NUMBER


def _get_twilio_client():
    global _client
    if _client is None and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        from twilio.rest import Client

        _client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _client


def _fill_template(content: str, values: Dict[str, str]) -> str:
    """Replace {{1}}, {{2}}, etc. with actual values."""
    result = content
    for key, value in values.items():
        result = result.replace("{{" + key + "}}", value)
    return result


def _fill_from_user_data(content: str, profile: Profile, values: Dict[str, str]) -> str:
    """Fill template variables from user profile data."""
    result = content
    user_fields = {
        "1": profile.full_name or profile.username or "there",
        "full_name": profile.full_name or "",
        "username": profile.username or "",
        "whatsapp": profile.whatsapp_number or "",
    }
    for key, user_val in user_fields.items():
        result = result.replace(f"{{{{{key}}}}}", user_val)
    for key, manual_val in values.items():
        if key not in user_fields:
            result = result.replace(f"{{{{{key}}}}}", manual_val)
    return result


async def _send_whatsapp_message(phone_number: str, content: str, from_number: str = None) -> bool:
    """Send a WhatsApp message via Twilio."""
    client = _get_twilio_client()
    if not client:
        print(f"[broadcast] No Twilio client available")
        return False

    effective_from = from_number or TWILIO_SANDBOX_NUMBER
    try:
        message = client.messages.create(
            from_=effective_from,
            body=content,
            to=phone_number,
        )
        print(f"[broadcast] Sent message SID: {message.sid}")
        return True
    except Exception as e:
        print(f"[broadcast] Failed to send message: {e}")
        return False


async def _process_broadcast(broadcast: BroadcastSchedule, db: Session):
    """Process a single broadcast - send messages to all group members."""
    org_from_number = _get_org_from_number(broadcast.org_id)

    template = (
        db.query(MessageTemplate)
        .filter(MessageTemplate.id == broadcast.template_id)
        .first()
    )
    group = db.query(Group).filter(Group.id == broadcast.group_id).first()

    if not template:
        print(f"[broadcast] Template not found for broadcast {broadcast.id}")
        broadcast.status = "failed"
        db.commit()
        return

    if not group:
        print(f"[broadcast] Group not found for broadcast {broadcast.id}")
        broadcast.status = "failed"
        db.commit()
        return

    members = db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
    if not members:
        print(f"[broadcast] No members in group {group.id}")
        broadcast.status = "completed"
        broadcast.sent_count = 0
        db.commit()
        return

    broadcast.status = "processing"
    db.commit()

    sent_count = 0
    failed_count = 0

    for member in members:
        profile = db.query(Profile).filter(Profile.id == member.profile_id).first()
        if not profile or not profile.whatsapp_number:
            failed_count += 1
            continue

        message_content = _fill_from_user_data(
            template.content, profile, broadcast.variable_values or {}
        )

        success = await _send_whatsapp_message(profile.whatsapp_number, message_content, from_number=org_from_number)
        if success:
            sent_count += 1
        else:
            failed_count += 1

        await asyncio.sleep(0.1)

    broadcast.status = "completed"
    broadcast.sent_count = sent_count
    broadcast.failed_count = failed_count
    broadcast.sent_at = datetime.utcnow()
    db.commit()

    print(
        f"[broadcast] Completed broadcast {broadcast.id}: {sent_count} sent, {failed_count} failed"
    )


async def process_due_broadcasts():
    """Find and process due broadcasts."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due_broadcasts = (
            db.query(BroadcastSchedule)
            .filter(
                BroadcastSchedule.status == "pending",
                BroadcastSchedule.scheduled_at <= now,
            )
            .all()
        )

        for broadcast in due_broadcasts:
            await _process_broadcast(broadcast, db)

    except Exception as e:
        print(f"[broadcast] Error processing broadcasts: {e}")
    finally:
        db.close()


async def broadcast_scheduler():
    """Background scheduler - checks every 30 seconds for due broadcasts."""
    print("[broadcast] Scheduler started")
    while True:
        await process_due_broadcasts()
        await asyncio.sleep(30)
