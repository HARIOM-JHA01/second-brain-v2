from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import CoachingSession, WhatsAppMessage

router = APIRouter(prefix="/api", tags=["coaching"])


@router.get("/coaching-sessions")
def get_coaching_sessions(db: Session = Depends(get_db)):
    sessions = (
        db.query(CoachingSession)
        .order_by(CoachingSession.started_at.desc())
        .all()
    )
    result = []
    for s in sessions:
        q = db.query(WhatsAppMessage).filter(
            WhatsAppMessage.phone_number == s.phone_number,
            WhatsAppMessage.created_at >= s.started_at,
        )
        if s.ended_at:
            q = q.filter(WhatsAppMessage.created_at <= s.ended_at)
        messages = q.order_by(WhatsAppMessage.created_at.asc()).all()

        result.append(
            {
                "id": str(s.id),
                "org_id": str(s.org_id) if s.org_id else None,
                "phone_number": s.phone_number,
                "scenario_id": str(s.scenario_id) if s.scenario_id else None,
                "scenario_name": s.scenario_name,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "report_text": s.report_text,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "message_type": m.message_type,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in messages
                ],
            }
        )
    return result
