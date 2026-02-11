# python3 procesa_mensajes.py

from agente_roleplay import responder_usuario
from chat_history import add_to_chat_history, get_chat_history, reset_chat_history
from datetime import datetime
from dotenv import load_dotenv
from google_drive import subir_archivo_a_drive
from utils import borrar_metadata
from twilio.rest import Client

import json
import os
import redis
import requests
import time

load_dotenv(override=True)

# Credenciales de Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SANDBOX_NUMBER = os.getenv("TWILIO_SANDBOX_NUMBER")

# Redis
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")

# Cliente de Twilio
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Redis client
r = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username="default",
    password=redis_password,
)

def descargar_documento_de_twilio(media_url, nombre_archivo, tipo_archivo):
    """
    Descarga un documento desde Twilio y lo guarda temporalmente
    
    Args:
        media_url (str): URL del archivo en Twilio
        nombre_archivo (str): Nombre deseado para el archivo
        tipo_archivo (str): Extensión (xlsx, pdf, docx, etc)
    
    Returns:
        str: Ruta del archivo temporal o None si falla
    """
    try:
        print(f"📥 Descargando de Twilio: {media_url}")
        
        # Descargar con autenticación de Twilio
        response = requests.get(
            media_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Error descargando: Status {response.status_code}")
            return None
        
        # Crear directorio temporal si no existe
        temp_dir = "./temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Nombre completo del archivo
        nombre_completo = f"{nombre_archivo}.{tipo_archivo}"
        ruta_temporal = os.path.join(temp_dir, nombre_completo)
        
        # Guardar archivo
        with open(ruta_temporal, 'wb') as f:
            f.write(response.content)
        
        tamaño_kb = len(response.content) / 1024
        print(f"✅ Archivo descargado: {ruta_temporal} ({tamaño_kb:.2f} KB)")
        
        return ruta_temporal
        
    except Exception as e:
        print(f"❌ Error descargando archivo: {e}")
        return None

def enviar_mensaje_twilio_orig(telefono, texto, max_retries=3):
    """
    Envía mensaje de WhatsApp usando Twilio
    telefono debe venir en formato: whatsapp:+5215512345678
    """
    for intento in range(max_retries):
        try:
            print(f"📤 Enviando mensaje con Twilio (intento {intento + 1}/{max_retries}): {texto[:50]}...")
            print(f"📤 From: {TWILIO_SANDBOX_NUMBER}")  # Para debug
            print(f"📤 To: {telefono}")  # Para debug
            
            message = twilio_client.messages.create(
                from_=TWILIO_SANDBOX_NUMBER,  # 🔥 Usa la variable global, NO el parámetro
                body=texto,
                to=telefono
            )
            
            print(f"✅ Mensaje enviado exitosamente. SID: {message.sid}")
            return {"success": True, "response": {"sid": message.sid, "status": message.status}}

        except Exception as e:
            print(f"❌ ERROR EN INTENTO {intento + 1}/{max_retries}: {str(e)}")
            if intento < max_retries - 1:
                time.sleep(3 * (intento + 1))
                continue
            else:
                print(f"❌ ERROR FINAL después de {max_retries} intentos: {str(e)}")
                return {"success": False, "error": str(e)}

    return {"success": False, "error": "Falló después de todos los reintentos"}

def enviar_mensaje_twilio(telefono, texto, max_retries=3):
    """
    Envía mensaje de WhatsApp usando Twilio, respetando el límite de caracteres (1600) y con reintentos en caso de error.
    Teléfono debe venir en formato: whatsapp:+5215512345678
    """

    num_caracteres = len(texto)
    too_long_ending_text = "La respuesta del asistente es demasiado larga, ha sido recortada"

    if num_caracteres >= 1600:
        texto = texto[:1500] + "\n\n" + too_long_ending_text

    for intento in range(max_retries):
        try:
            print(f"📤 Enviando mensaje con Twilio (intento {intento + 1}/{max_retries}): {texto[:50]}...")
            print(f"📤 From: {TWILIO_SANDBOX_NUMBER}")  # Para debug
            print(f"📤 To: {telefono}")  # Para debug
            
            message = twilio_client.messages.create(
                from_=TWILIO_SANDBOX_NUMBER,  # Usa la variable global, NO el parámetro
                body=texto,
                to=telefono
            )
            
            print(f"✅ Mensaje enviado exitosamente. SID: {message.sid}")
            return {"success": True, "response": {"sid": message.sid, "status": message.status}}

        except Exception as e:
            print(f"❌ ERROR EN INTENTO {intento + 1}/{max_retries}: {str(e)}")
            if intento < max_retries - 1:
                time.sleep(3 * (intento + 1))
                continue
            else:
                print(f"❌ ERROR FINAL después de {max_retries} intentos: {str(e)}")
                return {"success": False, "error": str(e)}

    return {"success": False, "error": "Falló después de todos los reintentos"}

def enviar_documento_twilio(telefono, documento_url, caption=""):
    """
    Envía un documento usando Twilio
    """
    try:
        print(f"📎 Enviando documento: {documento_url}")
        
        message = twilio_client.messages.create(
            from_=TWILIO_SANDBOX_NUMBER,  # 🔥 Variable global
            body=caption if caption else "Aquí está tu documento",
            media_url=[documento_url],
            to=telefono
        )
        
        print(f"✅ Documento enviado. SID: {message.sid}")
        return {"success": True, "response": {"sid": message.sid}}
        
    except Exception as e:
        print(f"❌ ERROR enviando documento: {str(e)}")
        return {"success": False, "error": str(e)}

def extract_phone_from_twilio(from_field):
    """
    Extrae el número de teléfono del formato de Twilio
    Input: whatsapp:+5215512345678
    Output: 5215512345678
    """
    if not from_field:
        return ""
    
    # Remover prefijo whatsapp:
    phone = from_field.replace("whatsapp:", "")
    # Remover el símbolo +
    phone = phone.replace("+", "")
    
    return phone

def procesar_mensajes_entrantes_funcional(form_data, redis_client=r):
    """
    Procesa mensajes entrantes de Twilio WhatsApp
    form_data viene como diccionario con los campos de Twilio
    """
    print("📥 FORM DATA DE TWILIO:", form_data)
    TEMP_DIR = "./temp_uploads"
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Extraer campos importantes de Twilio
    from_number = form_data.get('From', '')  # whatsapp:+5215512345678
    to_number = form_data.get('To', '')      # whatsapp:+14155238886
    body = form_data.get('Body', '')
    message_sid = form_data.get('MessageSid', '')
    num_media = int(form_data.get('NumMedia', 0))
    
    # Extraer teléfono limpio
    phone_number = extract_phone_from_twilio(from_number)
    print(f"📱 PHONE NUMBER: {phone_number}")

    if not phone_number:
        print("❌ No se pudo extraer número de teléfono")
        return 'NoCommand'

    # Timestamp actual (Twilio no envía timestamp en form data)
    timestamp = int(time.time())

    # 🔥 DEDUPLICACIÓN POR TELÉFONO + MESSAGE_SID
    dedup_key = f"msg:twilio:{message_sid}"
    
    if redis_client.exists(dedup_key):
        print(f"⚠️ Mensaje duplicado detectado: {dedup_key}")
        return 'NoCommand'
    
    print(f"🔍 Procesando mensaje nuevo: {dedup_key}")

    # Determinar tipo de mensaje
    message_type = 'text'
    media_url = ''
    media_content_type = ''
    
    if num_media > 0:
        media_url = form_data.get('MediaUrl0', '')
        media_content_type = form_data.get('MediaContentType0', '')
        
        # Clasificar tipo de mensaje según content type
        if 'image' in media_content_type:
            message_type = 'image'
        elif 'audio' in media_content_type or 'ogg' in media_content_type:
            message_type = 'audio'
        elif 'video' in media_content_type:
            message_type = 'video'
        elif 'application' in media_content_type or 'pdf' in media_content_type:
            message_type = 'document'
        else:
            message_type = 'media'
        
        print(f"📎 Media detectado: {message_type} - {media_url}")

    # Estructura de datos compatible con tu código existente
    data = {
        'id': message_sid,
        'from': from_number,
        'to': to_number,
        'body': body,
        'fromMe': False,  # Twilio solo envía mensajes entrantes
        'type': message_type,
        'pushName': form_data.get('ProfileName', ''),
        'timestamp': timestamp,
        'media': media_url,
        'media_content_type': media_content_type
    }

    print("✅ DATA procesada:", data)

    # 🗑️ COMANDO: BORRAR MEMORIA
    if body and 'borrar memoria' in body.lower():
        print(f"🗑️ Ejecutando borrado de memoria para: {phone_number}")
        reset_chat_history(phone_number)
        resultado = enviar_mensaje_twilio(
            from_number,
            "✅ Tu memoria ha sido borrada."
        )
        if resultado.get('success', False):
            redis_client.set(dedup_key, 'exists', ex=600)
            print(f"✅ Borrar memoria procesado: {dedup_key}")
        return resultado

    # Variables para el resto del flujo
    id_phone_number = f"fp-idPhone:{phone_number}"
    id_conversacion = f"fp-idPhone:{phone_number}_{datetime.now().strftime('%Y-%m-%d_%H:%M')}"

    # ✅ Procesa mensajes de audio (si quieres encolarlos)
    if message_type == 'audio':
        audio_dedup_key = f"audio_queued:{phone_number}:{timestamp}"

        if redis_client.exists(audio_dedup_key):
            print(f"⚠️ Audio ya fue encolado anteriormente: {audio_dedup_key}")
            return 'NoCommand'
        
        redis_client.set(audio_dedup_key, 'queued', ex=300)
        
        # Obtener user_data
        if not redis_client.exists(id_phone_number):
            user_data = {
                'Usuario': '',
                'Telefono': phone_number
            }
            redis_client.set(id_phone_number, json.dumps(user_data), ex=600)
        else:
            user_data = json.loads(redis_client.get(id_phone_number))
        
        # Crear job para el worker (si usas procesamiento asíncrono)
        audio_job = {
            'media_url': media_url,
            'phone_number': phone_number,
            'from': from_number,
            'id_conversacion': id_conversacion,
            'timestamp': timestamp,
            'user_data': user_data,
            'message_sid': message_sid
        }
        
        # Encolar para procesamiento asíncrono
        redis_client.lpush('audio_queue', json.dumps(audio_job))
        
        print(f"✅ Audio encolado para procesamiento: {phone_number}")
        return 'AudioQueued'
    
    # ✅ Procesa mensajes de documento
    if message_type == 'document':
        print(f"📄 Documento recibido: {media_url}")

        # ==============================================================================

        # BUSCAR SI EL USUARIO YA DIO UN NOMBRE
        nombre_esperado_key = f"doc_nombre:{phone_number}"
        tipo_esperado_key = f"doc_tipo:{phone_number}"
        
        nombre_deseado = redis_client.get(nombre_esperado_key)
        tipo_deseado = redis_client.get(tipo_esperado_key)
        
        # Si hay nombre guardado, usarlo
        if nombre_deseado and tipo_deseado:
            nombre_base = nombre_deseado
            extension = tipo_deseado
            print(f"✅ Usando nombre del usuario: {nombre_base}.{extension}")
            
            # Limpiar después de usar
            redis_client.delete(nombre_esperado_key)
            redis_client.delete(tipo_esperado_key)
        else:
            # Generar nombre automático
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_base = f"documento_{phone_number}_{timestamp_str}"
            
            extensiones = {
                'application/pdf': 'pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
                'image/jpeg': 'jpg',
                'image/png': 'png'
            }
            
            extension = extensiones.get(media_content_type, 'bin')
        
        # Notificar al usuario
        enviar_mensaje_twilio(
            from_number,
            f"📄 Subiendo '{nombre_base}.{extension}' a Google Drive..."
        )
        
        # Descargar archivo de Twilio
        ruta_temporal = descargar_documento_de_twilio(
            media_url=media_url,
            nombre_archivo=nombre_base,
            tipo_archivo=extension
        )
        
        if not ruta_temporal:
            enviar_mensaje_twilio(
                from_number,
                "❌ Lo siento, hubo un error al descargar tu documento."
            )
            redis_client.set(dedup_key, 'exists', ex=600)
            return 'DocumentError'
        
        # Subir a Google Drive
        from google_drive import subir_archivo_a_drive
        folder_id = "1M0TmERmETfEM8flmzwGgfKC7IkrVZaoD"
        
        resultado = subir_archivo_a_drive(
            ruta_archivo_local=ruta_temporal,
            # nombre_carpeta="Second Brain",
            folder_id=folder_id
        )
        
        # la solucion que sirve con el nombre pero no actualiza en qdrant 
        # Limpiar archivo temporal
        try:
            os.remove(ruta_temporal)
            print(f"🗑️ Archivo temporal eliminado: {ruta_temporal}")
        except:
            pass
        
        # Responder al usuario
        if resultado and resultado.get('success'):
            mensaje = f"✅ Documento '{nombre_base}.{extension}' subido exitosamente!\n\n"
            mensaje += f"🔗 Link: {resultado['web_view_link']}"
            
            enviar_mensaje_twilio(from_number, mensaje)

        else:
            error_msg = resultado.get('error', 'Desconocido') if resultado else 'Desconocido'
            enviar_mensaje_twilio(
                from_number,
                f"❌ Error al subir a Drive: {error_msg}"
            )
        
        redis_client.set(dedup_key, 'exists', ex=600)
        return 'DocumentProcessed'

        # ==============================================================================
        
        # ==============================================================================
        # este proceso funciona pero no pone el nombre del documento que proporciona el usuario 
        # Notificar al usuario que se está procesando
        # enviar_mensaje_twilio(
        #     from_number,
        #     "📄 He recibido tu documento. Lo estoy procesando y subiré a Drive..."
        # )
        
        # # Extraer nombre del archivo del contenido o generar uno
        # timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        # nombre_base = f"documento_{phone_number}_{timestamp_str}"
        
        # # Detectar extensión del tipo de contenido
        # extensiones = {
        #     'application/pdf': 'pdf',
        #     'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        #     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        #     'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
        #     'image/jpeg': 'jpg',
        #     'image/png': 'png'
        # }
        
        # extension = extensiones.get(media_content_type, 'bin')
        
        # # Descargar archivo de Twilio
        # ruta_temporal = descargar_documento_de_twilio(
        #     media_url=media_url,
        #     nombre_archivo=nombre_base,
        #     tipo_archivo=extension
        # )
        
        # if not ruta_temporal:
        #     enviar_mensaje_twilio(
        #         from_number,
        #         "❌ Lo siento, hubo un error al descargar tu documento."
        #     )
        #     redis_client.set(dedup_key, 'exists', ex=600)
        #     return 'DocumentError'
        
        # resultado = subir_archivo_a_drive(
        #     ruta_archivo_local=ruta_temporal,
        #     # nombre_carpeta="Second Brain",  # O la carpeta que prefieras
        #     # folder_id="1ciaGOxXKcLMNeuIa9103ivxYgBon__7q"  # ID de second brain 
        #     folder_id="1M0TmERmETfEM8flmzwGgfKC7IkrVZaoD" # Id de chat gpt business 
        # )
        
        # # Limpiar archivo temporal
        # try:
        #     os.remove(ruta_temporal)
        #     print(f"🗑️ Archivo temporal eliminado: {ruta_temporal}")
        # except:
        #     pass
        
        # # Responder al usuario
        # if resultado and resultado.get('success'):
        #     mensaje = f"✅ Documento subido exitosamente a Google Drive!\n\n"
        #     mensaje += f"📄 Nombre: {resultado['file_name']}\n"
        #     mensaje += f"🔗 Link: {resultado['web_view_link']}"
            
        #     enviar_mensaje_twilio(from_number, mensaje)
        # else:
        #     error_msg = resultado.get('error', 'Desconocido') if resultado else 'Desconocido'
        #     enviar_mensaje_twilio(
        #         from_number,
        #         f"❌ Error al subir a Drive: {error_msg}"
        #     )
        
        # redis_client.set(dedup_key, 'exists', ex=600)
        # return 'DocumentProcessed'
        # ==============================================================================

        # print(f"📄 Documento recibido: {media_url}")
        # # Aquí puedes procesar el documento
        # # Por ahora solo notificamos al usuario
        # enviar_mensaje_twilio(
        #     from_number,
        #     "📄 He recibido tu documento. Lo estoy procesando..."
        # )
        # # TODO: Implementar descarga y procesamiento del documento
        # redis_client.set(dedup_key, 'exists', ex=600)
        # return 'DocumentReceived'

    # Verifica si el número existe en caché
    if not redis_client.exists(id_phone_number):
        user_data = {
            'Usuario': '',
            'Telefono': phone_number
        }
        data["user_data"] = user_data
        redis_client.set(id_phone_number, json.dumps(user_data), ex=600)
    else:
        print(id_phone_number)
        data["user_data"] = json.loads(redis_client.get(id_phone_number))
        print(data["user_data"])

    # ID para el historial de chat
    id_chat_history = f'fp-chatHistory:{from_number}'

    dict_conversation_user_supabase = {
        "session_id": str(id_chat_history),
        "phone_number": phone_number,
        "message": body,
        "role": "user",
        "type": message_type
    }
    
    try: 
        print("DICT CONVERSATION SUPABASE", dict_conversation_user_supabase)
    except:
        print("ERROR AL IMPRIMIR DICT CONVERSATION USER SUPABASE")

    # Obtener historial y generar respuesta
    messages = get_chat_history(id_chat_history, telefono=phone_number)
    answer_data = responder_usuario(messages, data, telefono=phone_number, id_conversacion=id_conversacion, id_phone_number=id_phone_number)
    print("--------------------------")
    print('ANSWER DATA', answer_data)
    print("--------------------------")

    dict_conversation_assistant_supabase = {
        "session_id": str(id_chat_history),
        "phone_number": phone_number,
        "message": str(answer_data['answer']),
        "role": "assistant",
        "type": "text"
    }
    
    try: 
        print("DICT CONVERSATION ASSISTANT SUPABASE", dict_conversation_assistant_supabase)
    except:
        print("ERROR AL IMPRIMIR DICT CONVERSATION ASSISTANT SUPABASE")

    # Envía respuesta al usuario con Twilio
    resultado_envio = enviar_mensaje_twilio(
        from_number,
        str(answer_data['answer'])
    )

    # 🔥 CRÍTICO: Solo completar si el envío fue exitoso
    if not resultado_envio.get('success', False):
        print(f"⚠️ ADVERTENCIA: Mensaje no enviado. Error: {resultado_envio.get('error', 'Desconocido')}")
        return 'ErrorEnvio'

    # ✅ Solo si el envío fue exitoso, marcar como procesado
    redis_client.set(dedup_key, 'exists', ex=600)
    print(f"✅ Mensaje marcado como procesado: {dedup_key}")

    # Agregar al historial de chat
    add_to_chat_history(id_chat_history, body, "user", phone_number)
    add_to_chat_history(id_chat_history, answer_data['answer'], "assistant", phone_number)

    print('✅ Procesamiento completado exitosamente.')
    return 'Success'

def procesar_mensajes_entrantes(form_data, redis_client=r):
    print("📥 FORM DATA DE TWILIO:", form_data)
    TEMP_DIR = "./temp_uploads"
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Extraer campos importantes de Twilio
    from_number = form_data.get('From', '')  # whatsapp:+5215512345678
    to_number = form_data.get('To', '')      # whatsapp:+14155238886
    body = form_data.get('Body', '')
    message_sid = form_data.get('MessageSid', '')
    num_media = int(form_data.get('NumMedia', 0))
    
    # Extraer teléfono limpio
    phone_number = extract_phone_from_twilio(from_number)
    print(f"📱 PHONE NUMBER: {phone_number}")

    if not phone_number:
        print("❌ No se pudo extraer número de teléfono")
        return 'NoCommand'

    # Timestamp actual (Twilio no envía timestamp en form data)
    timestamp = int(time.time())

    # 🔥 DEDUPLICACIÓN POR TELÉFONO + MESSAGE_SID
    dedup_key = f"msg:twilio:{message_sid}"
    
    if redis_client.exists(dedup_key):
        print(f"⚠️ Mensaje duplicado detectado: {dedup_key}")
        return 'NoCommand'
    
    print(f"🔍 Procesando mensaje nuevo: {dedup_key}")

    # Determinar tipo de mensaje
    message_type = 'text'
    media_url = ''
    media_content_type = ''
    
    if num_media > 0:
        media_url = form_data.get('MediaUrl0', '')
        media_content_type = form_data.get('MediaContentType0', '')
        
        # Clasificar tipo de mensaje según content type
        if 'image' in media_content_type:
            message_type = 'image'
        elif 'audio' in media_content_type or 'ogg' in media_content_type:
            message_type = 'audio'
        elif 'video' in media_content_type:
            message_type = 'video'
        elif 'application' in media_content_type or 'pdf' in media_content_type:
            message_type = 'document'
        else:
            message_type = 'media'
        
        print(f"📎 Media detectado: {message_type} - {media_url}")

    # Estructura de datos compatible con tu código existente
    data = {
        'id': message_sid,
        'from': from_number,
        'to': to_number,
        'body': body,
        'fromMe': False,  # Twilio solo envía mensajes entrantes
        'type': message_type,
        'pushName': form_data.get('ProfileName', ''),
        'timestamp': timestamp,
        'media': media_url,
        'media_content_type': media_content_type
    }

    print("✅ DATA procesada:", data)

    # 🗑️ COMANDO: BORRAR MEMORIA
    if body and 'borrar memoria' in body.lower():
        print(f"🗑️ Ejecutando borrado de memoria para: {phone_number}")
        reset_chat_history(phone_number)
        resultado = enviar_mensaje_twilio(
            from_number,
            "✅ Tu memoria ha sido borrada."
        )
        if resultado.get('success', False):
            redis_client.set(dedup_key, 'exists', ex=600)
            print(f"✅ Borrar memoria procesado: {dedup_key}")
        return resultado

    # Variables para el resto del flujo
    id_phone_number = f"fp-idPhone:{phone_number}"
    id_conversacion = f"fp-idPhone:{phone_number}_{datetime.now().strftime('%Y-%m-%d_%H:%M')}"

    # ✅ Procesa mensajes de audio (si quieres encolarlos)
    if message_type == 'audio':
        audio_dedup_key = f"audio_queued:{phone_number}:{timestamp}"

        if redis_client.exists(audio_dedup_key):
            print(f"⚠️ Audio ya fue encolado anteriormente: {audio_dedup_key}")
            return 'NoCommand'
        
        redis_client.set(audio_dedup_key, 'queued', ex=300)
        
        # Obtener user_data
        if not redis_client.exists(id_phone_number):
            user_data = {
                'Usuario': '',
                'Telefono': phone_number
            }
            redis_client.set(id_phone_number, json.dumps(user_data), ex=600)
        else:
            user_data = json.loads(redis_client.get(id_phone_number))
        
        # Crear job para el worker (si usas procesamiento asíncrono)
        audio_job = {
            'media_url': media_url,
            'phone_number': phone_number,
            'from': from_number,
            'id_conversacion': id_conversacion,
            'timestamp': timestamp,
            'user_data': user_data,
            'message_sid': message_sid
        }
        
        # Encolar para procesamiento asíncrono
        redis_client.lpush('audio_queue', json.dumps(audio_job))
        
        print(f"✅ Audio encolado para procesamiento: {phone_number}")
        return 'AudioQueued'
    
    # ✅ Procesa mensajes de documento
    if message_type == 'document':
        # ✅ Procesa mensajes de documento
        print(f"📄 Documento recibido: {media_url}")

        # 🔥 BUSCAR SI EL USUARIO YA DIO UN NOMBRE
        nombre_esperado_key = f"doc_nombre:{phone_number}"
        tipo_esperado_key = f"doc_tipo:{phone_number}"
        
        nombre_deseado = redis_client.get(nombre_esperado_key)
        tipo_deseado = redis_client.get(tipo_esperado_key)
        
        # Si hay nombre guardado, usarlo
        if nombre_deseado and tipo_deseado:
            nombre_base = nombre_deseado
            extension = tipo_deseado
            print(f"✅ Usando nombre del usuario: {nombre_base}.{extension}")
            
            # Limpiar después de usar
            redis_client.delete(nombre_esperado_key)
            redis_client.delete(tipo_esperado_key)
        else:
            # Generar nombre automático
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_base = f"documento_{phone_number}_{timestamp_str}"
            
            extensiones = {
                'application/pdf': 'pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
                'image/jpeg': 'jpg',
                'image/png': 'png'
            }
            
            extension = extensiones.get(media_content_type, 'bin')
        
        # Notificar al usuario
        enviar_mensaje_twilio(
            from_number,
            f"📄 Subiendo '{nombre_base}.{extension}' a Google Drive..."
        )
        
        # Descargar archivo de Twilio
        ruta_temporal = descargar_documento_de_twilio(
            media_url=media_url,
            nombre_archivo=nombre_base,
            tipo_archivo=extension
        )
        
        if not ruta_temporal:
            enviar_mensaje_twilio(
                from_number,
                "❌ Lo siento, hubo un error al descargar tu documento."
            )
            redis_client.set(dedup_key, 'exists', ex=600)
            return 'DocumentError'
        
        # Subir a Google Drive
        from google_drive import subir_archivo_a_drive
        
        resultado = subir_archivo_a_drive(
            ruta_archivo_local=ruta_temporal,
            folder_id="1M0TmERmETfEM8flmzwGgfKC7IkrVZaoD"
        )

        # 🔥 AGREGAR A QDRANT
        qdrant_ok = False
        if resultado and resultado.get('success'):
            from function_tools import agregar_documento_a_qdrant

            qdrant_ok = agregar_documento_a_qdrant(
                file_id=resultado['file_id'],
                mime_type=media_content_type,
                nombre=f"{nombre_base}.{extension}",
                ruta=f"Second Brain/{nombre_base}.{extension}",
                ruta_temporal=ruta_temporal
            )

        # Limpiar archivo temporal
        try:
            os.remove(ruta_temporal)
            print(f"🗑️ Archivo temporal eliminado: {ruta_temporal}")
        except:
            pass
        
        # Responder al usuario
        if resultado and resultado.get('success'):
            mensaje = f"✅ Documento '{nombre_base}.{extension}' subido!\n"
            if qdrant_ok:
                mensaje += "📚 Ya disponible para consultas\n"
            mensaje += f"🔗 {resultado['web_view_link']}"
            
            enviar_mensaje_twilio(from_number, mensaje)
        else:
            error_msg = resultado.get('error', 'Desconocido') if resultado else 'Desconocido'
            enviar_mensaje_twilio(
                from_number,
                f"❌ Error al subir a Drive: {error_msg}"
            )
        
        redis_client.set(dedup_key, 'exists', ex=600)
        return 'DocumentProcessed'

        # ==============================================================================
        
        # ==============================================================================
        # este proceso funciona pero no pone el nombre del documento que proporciona el usuario 
        # Notificar al usuario que se está procesando
        # enviar_mensaje_twilio(
        #     from_number,
        #     "📄 He recibido tu documento. Lo estoy procesando y subiré a Drive..."
        # )
        
        # # Extraer nombre del archivo del contenido o generar uno
        # timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        # nombre_base = f"documento_{phone_number}_{timestamp_str}"
        
        # # Detectar extensión del tipo de contenido
        # extensiones = {
        #     'application/pdf': 'pdf',
        #     'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        #     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        #     'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
        #     'image/jpeg': 'jpg',
        #     'image/png': 'png'
        # }
        
        # extension = extensiones.get(media_content_type, 'bin')
        
        # # Descargar archivo de Twilio
        # ruta_temporal = descargar_documento_de_twilio(
        #     media_url=media_url,
        #     nombre_archivo=nombre_base,
        #     tipo_archivo=extension
        # )
        
        # if not ruta_temporal:
        #     enviar_mensaje_twilio(
        #         from_number,
        #         "❌ Lo siento, hubo un error al descargar tu documento."
        #     )
        #     redis_client.set(dedup_key, 'exists', ex=600)
        #     return 'DocumentError'
        
        # resultado = subir_archivo_a_drive(
        #     ruta_archivo_local=ruta_temporal,
        #     # nombre_carpeta="Second Brain",  # O la carpeta que prefieras
        #     # folder_id="1ciaGOxXKcLMNeuIa9103ivxYgBon__7q"  # ID de second brain 
        #     folder_id="1M0TmERmETfEM8flmzwGgfKC7IkrVZaoD" # Id de chat gpt business 
        # )
        
        # # Limpiar archivo temporal
        # try:
        #     os.remove(ruta_temporal)
        #     print(f"🗑️ Archivo temporal eliminado: {ruta_temporal}")
        # except:
        #     pass
        
        # # Responder al usuario
        # if resultado and resultado.get('success'):
        #     mensaje = f"✅ Documento subido exitosamente a Google Drive!\n\n"
        #     mensaje += f"📄 Nombre: {resultado['file_name']}\n"
        #     mensaje += f"🔗 Link: {resultado['web_view_link']}"
            
        #     enviar_mensaje_twilio(from_number, mensaje)
        # else:
        #     error_msg = resultado.get('error', 'Desconocido') if resultado else 'Desconocido'
        #     enviar_mensaje_twilio(
        #         from_number,
        #         f"❌ Error al subir a Drive: {error_msg}"
        #     )
        
        # redis_client.set(dedup_key, 'exists', ex=600)
        # return 'DocumentProcessed'
        # ==============================================================================

        # print(f"📄 Documento recibido: {media_url}")
        # # Aquí puedes procesar el documento
        # # Por ahora solo notificamos al usuario
        # enviar_mensaje_twilio(
        #     from_number,
        #     "📄 He recibido tu documento. Lo estoy procesando..."
        # )
        # # TODO: Implementar descarga y procesamiento del documento
        # redis_client.set(dedup_key, 'exists', ex=600)
        # return 'DocumentReceived'

    # Verifica si el número existe en caché
    if not redis_client.exists(id_phone_number):
        user_data = {
            'Usuario': '',
            'Telefono': phone_number
        }
        data["user_data"] = user_data
        redis_client.set(id_phone_number, json.dumps(user_data), ex=600)
    else:
        print(id_phone_number)
        data["user_data"] = json.loads(redis_client.get(id_phone_number))
        print(data["user_data"])

    # ID para el historial de chat
    id_chat_history = f'fp-chatHistory:{from_number}'

    dict_conversation_user_supabase = {
        "session_id": str(id_chat_history),
        "phone_number": phone_number,
        "message": body,
        "role": "user",
        "type": message_type
    }
    
    try: 
        print("DICT CONVERSATION SUPABASE", dict_conversation_user_supabase)
    except:
        print("ERROR AL IMPRIMIR DICT CONVERSATION USER SUPABASE")

    # Obtener historial y generar respuesta
    messages = get_chat_history(id_chat_history, telefono=phone_number)
    answer_data = responder_usuario(messages, data, telefono=phone_number, id_conversacion=id_conversacion, id_phone_number=id_phone_number)
    print("--------------------------")
    print('ANSWER DATA', answer_data)
    print("--------------------------")

    dict_conversation_assistant_supabase = {
        "session_id": str(id_chat_history),
        "phone_number": phone_number,
        "message": str(answer_data['answer']),
        "role": "assistant",
        "type": "text"
    }
    
    try: 
        print("DICT CONVERSATION ASSISTANT SUPABASE", dict_conversation_assistant_supabase)
    except:
        print("ERROR AL IMPRIMIR DICT CONVERSATION ASSISTANT SUPABASE")

    answer_text = str(answer_data['answer'])

    # 🔥 LIMITAR A 1600 CARACTERES (WhatsApp permite hasta 1600)
    MAX_LENGTH = 1520  # Dejamos margen

    if len(answer_text) > MAX_LENGTH:
        answer_text = answer_text[:MAX_LENGTH] + "\n\n... (respuesta truncada)\n💡 Haz una pregunta más específica para obtener detalles."
        print(f"⚠️ Respuesta truncada de {len(answer_data['answer'])} a {MAX_LENGTH} caracteres")

    # Envía respuesta al usuario con Twilio
    resultado_envio = enviar_mensaje_twilio(
        from_number,
        answer_text  # 🔥 Usar la versión truncada
    )
    
    # Envía respuesta al usuario con Twilio
    # resultado_envio = enviar_mensaje_twilio(
    #     from_number,
    #     str(answer_data['answer'])
    # )

    # 🔥 CRÍTICO: Solo completar si el envío fue exitoso
    if not resultado_envio.get('success', False):
        print(f"⚠️ ADVERTENCIA: Mensaje no enviado. Error: {resultado_envio.get('error', 'Desconocido')}")
        return 'ErrorEnvio'

    # ✅ Solo si el envío fue exitoso, marcar como procesado
    redis_client.set(dedup_key, 'exists', ex=600)
    print(f"✅ Mensaje marcado como procesado: {dedup_key}")

    # Agregar al historial de chat
    add_to_chat_history(id_chat_history, body, "user", phone_number)
    add_to_chat_history(id_chat_history, answer_data['answer'], "assistant", phone_number)

    print('✅ Procesamiento completado exitosamente.')
    return 'Success'

if __name__ == "__main__":

    telefono = "whatsapp:+5215566098295"
    texto = "Hola, este es un mensaje de prueba desde el script principal."

    enviar_mensaje_twilio(telefono, texto, max_retries=3)