from agente_rolplay.messaging.twilio_client import (
    send_twilio_message,
    send_twilio_document,
    download_document_from_twilio,
)
from agente_rolplay.messaging.message_processor import (
    process_incoming_messages_functional,
    process_incoming_messages,
)

enviar_mensaje_twilio = send_twilio_message
enviar_documento_twilio = send_twilio_document
descargar_documento_de_twilio = download_document_from_twilio
procesar_mensajes_entrantes = process_incoming_messages
procesar_mensajes_entrantes_funcional = process_incoming_messages_functional
