import traceback

from fastapi import APIRouter, Request
from fastapi.responses import Response

from src.agente_rolplay.process_messages import procesar_mensajes_entrantes

router = APIRouter()


@router.post("/api/v1/webhook")
async def webhook_post(request: Request):
    """Receives messages from Twilio WhatsApp"""
    try:
        form_data = await request.form()
        mensaje_data = dict(form_data)

        print("POST received from Twilio:", mensaje_data)

        procesar_mensajes_entrantes(mensaje_data)

        return Response(content="", status_code=200)

    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return Response(content="", status_code=200)


@router.post("/api/v1/webhook/status")
async def webhook_status(request: Request):
    """Optional endpoint to receive status updates for sent messages"""
    try:
        form_data = await request.form()
        status_data = dict(form_data)
        print("Status callback received:", status_data)

        return Response(content="", status_code=200, media_type="text/xml")
    except Exception as e:
        print(f"Error processing status: {e}")
        return Response(content="", status_code=200, media_type="text/xml")
