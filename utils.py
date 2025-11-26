# python3 utils.py

from datetime import datetime
from dotenv import load_dotenv

import json
import os
import redis
import requests
import tiktoken

load_dotenv()

INSTANCIA_ULTRAMSG=os.getenv('INSTANCIA_ULTRAMSG')
TOKEN_ULTRAMSG=os.getenv('TOKEN_ULTRAMSG')
WEBHOOK_RENDER=os.getenv('WEBHOOK_RENDER')

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")

redis_metadata_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username="default",
    password=redis_password,
)

# 🔥 NUEVO: TTL de 24 horas (en lugar de 10 minutos)
METADATA_TTL = 86400  # 24 horas en segundos

def enviar_imagen_ultramsg(telefono, url_imagen, caption=None, msgID=None, INSTANCIA_ULTRAMSG=None, token_ultramsg=None):
    """
    Envía una imagen por UltraMSG usando su API REST.

    Parámetros:
    - telefono (str): número destino en formato internacional completo, incluyendo el signo +
                      ej. "+5219991234567"
    - url_imagen (str): URL pública de la imagen
    - caption (str): texto opcional para mostrar como pie de imagen
    - msgID (str): opcional, ID del mensaje al que se responde
    """

    telefono = f"521{telefono}"

    if not telefono.startswith("+"):
        telefono = f"+{telefono}"

    url = f"https://api.ultramsg.com/{INSTANCIA_ULTRAMSG}/messages/image"

    # Usa el caption si se proporcionó, si no deja vacío
    caption = caption or ""

    # Construir el payload como string plano
    payload = f"token={token_ultramsg}&to={telefono}&image={url_imagen}&caption={caption}"
    payload = payload.encode('utf8').decode('iso-8859-1')

    headers = {'content-type': 'application/x-www-form-urlencoded'}

    response = requests.request("POST", url, data=payload, headers=headers)

    print(response.status_code, response.text)
    return response

def extract_phone_from_ultra_msg(data_from: str) -> str:
    posicion_arroba = data_from.find('@')
    return data_from[posicion_arroba-10:posicion_arroba]

def num_tokens_from_string(string: str, encoding_name: str) -> int:

    encoding = tiktoken.get_encoding("cl100k_base")

    if isinstance(string, str):
        tokens = len(encoding.encode(string))
    elif isinstance(string, list):
        tokens = sum(len(encoding.encode(t)) for t in string)

    return tokens

# 🔥 NUEVA VERSIÓN CON REDIS + AUTO-REFRESH
def get_metadata(telefono):
    """
    Obtiene metadata de Redis con auto-refresh del TTL
    Si no existe, crea metadata por defecto
    """
    # Limpiar número de teléfono
    telefono_limpio = telefono.replace('@s.whatsapp.net', '')
    if telefono_limpio.startswith('521'):
        telefono_limpio = telefono_limpio[3:]  # Quitar prefijo 521
    
    key = f"metadata:{telefono_limpio}"
    
    try:
        # Intentar obtener de Redis
        data = redis_metadata_client.get(key)
        
        if data:
            metadata = json.loads(data)
            
            # ✅ AUTO-REFRESH: Extender TTL cada vez que se accede
            redis_metadata_client.expire(key, METADATA_TTL)
            
            print(f"✅ Metadata recuperada de Redis: {telefono_limpio} | Fase: {metadata.get('fase_actual')}")
            return metadata
        
        # Si no existe, crear metadata por defecto
        print(f"⚠️ No existe metadata para {telefono_limpio}, creando nueva...")
        
    except Exception as e:
        print(f"⚠️ Error al obtener metadata de Redis: {e}")
    
    # Metadata por defecto
    default_metadata = {
        'fase_actual': 1,
        'problema_mencionado': False,
        'problema_identificado': False,
        'problema_detalle': '',
        'producto_presentado_tecnico': False,
        'metricas_mostradas': False,
        'opcion_elegida': None,
        'timestamp_fase_3a': None,
        'nombre_usuario': None,
        'created_at': datetime.now().isoformat()
    }
    
    # Guardar metadata inicial en Redis
    save_metadata(telefono, default_metadata)
    return default_metadata

# 🔥 NUEVA VERSIÓN CON REDIS
def save_metadata(telefono, metadata):
    """
    Guarda metadata en Redis con TTL de 24 horas
    También mantiene backup en archivo local
    """
    # Limpiar número de teléfono
    telefono_limpio = telefono.replace('@s.whatsapp.net', '')
    if telefono_limpio.startswith('521'):
        telefono_limpio = telefono_limpio[3:]  # Quitar prefijo 521
    
    key = f"metadata:{telefono_limpio}"
    
    # Agregar timestamp de última actualización
    metadata['updated_at'] = datetime.now().isoformat()
    
    try:
        # Guardar en Redis con TTL de 24 horas
        redis_metadata_client.set(key, json.dumps(metadata), ex=METADATA_TTL)
        
        print(f"✅ Metadata guardada en Redis: {telefono_limpio} | Fase: {metadata.get('fase_actual')} | TTL: 24h")
        
    except Exception as e:
        print(f"❌ ERROR al guardar metadata en Redis: {e}")
    
    # 💾 BACKUP: También guardar en archivo local como fallback
    try:
        os.makedirs("metadata", exist_ok=True)
        metadata_file = f"metadata/metadata_{telefono_limpio}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"💾 Backup en archivo local: {metadata_file}")
    except Exception as e:
        print(f"⚠️ Error al guardar backup local: {e}")

def agregar_prompt(prefijo, texto, archivo="system_prompt.py"):
    nombre_variable = f"PROMPT_{prefijo.upper()}"

    prompt_formateado = f'\n{nombre_variable} = """\n{texto}\n"""\n'

    with open(archivo, 'a', encoding='utf-8') as f:
        f.write(prompt_formateado)
    
    print(f"✅ Prompt agregado: {nombre_variable}")

# 🔥 ACTUALIZADA: Borrar de Redis y archivo
def borrar_metadata(telefono, metadata_dir="metadata"):
    """
    Borra metadata de Redis Y del archivo local
    """
    # Limpiar el número
    telefono_limpio = telefono.replace('@s.whatsapp.net', '')
    if telefono_limpio.startswith('521'):
        telefono_limpio = telefono_limpio[3:]
    
    success = False
    
    # 1. Borrar de Redis
    try:
        key = f"metadata:{telefono_limpio}"
        deleted = redis_metadata_client.delete(key)
        if deleted:
            print(f"✅ Metadata borrada de Redis: {telefono_limpio}")
            success = True
        else:
            print(f"⚠️ No se encontró metadata en Redis para: {telefono_limpio}")
    except Exception as e:
        print(f"❌ Error al borrar de Redis: {e}")
    
    # 2. Borrar archivo local (backup)
    posibles_nombres = [
        f"metadata_{telefono_limpio}.json",
        f"metadata_521{telefono_limpio}.json",
    ]
    
    archivo_encontrado = None
    for nombre in posibles_nombres:
        filepath = os.path.join(metadata_dir, nombre)
        if os.path.exists(filepath):
            archivo_encontrado = filepath
            break
    
    if archivo_encontrado:
        try:
            os.remove(archivo_encontrado)
            print(f"✅ Archivo local borrado: {archivo_encontrado}")
            success = True
        except Exception as e:
            print(f"❌ Error al borrar archivo: {e}")
    else:
        print(f"⚠️ No se encontró archivo local para: {telefono_limpio}")
    
    return success

if __name__ == "__main__":

    # agregar_prompt(
    #     prefijo="TEST_1",
    #     texto="""
    # INSTRUCCIONES PARA SALUDO INICIAL
    # Tu objetivo: Saludar + preguntar por el problema
    # ...
    # """
    # )
    # export_logs_to_txt(
    #     # phone_number="5513805760",
    #     phone_number="9765455060",
    #     # phone_number="9095535860",
    #     agent_name="Agrobotanix", 
    #     output_dir="logs_exports"
    # )
    print("✅")