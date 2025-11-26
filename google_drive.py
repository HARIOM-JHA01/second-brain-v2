# python3 google_drive.py

import datetime
import io
import json
import os
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv
from typing import List, Dict
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI

load_dotenv()

qdrant_host = os.getenv("QDRANT_URL", "")
qdrant_api_key = os.getenv("QDRANT_API_KEY", "")

openai_embeddings_model = os.getenv("OPENAI_EMBEDDINGS_MODEL", "")
openai_api_key = os.getenv("OPENAI_API_KEY", "")

client = OpenAI(api_key=openai_api_key)

load_dotenv()

DRIVE_CREDENTIALS =  os.getenv("DRIVE_CREDENTIALS", "DRIVE_CREDENTIALS.json")
DRIVE_TOKENS = os.getenv("DRIVE_TOKENS", "token.json")

def obtener_servicio():
    creds = None
    SCOPES = [
        "https://www.googleapis.com/auth/drive"
    ]
    CREDENTIALS_PATH = os.path.join(
        os.path.dirname(__file__), DRIVE_CREDENTIALS
    )
    TOKENS_PATH = os.path.join(
        os.path.dirname(__file__), DRIVE_TOKENS
    )

    if os.path.exists(TOKENS_PATH):
        creds = Credentials.from_authorized_user_file(
            TOKENS_PATH, SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=8080)
            # creds = flow.run_console()

        with open(TOKENS_PATH, "w") as token:
            token.write(creds.to_json())

    try:
        return build("drive", "v3", credentials=creds)

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def listar_todas_las_carpetas():
    """
    Lista TODAS las carpetas en Google Drive
    
    Returns:
        List[Dict]: Lista de carpetas con id, name, createdTime, etc.
    """
    service = obtener_servicio()
    
    if not service:
        print("❌ No se pudo obtener el servicio de Drive")
        return []
    
    try:
        print("🔍 Buscando carpetas en Google Drive...")
        
        # Query para obtener solo carpetas
        query = "mimeType='application/vnd.google-apps.folder'"
        
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, createdTime, modifiedTime, parents, webViewLink)",
            orderBy="name"
        ).execute()
        
        carpetas = results.get('files', [])
        
        if not carpetas:
            print('⚠️ No se encontraron carpetas.')
            return []
        
        print(f'\n📂 Carpetas encontradas: {len(carpetas)}\n')
        print("=" * 80)
        
        for carpeta in carpetas:
            print(f"📁 Nombre: {carpeta['name']}")
            print(f"   ID: {carpeta['id']}")
            print(f"   Link: {carpeta.get('webViewLink', 'N/A')}")
            print(f"   Modificado: {carpeta.get('modifiedTime', 'N/A')}")
            print("-" * 80)
        
        return carpetas
        
    except HttpError as error:
        print(f'❌ Error listando carpetas: {error}')
        return []

def buscar_carpeta_por_nombre(nombre_carpeta):
    """
    Busca una carpeta por su nombre exacto o parcial
    
    Args:
        nombre_carpeta (str): Nombre de la carpeta a buscar
    
    Returns:
        List[Dict]: Lista de carpetas que coinciden con el nombre
    """
    service = obtener_servicio()
    
    if not service:
        print("❌ No se pudo obtener el servicio de Drive")
        return []
    
    try:
        print(f"🔍 Buscando carpeta: '{nombre_carpeta}'...")
        
        # Query para buscar carpetas con nombre específico
        query = f"mimeType='application/vnd.google-apps.folder' and name contains '{nombre_carpeta}'"
        
        results = service.files().list(
            q=query,
            pageSize=50,
            fields="files(id, name, createdTime, modifiedTime, webViewLink)"
        ).execute()
        
        carpetas = results.get('files', [])
        
        if not carpetas:
            print(f'⚠️ No se encontró ninguna carpeta con nombre "{nombre_carpeta}"')
            return []
        
        print(f'\n✅ Encontradas {len(carpetas)} carpeta(s):\n')
        for carpeta in carpetas:
            print(f"📁 {carpeta['name']}")
            print(f"   ID: {carpeta['id']}")
            print(f"   Link: {carpeta.get('webViewLink', 'N/A')}")
            print("-" * 40)
        
        return carpetas
        
    except HttpError as error:
        print(f'❌ Error buscando carpeta: {error}')
        return []

def listar_archivos_en_carpeta(nombre_carpeta=None, folder_id=None):
    """
    Lista todos los archivos dentro de una carpeta específica
    
    Args:
        nombre_carpeta (str): Nombre de la carpeta (buscará por nombre)
        folder_id (str): ID de la carpeta (más preciso)
    
    Returns:
        List[Dict]: Lista de archivos en la carpeta
    """
    service = obtener_servicio()
    
    if not service:
        print("❌ No se pudo obtener el servicio de Drive")
        return []
    
    try:
        # Si no tenemos folder_id, buscar por nombre
        if not folder_id and nombre_carpeta:
            carpetas = buscar_carpeta_por_nombre(nombre_carpeta)
            if not carpetas:
                return []
            folder_id = carpetas[0]['id']
            print(f"\n📂 Usando carpeta: {carpetas[0]['name']} (ID: {folder_id})")
        
        if not folder_id:
            print("❌ Debes proporcionar nombre_carpeta o folder_id")
            return []
        
        print(f"\n🔍 Listando archivos en la carpeta...")
        
        # Query para obtener archivos dentro de la carpeta
        query = f"'{folder_id}' in parents"
        
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink, webContentLink)",
            orderBy="name"
        ).execute()
        
        archivos = results.get('files', [])
        
        if not archivos:
            print('⚠️ La carpeta está vacía.')
            return []
        
        print(f'\n📄 Archivos encontrados: {len(archivos)}\n')
        print("=" * 80)
        
        for archivo in archivos:
            print(f"📄 Nombre: {archivo['name']}")
            print(f"   ID: {archivo['id']}")
            print(f"   Tipo: {archivo['mimeType']}")
            
            if 'size' in archivo:
                size_mb = int(archivo['size']) / (1024 * 1024)
                print(f"   Tamaño: {size_mb:.2f} MB")
            
            print(f"   Link: {archivo.get('webViewLink', 'N/A')}")
            print(f"   Modificado: {archivo.get('modifiedTime', 'N/A')}")
            print("-" * 80)
        
        return archivos
        
    except HttpError as error:
        print(f'❌ Error listando archivos: {error}')
        return []

def obtener_id_carpeta_por_nombre(nombre_carpeta):
    """
    Obtiene el ID de una carpeta dado su nombre
    
    Args:
        nombre_carpeta (str): Nombre de la carpeta
    
    Returns:
        str: ID de la carpeta o None si no se encuentra
    """
    carpetas = buscar_carpeta_por_nombre(nombre_carpeta)
    
    if carpetas:
        return carpetas[0]['id']
    
    return None

def descargar_archivo(file_id, ruta_destino):
    """
    Descarga un archivo de Google Drive
    
    Args:
        file_id (str): ID del archivo en Drive
        ruta_destino (str): Ruta donde guardar el archivo
    
    Returns:
        bool: True si se descargó exitosamente
    """
    service = obtener_servicio()
    
    if not service:
        print("❌ No se pudo obtener el servicio de Drive")
        return False
    
    try:
        print(f"📥 Descargando archivo...")
        
        request = service.files().get_media(fileId=file_id)
        
        fh = io.FileIO(ruta_destino, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"📊 Descarga {int(status.progress() * 100)}%")
        
        print(f"✅ Archivo descargado en: {ruta_destino}")
        return True
        
    except HttpError as error:
        print(f'❌ Error descargando archivo: {error}')
        return False

# ============================================================================
# FUNCIONES DE PRUEBA
# ============================================================================

def buscar_carpetas_drive(nombre_carpeta=None, folder_id=None):
    """
    Busca carpetas en Google Drive por nombre o ID
    
    Args:
        nombre_carpeta (str, optional): Nombre de la carpeta a buscar (puede ser parcial)
        folder_id (str, optional): ID específico de la carpeta
    
    Returns:
        List[Dict]: Lista de carpetas encontradas
    """
    service = obtener_servicio()
    
    if not service:
        print("❌ No se pudo obtener el servicio de Drive")
        return []
    
    try:
        # Si tenemos folder_id, buscar directamente por ID
        if folder_id:
            print(f"🔍 Buscando carpeta con ID: {folder_id}")
            
            carpeta = service.files().get(
                fileId=folder_id,
                fields="id, name, createdTime, modifiedTime, webViewLink, parents"
            ).execute()
            
            # Verificar que sea una carpeta
            if carpeta.get('mimeType') != 'application/vnd.google-apps.folder':
                print(f"⚠️ El ID proporcionado no es una carpeta")
                return []
            
            print(f"\n✅ Carpeta encontrada:")
            print(f"📁 Nombre: {carpeta['name']}")
            print(f"   ID: {carpeta['id']}")
            print(f"   Link: {carpeta.get('webViewLink', 'N/A')}")
            print(f"   Modificado: {carpeta.get('modifiedTime', 'N/A')}")
            
            return [carpeta]
        
        # Si tenemos nombre, buscar por nombre
        if nombre_carpeta:
            print(f"🔍 Buscando carpetas con nombre: '{nombre_carpeta}'")
            
            # Query para buscar solo carpetas con el nombre
            query = f"mimeType='application/vnd.google-apps.folder' and name contains '{nombre_carpeta}'"
            
            results = service.files().list(
                q=query,
                pageSize=50,
                fields="files(id, name, createdTime, modifiedTime, webViewLink, parents)",
                orderBy="name"
            ).execute()
            
            carpetas = results.get('files', [])
            
            if not carpetas:
                print(f'⚠️ No se encontraron carpetas con nombre "{nombre_carpeta}"')
                return []
            
            print(f'\n✅ Encontradas {len(carpetas)} carpeta(s):\n')
            print("=" * 80)
            
            for carpeta in carpetas:
                print(f"📁 Nombre: {carpeta['name']}")
                print(f"   ID: {carpeta['id']}")
                print(f"   Link: {carpeta.get('webViewLink', 'N/A')}")
                print(f"   Modificado: {carpeta.get('modifiedTime', 'N/A')}")
                print("-" * 80)
            
            return carpetas
        
        print("❌ Debes proporcionar nombre_carpeta o folder_id")
        return []
        
    except HttpError as error:
        print(f'❌ Error buscando carpeta: {error}')
        return []

def listar_carpetas_limitadas(limit=100):
    """
    Lista las primeras N carpetas en Google Drive
    
    Args:
        limit (int): Número de carpetas a mostrar (default: 10)
    
    Returns:
        List[Dict]: Lista de carpetas encontradas
    """
    service = obtener_servicio()
    
    if not service:
        print("❌ No se pudo obtener el servicio de Drive")
        return []
    
    try:
        print(f"🔍 Buscando las primeras {limit} carpetas en Google Drive...")
        
        # Query para obtener solo carpetas
        query = "mimeType='application/vnd.google-apps.folder'"
        
        results = service.files().list(
            q=query,
            pageSize=limit,  # 🔥 Limitar aquí
            fields="nextPageToken, files(id, name, createdTime, modifiedTime, parents, webViewLink)",
            orderBy="name"
        ).execute()
        
        carpetas = results.get('files', [])
        
        if not carpetas:
            print('⚠️ No se encontraron carpetas.')
            return []
        
        print(f'\n📂 Mostrando {len(carpetas)} carpeta(s):\n')
        print("=" * 80)
        
        for i, carpeta in enumerate(carpetas, 1):
            print(f"{i}. 📁 Nombre: {carpeta['name']} --- ID: {carpeta['id']}")
            # print(f"   ID: {carpeta['id']}")
            print(f"   Link: {carpeta.get('webViewLink', 'N/A')}")
            # print(f"   Modificado: {carpeta.get('modifiedTime', 'N/A')}")
            print("-" * 80)
        
        return carpetas
        
    except HttpError as error:
        print(f'❌ Error listando carpetas: {error}')
        return []

def subir_archivo_a_drive(ruta_archivo_local, nombre_carpeta=None, folder_id=None):
    """
    Sube un archivo desde tu computadora local a Google Drive
    
    Args:
        ruta_archivo_local (str): Ruta del archivo en tu computadora (ej: "./documento.xlsx")
        nombre_carpeta (str, optional): Nombre de la carpeta destino en Drive
        folder_id (str, optional): ID de la carpeta destino (más preciso)
    
    Returns:
        dict: Información del archivo subido (id, name, webViewLink)
    """
    service = obtener_servicio()
    
    if not service:
        print("❌ No se pudo obtener el servicio de Drive")
        return None
    
    # Verificar que el archivo existe
    if not os.path.exists(ruta_archivo_local):
        print(f"❌ El archivo no existe: {ruta_archivo_local}")
        return None
    
    try:
        # Obtener el nombre del archivo
        nombre_archivo = os.path.basename(ruta_archivo_local)
        
        # Si tenemos nombre de carpeta pero no ID, buscarlo
        if nombre_carpeta and not folder_id:
            carpetas = buscar_carpetas_drive(nombre_carpeta=nombre_carpeta)
            if carpetas:
                folder_id = carpetas[0]['id']
                print(f"📁 Usando carpeta: {carpetas[0]['name']} (ID: {folder_id})")
            else:
                print(f"⚠️ No se encontró la carpeta '{nombre_carpeta}'. Subiendo a raíz.")
        
        # Detectar el tipo MIME según la extensión
        mime_types = {
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png'
        }
        
        extension = os.path.splitext(nombre_archivo)[1].lower()
        mime_type = mime_types.get(extension, 'application/octet-stream')
        
        print(f"📤 Subiendo archivo: {nombre_archivo}")
        print(f"   Tipo: {mime_type}")
        print(f"   Tamaño: {os.path.getsize(ruta_archivo_local) / 1024:.2f} KB")
        
        # Metadata del archivo
        file_metadata = {
            'name': nombre_archivo
        }
        
        # Si tenemos folder_id, agregarlo
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        # Leer el archivo
        from googleapiclient.http import MediaFileUpload
        
        media = MediaFileUpload(
            ruta_archivo_local,
            mimetype=mime_type,
            resumable=True
        )
        
        # Subir el archivo
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, webContentLink, size'
        ).execute()
        
        size_mb = int(file.get('size', 0)) / (1024 * 1024)
        
        print(f"\n✅ Archivo subido exitosamente!")
        print(f"📄 Nombre: {file.get('name')}")
        print(f"🆔 ID: {file.get('id')}")
        print(f"📊 Tamaño: {size_mb:.2f} MB")
        print(f"🔗 Link: {file.get('webViewLink')}")
        
        return {
            'success': True,
            'file_id': file.get('id'),
            'file_name': file.get('name'),
            'web_view_link': file.get('webViewLink'),
            'web_content_link': file.get('webContentLink'),
            'size': file.get('size')
        }
        
    except HttpError as error:
        print(f'❌ Error subiendo archivo: {error}')
        return {'success': False, 'error': str(error)}
    except Exception as e:
        print(f'❌ Error inesperado: {e}')
        return {'success': False, 'error': str(e)}

# ============================================================================
# PRUEBAS
# ============================================================================
def obtener_todos_los_archivos_recursivamente(folder_id, nivel=0):
    """
    Obtiene TODOS los archivos dentro de una carpeta de forma recursiva
    (incluye archivos en subcarpetas)
    
    Args:
        folder_id (str): ID de la carpeta principal
        nivel (int): Nivel de profundidad (para debugging)
    
    Returns:
        List[Dict]: Lista con TODOS los archivos encontrados
    """
    service = obtener_servicio()
    
    if not service:
        print("❌ No se pudo obtener el servicio de Drive")
        return []
    
    todos_los_archivos = []
    indent = "  " * nivel
    
    try:
        print(f"{indent}🔍 Explorando carpeta (nivel {nivel})...")
        
        # Query para obtener TODO dentro de la carpeta
        query = f"'{folder_id}' in parents"
        
        results = service.files().list(
            q=query,
            pageSize=1000,
            fields="files(id, name, mimeType, size, webViewLink, parents)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print(f"{indent}⚠️ Carpeta vacía")
            return []
        
        print(f"{indent}📦 Encontrados {len(items)} items")
        
        for item in items:
            item_type = item.get('mimeType', '')
            
            # Si es una CARPETA, explorarla recursivamente
            if item_type == 'application/vnd.google-apps.folder':
                print(f"{indent}📁 Carpeta: {item['name']} (ID: {item['id']})")
                
                # 🔥 RECURSIÓN: Explorar esta carpeta
                archivos_en_subcarpeta = obtener_todos_los_archivos_recursivamente(
                    item['id'], 
                    nivel + 1
                )
                
                # Agregar todos los archivos encontrados en la subcarpeta
                todos_los_archivos.extend(archivos_en_subcarpeta)
            
            # Si es un ARCHIVO, agregarlo a la lista
            else:
                print(f"{indent}📄 Archivo: {item['name']} (ID: {item['id']})")
                todos_los_archivos.append(item)
        
        return todos_los_archivos
        
    except HttpError as error:
        print(f'{indent}❌ Error: {error}')
        return []

def obtener_estructura_completa_con_paths(folder_id, ruta_actual="", nivel=0):
    """
    Obtiene TODOS los archivos con sus rutas completas
    
    Args:
        folder_id (str): ID de la carpeta principal
        ruta_actual (str): Ruta acumulada
        nivel (int): Nivel de profundidad
    
    Returns:
        List[Dict]: Lista con archivos y sus rutas
    """
    service = obtener_servicio()
    
    if not service:
        return []
    
    todos_los_archivos = []
    indent = "  " * nivel
    
    try:
        query = f"'{folder_id}' in parents"
        
        results = service.files().list(
            q=query,
            pageSize=1000,
            fields="files(id, name, mimeType, size, webViewLink)"
        ).execute()
        
        items = results.get('files', [])
        
        for item in items:
            item_type = item.get('mimeType', '')
            nombre = item['name']
            nueva_ruta = f"{ruta_actual}/{nombre}" if ruta_actual else nombre
            
            if item_type == 'application/vnd.google-apps.folder':
                print(f"{indent}📁 {nueva_ruta}")
                
                # Recursión en subcarpeta
                archivos_en_subcarpeta = obtener_estructura_completa_con_paths(
                    item['id'], 
                    nueva_ruta,
                    nivel + 1
                )
                
                todos_los_archivos.extend(archivos_en_subcarpeta)
            
            else:
                print(f"{indent}📄 {nueva_ruta}")
                
                # Agregar archivo con su ruta
                archivo_con_ruta = item.copy()
                archivo_con_ruta['ruta'] = nueva_ruta
                archivo_con_ruta['nivel'] = nivel
                
                todos_los_archivos.append(archivo_con_ruta)
        
        return todos_los_archivos
        
    except HttpError as error:
        print(f'{indent}❌ Error: {error}')
        return []

def guardar_estructura_en_json(folder_id, nombre_archivo="estructura_drive.json"):
    """
    Guarda toda la estructura en un archivo JSON
    
    Args:
        folder_id (str): ID de la carpeta principal
        nombre_archivo (str): Nombre del archivo JSON de salida
    """
    print("🔍 Obteniendo estructura completa del Drive...")
    
    archivos = obtener_estructura_completa_con_paths(folder_id)
    
    print(f"\n✅ Total de archivos encontrados: {len(archivos)}")
    
    # Guardar en JSON
    with open(nombre_archivo, 'w', encoding='utf-8') as f:
        json.dump(archivos, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Estructura guardada en: {nombre_archivo}")
    
    return archivos


# ============================================================================
# Scripts para leer archivos desde drive 
# ============================================================================
import PyPDF2
from io import BytesIO

def extraer_texto_de_archivo(file_id, mime_type):
    """
    Extrae el texto de un archivo (PDF o Google Doc)
    
    Args:
        file_id (str): ID del archivo en Drive
        mime_type (str): Tipo MIME del archivo
    
    Returns:
        str: Texto extraído del archivo
    """
    service = obtener_servicio()
    
    if not service:
        print("❌ No se pudo obtener el servicio de Drive")
        return None
    
    try:
        # Para PDFs
        if mime_type == 'application/pdf':
            print(f"📄 Extrayendo texto de PDF...")
            
            # Descargar el PDF
            request = service.files().get_media(fileId=file_id)
            file_data = BytesIO()
            downloader = MediaIoBaseDownload(file_data, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_data.seek(0)
            
            # Extraer texto con PyPDF2
            pdf_reader = PyPDF2.PdfReader(file_data)
            texto_completo = ""
            
            for page_num, page in enumerate(pdf_reader.pages):
                texto = page.extract_text()
                texto_completo += f"\n--- Página {page_num + 1} ---\n{texto}\n"
            
            return texto_completo
        
        # Para Google Docs
        elif mime_type == 'application/vnd.google-apps.document':
            print(f"📝 Extrayendo texto de Google Doc...")
            
            # Exportar como texto plano
            request = service.files().export_media(
                fileId=file_id,
                mimeType='text/plain'
            )
            
            file_data = BytesIO()
            downloader = MediaIoBaseDownload(file_data, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_data.seek(0)
            texto = file_data.read().decode('utf-8')
            
            return texto
        
        else:
            print(f"⚠️ Tipo de archivo no soportado: {mime_type}")
            return None
            
    except Exception as e:
        print(f"❌ Error extrayendo texto: {e}")
        return None

def procesar_todos_los_documentos(archivos_json="estructura_second_brain.json"):
    """
    Procesa TODOS los PDFs y Google Docs de la estructura
    
    Args:
        archivos_json (str): Ruta al archivo JSON con la estructura
    
    Returns:
        List[Dict]: Lista con archivos y su texto extraído
    """
    # Cargar estructura
    with open(archivos_json, 'r', encoding='utf-8') as f:
        archivos = json.load(f)
    
    # Filtrar solo PDFs y Google Docs
    tipos_soportados = [
        'application/pdf',
        'application/vnd.google-apps.document'
    ]
    
    archivos_a_procesar = [
        archivo for archivo in archivos 
        if archivo.get('mimeType') in tipos_soportados
    ]
    
    print(f"📚 Archivos a procesar: {len(archivos_a_procesar)}")
    print(f"   PDFs: {sum(1 for a in archivos_a_procesar if a['mimeType'] == 'application/pdf')}")
    print(f"   Google Docs: {sum(1 for a in archivos_a_procesar if 'document' in a['mimeType'])}")
    
    resultados = []
    
    for i, archivo in enumerate(archivos_a_procesar, 1):
        print(f"\n{'='*80}")
        print(f"📄 [{i}/{len(archivos_a_procesar)}] Procesando: {archivo['name']}")
        print(f"   Ruta: {archivo.get('ruta', 'N/A')}")
        print(f"   ID: {archivo['id']}")
        
        try:
            texto = extraer_texto_de_archivo(
                archivo['id'], 
                archivo['mimeType']
            )
            
            if texto:
                # Calcular estadísticas
                num_caracteres = len(texto)
                num_palabras = len(texto.split())
                
                print(f"✅ Texto extraído: {num_caracteres} caracteres, {num_palabras} palabras")
                
                resultado = {
                    'file_id': archivo['id'],
                    'nombre': archivo['name'],
                    'ruta': archivo.get('ruta', ''),
                    'mime_type': archivo['mimeType'],
                    'texto': texto,
                    'num_caracteres': num_caracteres,
                    'num_palabras': num_palabras
                }
                
                resultados.append(resultado)
            else:
                print(f"⚠️ No se pudo extraer texto")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    print(f"\n{'='*80}")
    print(f"✅ Procesamiento completado")
    print(f"   Exitosos: {len(resultados)}/{len(archivos_a_procesar)}")
    
    return resultados

def guardar_textos_extraidos(resultados, nombre_archivo="textos_extraidos.json"):
    """
    Guarda todos los textos extraídos en un archivo JSON
    
    Args:
        resultados (List[Dict]): Lista con textos extraídos
        nombre_archivo (str): Nombre del archivo de salida
    """
    print(f"\n💾 Guardando textos extraídos en: {nombre_archivo}")
    
    with open(nombre_archivo, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    # Calcular tamaño del archivo
    tamaño_mb = os.path.getsize(nombre_archivo) / (1024 * 1024)
    
    print(f"✅ Archivo guardado: {tamaño_mb:.2f} MB")
    
    # Resumen
    total_caracteres = sum(r['num_caracteres'] for r in resultados)
    total_palabras = sum(r['num_palabras'] for r in resultados)
    
    print(f"\n📊 RESUMEN:")
    print(f"   Total documentos: {len(resultados)}")
    print(f"   Total caracteres: {total_caracteres:,}")
    print(f"   Total palabras: {total_palabras:,}")

def get_drive_structure_and_extract_text(extracted_texts_path="textos_drive_extraidos.json", drive_structure="estructura_second_brain.json", second_brain_folder_id="1ciaGOxXKcLMNeuIa9103ivxYgBon__7q"):
    
    todos_archivos = obtener_todos_los_archivos_recursivamente(second_brain_folder_id)

    print("\n" + "=" * 80)
    print(f"✅ TOTAL ARCHIVOS ENCONTRADOS: {len(todos_archivos)}")
    print("=" * 80)

    todos_los_ids = [archivo['id'] for archivo in todos_archivos]
    
    print("\n📋 Lista de IDs:")
    for i, file_id in enumerate(todos_los_ids, 1):
        print(f"{i}. {file_id}")
    
    print("\n" + "=" * 80)
    print("GUARDANDO ESTRUCTURA COMPLETA")
    print("=" * 80)
    
    archivos_con_rutas = guardar_estructura_en_json(
        second_brain_folder_id,
        drive_structure
    )

    print("\n📊 RESUMEN:")
    print(f"Total archivos: {len(archivos_con_rutas)}")

    tipos = {}
    for archivo in archivos_con_rutas:
        tipo = archivo.get('mimeType', 'unknown')
        tipos[tipo] = tipos.get(tipo, 0) + 1
    
    print("\n📈 Por tipo de archivo:")
    for tipo, cantidad in tipos.items():
        tipo_legible = tipo.split('.')[-1] if '.' in tipo else tipo
        print(f"  {tipo_legible}: {cantidad}")

    print("Se ha concluido con el proceso de obtener toda la estructura del Drive del 2nd Brain.")

    print("\n" + "=" * 80)
    print("EXTRACCIÓN DE TEXTO DE DOCUMENTOS")
    print("=" * 80)
    
    resultados = procesar_todos_los_documentos(drive_structure)
    
    # Paso 2: Guardar resultados
    guardar_textos_extraidos(resultados, extracted_texts_path)
    
    # Paso 3: Ver muestra del primer documento
    if resultados:
        print("\n" + "=" * 80)
        print("MUESTRA DEL PRIMER DOCUMENTO")
        print("=" * 80)
        
        primer_doc = resultados[0]
        print(f"📄 Archivo: {primer_doc['nombre']}")
        print(f"📍 Ruta: {primer_doc['ruta']}")
        print(f"\n--- Texto (primeros 500 caracteres) ---")
        print(primer_doc['texto'][:500])
        print("...")

if __name__ == "__main__":

    # ============================================================================
    # EL FLUJO COMPLETO VA A SER QUE SE DEBE DE GENERAR LA ESTRUCTURA DEL DRIVE , DESPUES
    # SE DEBE DE OBTENER TODA LA INFORMACION DE CADA DOCUMENTO , ESTO ES LO QUE SE DEBERA DE COMPARTIR AL AGENTE 
    # YO CREO QUE LO VOY A GENERAR EN UN TXT LOS NOMBRES DE CADA ARCHIVO Y QUE HAYA UN LLM CLASIFICADOR 
    # QUE PUEDA BUSCAR Y DEVOLVER HASTA TRES DE CONTEXTO AL AGENTE
    # ============================================================================

    # second_brain_folder_id = "1ciaGOxXKcLMNeuIa9103ivxYgBon__7q"
    chat_gpt_business_folder_id = "1M0TmERmETfEM8flmzwGgfKC7IkrVZaoD"

    get_drive_structure_and_extract_text(second_brain_folder_id=chat_gpt_business_folder_id)

    # subir_archivo_a_drive(
    #     ruta_archivo_local="brochure_area_25.pdf",
    #     # nombre_carpeta="Second Brain", 
    #     folder_id=second_brain_folder_id
    # )
    # listar_archivos_en_carpeta(folder_id=chat_gpt_business_folder_id)

    # TODOS LOS PROCESOS ANTERIORES ANTES DE GENERAR LA FUNCION COMPLETA 
    # la funcion maestra debe de buscar el drive y generar toda la estructura del second brain , 
    # luego guardarla en un json , despues de eso , se debe de hacer toda la extraccion de documentos 
    # y se debe de generar otro json con los textos extraidos de cada documento., pensar si lo meto en qdrant o que 
    # se haga busqueda directa de textos con un clasificador 

    # proceso para poder leer los archivos y extraer texto
    # print("\n" + "=" * 80)
    # print("EXTRACCIÓN DE TEXTO DE DOCUMENTOS")
    # print("=" * 80)
    
    # # Paso 1: Procesar todos los documentos
    # resultados = procesar_todos_los_documentos("estructura_second_brain.json")
    
    # # Paso 2: Guardar resultados
    # guardar_textos_extraidos(resultados, "textos_drive_extraidos.json")
    
    # # Paso 3: Ver muestra del primer documento
    # if resultados:
    #     print("\n" + "=" * 80)
    #     print("MUESTRA DEL PRIMER DOCUMENTO")
    #     print("=" * 80)
        
    #     primer_doc = resultados[0]
    #     print(f"📄 Archivo: {primer_doc['nombre']}")
    #     print(f"📍 Ruta: {primer_doc['ruta']}")
    #     print(f"\n--- Texto (primeros 500 caracteres) ---")
    #     print(primer_doc['texto'][:500])
    #     print("...")

    # proceso para obtener la estructura completa y guardarla en JSON
    # second_brain_folder_id = "1ciaGOxXKcLMNeuIa9103ivxYgBon__7q"
    
    # # Opción 1: Solo obtener todos los IDs
    # print("\n" + "=" * 80)
    # print("OBTENIENDO TODOS LOS ARCHIVOS RECURSIVAMENTE")
    # print("=" * 80)
    
    # todos_archivos = obtener_todos_los_archivos_recursivamente(second_brain_folder_id)
    
    # print("\n" + "=" * 80)
    # print(f"✅ TOTAL ARCHIVOS ENCONTRADOS: {len(todos_archivos)}")
    # print("=" * 80)
    
    # # Extraer solo los IDs
    # todos_los_ids = [archivo['id'] for archivo in todos_archivos]
    
    # print("\n📋 Lista de IDs:")
    # for i, file_id in enumerate(todos_los_ids, 1):
    #     print(f"{i}. {file_id}")
    
    # # Opción 2: Con rutas completas y guardar en JSON
    # print("\n" + "=" * 80)
    # print("GUARDANDO ESTRUCTURA COMPLETA")
    # print("=" * 80)
    
    # archivos_con_rutas = guardar_estructura_en_json(
    #     second_brain_folder_id,
    #     "estructura_second_brain.json"
    # )
    
    # # Ver resumen
    # print("\n📊 RESUMEN:")
    # print(f"Total archivos: {len(archivos_con_rutas)}")
    
    # # Contar por tipo
    # tipos = {}
    # for archivo in archivos_con_rutas:
    #     tipo = archivo.get('mimeType', 'unknown')
    #     tipos[tipo] = tipos.get(tipo, 0) + 1
    
    # print("\n📈 Por tipo de archivo:")
    # for tipo, cantidad in tipos.items():
    #     tipo_legible = tipo.split('.')[-1] if '.' in tipo else tipo
    #     print(f"  {tipo_legible}: {cantidad}")


    # print("\n" + "=" * 80)
    # print("GOOGLE DRIVE - PRUEBAS")
    # print("=" * 80)
    # second_brain_folder_id = "1ciaGOxXKcLMNeuIa9103ivxYgBon__7q"

    # archivos_iniciales_dentro_de_secondbrain = [
    #     '1Dt98_kXg7WIJ-yIC0--eN45r4TlFHjtB', # rolplay 360 area comercial
    #     '1K5jXyfqa4hyC-FyYDnPRl6O_6MzhW9yGC5X6ib5UJsw', # sanfer visitas
    #     '1M0TmERmETfEM8flmzwGgfKC7IkrVZaoD' # chat gpt business folder
    # ]

    # ans = obtener_servicio()
    # print(ans)

    # subir_archivo_a_drive(
    #     ruta_archivo_local="Monti.pdf",
    #     nombre_carpeta="Second Brain", 
    #     folder_id="1qbIIlN6Vi4a33fZFQrUClM0JjYz06Mz2"
    # )
    # listar_archivos_en_carpeta(folder_id=archivos_iniciales_dentro_de_secondbrain[2])
    
    # Prueba 1: Listar todas las carpetas
    # print("\n🧪 PRUEBA 1: Listar todas las carpetas")
    # carpetas = listar_carpetas_limitadas()
    # breakpoint()
    
    # # Prueba 2: Buscar una carpeta específica
    # print("\n🧪 PRUEBA 2: Buscar carpeta 'Documentos'")
    # # carpetas_docs = buscar_carpeta_por_nombre("Second Brain")
    # carpetas = buscar_carpetas_drive(nombre_carpeta="Second Brain")
    # breakpoint()
    
    # Prueba 3: Listar archivos en una carpeta
    # if carpetas:
    #     print("\n🧪 PRUEBA 3: Listar archivos en la primera carpeta")
    #     archivos = listar_archivos_en_carpeta(folder_id=carpetas[1]['id'])
    #     breakpoint()
    
    # print("\n" + "=" * 80)
    # print("✅ Pruebas completadas")
    # print("=" * 80)

