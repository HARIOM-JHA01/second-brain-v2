# python3 chat_history.py

import json
import os
import redis
import tiktoken
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')

# Configuración de conexión a Redis
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")

TIEMPO_NUEVO = int(os.getenv("TIEMPO_NUEVO")) if os.getenv("TIEMPO_NUEVO") else 60 * 10

redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username="default",
    password=redis_password,
)

MAX_MESSAGES_IN_MEMORY = 12  # Solo últimos 15 mensajes por defecto

def add_to_chat_history(id_chat_history, message, role, telefono):
    """
    Agrega mensaje al historial en Redis
    """
    try:
        history = redis_client.get(id_chat_history)
        
        if history:
            history = json.loads(history)
        else:
            history = []
        
        history.append({
            "role": role,
            "content": message
        })
        
        # 🔥 NUEVO: Mantener solo últimos MAX_MESSAGES_IN_MEMORY mensajes
        if len(history) > MAX_MESSAGES_IN_MEMORY:
            history = history[-MAX_MESSAGES_IN_MEMORY:]
            print(f"🔄 Historial truncado a {MAX_MESSAGES_IN_MEMORY} mensajes para {telefono}")
        
        redis_client.set(id_chat_history, json.dumps(history), ex=3600)
        
    except Exception as e:
        print(f"❌ Error al agregar mensaje al historial: {e}")

def get_chat_history(id_chat_history, telefono=None, limit=MAX_MESSAGES_IN_MEMORY):
    """
    Obtiene historial de chat desde Redis
    
    Args:
        id_chat_history: ID del chat
        telefono: Número de teléfono (opcional, para logs)
        limit: Cantidad máxima de mensajes a retornar (default: MAX_MESSAGES_IN_MEMORY)
    
    Returns:
        list: Últimos N mensajes del historial
    """
    try:
        history = redis_client.get(id_chat_history)
        
        if history:
            history = json.loads(history)
            
            # 🔥 NUEVO: Aplicar límite al retornar
            if len(history) > limit:
                history = history[-limit:]
                print(f"📊 Retornando últimos {limit} mensajes de {len(history)} totales para {telefono}")
            
            return history
        
        return []
    
    except Exception as e:
        print(f"❌ Error al obtener historial: {e}")
        return []

def num_tokens(text, model="gpt-4o"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def reset_chat_history(chat_history_id, redis_client=redis_client):
    """
    Elimina el historial de chat de Redis (versión mejorada)
    """
    # Si no tiene el prefijo, agregarlo
    if not chat_history_id.startswith('fp-chatHistory:'):
        chat_history_id = f'fp-chatHistory:{chat_history_id}'
    
    # Verificar si existe antes de borrar
    existe = redis_client.exists(chat_history_id)
    
    if not existe:
        print(f"⚠️  La key '{chat_history_id}' NO existe en Redis")
        
        # Buscar keys similares
        telefono = chat_history_id.replace('fp-chatHistory:', '')
        pattern = f'fp-chatHistory:*{telefono}*'
        keys_similares = redis_client.keys(pattern)
        
        if keys_similares:
            print(f"💡 Keys similares encontradas:")
            for key in keys_similares:
                print(f"   - {key}")
            
            # Borrar la primera coincidencia
            if keys_similares:
                ans = redis_client.delete(keys_similares[0])
                print(f"✅ Historial '{keys_similares[0]}' eliminado")
                return ans
        
        return 0
    
    # Eliminar
    ans = redis_client.delete(chat_history_id)
    
    if ans > 0:
        print(f"✅ Historial '{chat_history_id}' reiniciado exitosamente")
    else:
        print(f"❌ Error al eliminar '{chat_history_id}'")
    
    return ans

def listar_chat_histories(redis_client=redis_client):
    """
    Lista todos los chat histories almacenados en Redis
    """
    # Buscar todas las keys que empiezan con 'fp-chatHistory:'
    pattern = 'fp-chatHistory:*'
    keys = redis_client.keys(pattern)
    
    print(f"\n{'='*60}")
    print(f"📊 TOTAL DE CHAT HISTORIES: {len(keys)}")
    print(f"{'='*60}\n")
    
    if not keys:
        print("❌ No hay chat histories almacenados en Redis")
        return []
    
    for key in keys:
        # Obtener el contenido
        content = redis_client.get(key)
        
        # Extraer el número de teléfono
        telefono = key.replace('fp-chatHistory:', '')
        
        # Contar mensajes (si es JSON list)
        try:
            mensajes = json.loads(content) if content else []
            num_mensajes = len(mensajes)
        except:
            num_mensajes = "N/A"
        
        print(f"📱 {telefono}")
        print(f"   Key completa: {key}")
        print(f"   Mensajes: {num_mensajes}")
        print(f"   TTL: {redis_client.ttl(key)} segundos")
        print("-" * 60)
    
    return keys

if __name__ == "__main__":
    reset_chat_history('5215566098295')
    # listar_chat_histories()
