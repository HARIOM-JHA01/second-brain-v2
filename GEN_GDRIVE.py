# import datetime
# import io
# import json
# import os
# from dotenv import load_dotenv
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# from googleapiclient.http import MediaIoBaseDownload
# from dotenv import load_dotenv
# from typing import List, Dict
# from qdrant_client import QdrantClient
# from qdrant_client.http import models
# from openai import OpenAI

# load_dotenv()

# qdrant_host = os.getenv("QDRANT_URL", "")
# qdrant_api_key = os.getenv("QDRANT_API_KEY", "")

# openai_embeddings_model = os.getenv("OPENAI_EMBEDDINGS_MODEL", "")
# openai_api_key = os.getenv("OPENAI_API_KEY", "")

# client = OpenAI(api_key=openai_api_key)

# load_dotenv()

# DRIVE_CREDENTIALS =  os.getenv("DRIVE_CREDENTIALS", "DRIVE_CREDENTIALS.json")
# DRIVE_TOKENS = os.getenv("DRIVE_TOKENS", "DRIVE_TOKENS.json")

# # def obtener_servicio():
# #     creds = None
# #     SCOPES = [
# #         "https://www.googleapis.com/auth/spreadsheets",
# #         "https://www.googleapis.com/auth/drive"
# #     ]
# #     CREDENTIALS_PATH = os.path.join(
# #         os.path.dirname(__file__), DRIVE_CREDENTIALS
# #     )
# #     TOKENS_PATH = os.path.join(
# #         os.path.dirname(__file__), DRIVE_TOKENS
# #     )

# #     if os.path.exists(TOKENS_PATH):
# #         creds = Credentials.from_authorized_user_file(
# #             TOKENS_PATH, SCOPES
# #         )

# #     if not creds or not creds.valid:
# #         if creds and creds.expired and creds.refresh_token:
# #             creds.refresh(Request())
# #         else:
# #             flow = InstalledAppFlow.from_client_secrets_file(
# #                 CREDENTIALS_PATH, SCOPES
# #             )
# #             creds = flow.run_local_server(port=8080)
# #             # creds = flow.run_console()

# #         with open(TOKENS_PATH, "w") as token:
# #             token.write(creds.to_json())

# #     try:
# #         return build("sheets", "v4", credentials=creds)

# #     except HttpError as error:
# #         print(f"An error occurred: {error}")
# #         return None

# # def get_spreadsheet_id(nombre_archivo, servicio_sheets=obtener_servicio()):
# #     servicio_drive = build("drive", "v3", credentials=servicio_sheets._http.credentials)
# #     query = f"name = '{nombre_archivo}' and mimeType = 'application/vnd.google-apps.spreadsheet'"
# #     resultados = servicio_drive.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
# #     archivos = resultados.get("files", [])

# #     if archivos:
# #         return archivos[0]["id"]

# #     else:
# #         return None 

# # def leer_propiedades_excel_completo(spreadsheet_id, hoja, path_salida, servicio_sheets=obtener_servicio()):

# #     try:
# #         rango = f"{hoja}!A:Z"
# #         resultado = servicio_sheets.spreadsheets().values().get(
# #             spreadsheetId=spreadsheet_id,
# #             range=rango
# #         ).execute()

# #         valores = resultado.get("values", [])
# #         if not valores:
# #             print("No se encontraron datos en la hoja")
# #             return pd.DataFrame()

# #         headers = valores[0]
# #         data_rows = valores[1:] if len(valores) > 1 else []

# #         max_cols = len(headers)
# #         for i, row in enumerate(data_rows):
# #             if len(row) < max_cols:
# #                 data_rows[i].extend([''] * (max_cols - len(row)))

# #         df = pd.DataFrame(data_rows, columns=headers)
# #         df.columns = df.columns.str.strip()

# #         columnas_esperadas = [
# #             'id',
# #             'desarrollo',
# #             'tipo',
# #             'recamaras', 
# #             'baños',
# #             'precio',
# #             'zona',
# #             'caracteristicas_propiedad',
# #             'amenidades_desarrollo',
# #             'ubicacion_exacta',
# #             'referencias_cercanas'
# #         ]

# #         columnas_presentes = [col for col in columnas_esperadas if col in df.columns]
# #         columnas_faltantes = [col for col in columnas_esperadas if col not in df.columns]

# #         if columnas_faltantes:
# #             print(f"⚠️  Columnas faltantes: {columnas_faltantes}")
        
# #         print(f"✅ Columnas encontradas: {columnas_presentes}")
# #         print(f"📊 Total de propiedades: {len(df)}")

# #         df = df.fillna('')
# #         df.to_excel(path_salida)

# #         print(f"✅ Datos guardados en {path_salida}")
# #         return df

# #     except Exception as e:
# #         print(f"❌ Error al leer el Excel: {str(e)}")
# #         return pd.DataFrame()


# # obtener_servicio()

# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# from google.auth.transport.requests import Request
# import os

# # DRIVE_CREDENTIALS = "credentials.json"
# # DRIVE_TOKENS = "token.json"

# def obtener_servicio(tipo_servicio="drive"):
#     """
#     Obtiene el servicio de Google (Sheets o Drive)
#     tipo_servicio: 'sheets' o 'drive'
#     """
#     creds = None
#     SCOPES = [
#         # "https://www.googleapis.com/auth/spreadsheets",
#         "https://www.googleapis.com/auth/drive",
#         "https://www.googleapis.com/auth/drive.file",
#         "https://www.googleapis.com/auth/drive.readonly"
#     ]
    
#     CREDENTIALS_PATH = os.path.join(
#         os.path.dirname(__file__), DRIVE_CREDENTIALS
#     )
#     TOKENS_PATH = os.path.join(
#         os.path.dirname(__file__), DRIVE_TOKENS
#     )

#     # Si existe el token, cargarlo
#     if os.path.exists(TOKENS_PATH):
#         creds = Credentials.from_authorized_user_file(
#             TOKENS_PATH, SCOPES
#         )
#         print("✅ Token cargado desde archivo")

#     # Si no hay credenciales válidas
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             print("🔄 Token expirado, refrescando...")
#             creds.refresh(Request())
            
#             # Guardar el token actualizado
#             with open(TOKENS_PATH, "w") as token:
#                 token.write(creds.to_json())
#             print("✅ Token refrescado exitosamente")
#         else:
#             print("❌ No hay token válido. Ejecuta generar_token.py primero")
#             return None

#     try:
#         # Construir el servicio según lo solicitado
#         if tipo_servicio == "sheets":
#             service = build("sheets", "v4", credentials=creds)
#             print("✅ Servicio de Google Sheets obtenido")
#             return service
#         elif tipo_servicio == "drive":
#             service = build("drive", "v3", credentials=creds)
#             print("✅ Servicio de Google Drive obtenido")
#             return service
#         else:
#             print(f"❌ Tipo de servicio no reconocido: {tipo_servicio}")
#             return None

#     except HttpError as error:
#         print(f"❌ Error HTTP: {error}")
#         return None

# obtener_servicio()

# # from google.oauth2.credentials import Credentials
# # from google_auth_oauthlib.flow import InstalledAppFlow
# # from googleapiclient.discovery import build
# # from googleapiclient.errors import HttpError
# # from google.auth.transport.requests import Request
# # import os

# # # Nombre del archivo que descargaste
# # DRIVE_CREDENTIALS = os.getenv("DRIVE_CREDENTIALS", "DRIVE_CREDENTIALS.json")
# # # Nombre del token que se generará
# # DRIVE_TOKENS = os.getenv("DRIVE_TOKENS", "token.json")



# # este es el bueno 
# def generar_token_inicial():
#     """
#     Genera el token.json por primera vez usando credentials.json
#     Solo necesitas ejecutar esto UNA VEZ
#     """
#     SCOPES = [
#         # "https://www.googleapis.com/auth/spreadsheets",
#         "https://www.googleapis.com/auth/drive",
#         "https://www.googleapis.com/auth/drive.file",
#         "https://www.googleapis.com/auth/drive.readonly"
#     ]
    
#     CREDENTIALS_PATH = os.path.join(
#         os.path.dirname(__file__), DRIVE_CREDENTIALS
#     )
#     TOKENS_PATH = os.path.join(
#         os.path.dirname(__file__), DRIVE_TOKENS
#     )
    
#     if not os.path.exists(CREDENTIALS_PATH):
#         print(f"❌ ERROR: No existe el archivo {CREDENTIALS_PATH}")
#         print(f"Descarga el archivo de credenciales de Google Cloud Console")
#         return None
    
#     print("🔐 Iniciando proceso de autorización...")
#     print("Se abrirá tu navegador para autorizar la aplicación")
    
#     try:
#         flow = InstalledAppFlow.from_client_secrets_file(
#             CREDENTIALS_PATH, SCOPES
#         )
#         # Esto abre el navegador para autorizar
#         creds = flow.run_local_server(port=8080)
        
#         # Guardar el token generado
#         with open(TOKENS_PATH, "w") as token:
#             token.write(creds.to_json())
        
#         print(f"✅ Token generado exitosamente: {TOKENS_PATH}")
#         print("Ahora puedes usar obtener_servicio() normalmente")
#         return creds
        
#     except Exception as e:
#         print(f"❌ ERROR generando token: {e}")
#         return None

# def obtener_servicio(tipo_servicio="sheets"):
#     """
#     Obtiene el servicio de Google (Sheets o Drive)
#     tipo_servicio: 'sheets' o 'drive'
#     """
#     SCOPES = [
#         "https://www.googleapis.com/auth/spreadsheets",
#         "https://www.googleapis.com/auth/drive",
#         "https://www.googleapis.com/auth/drive.file",
#         "https://www.googleapis.com/auth/drive.readonly"
#     ]
    
#     CREDENTIALS_PATH = os.path.join(
#         os.path.dirname(__file__), DRIVE_CREDENTIALS
#     )
#     TOKENS_PATH = os.path.join(
#         os.path.dirname(__file__), DRIVE_TOKENS
#     )
    
#     creds = None
    
#     # Si existe el token, usarlo
#     if os.path.exists(TOKENS_PATH):
#         creds = Credentials.from_authorized_user_file(TOKENS_PATH, SCOPES)
    
#     # Si no hay credenciales válidas, generarlas
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             print("🔄 Token expirado, refrescando...")
#             creds.refresh(Request())
            
#             # Guardar token actualizado
#             with open(TOKENS_PATH, "w") as token:
#                 token.write(creds.to_json())
#             print("✅ Token refrescado")
#         else:
#             # Primera vez: generar token
#             print("⚠️ No existe token válido. Generando uno nuevo...")
#             if not os.path.exists(CREDENTIALS_PATH):
#                 print(f"❌ ERROR: No existe {CREDENTIALS_PATH}")
#                 return None
            
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 CREDENTIALS_PATH, SCOPES
#             )
#             creds = flow.run_local_server(port=8080)
            
#             with open(TOKENS_PATH, "w") as token:
#                 token.write(creds.to_json())
#             print("✅ Token generado exitosamente")
    
#     try:
#         if tipo_servicio == "sheets":
#             return build("sheets", "v4", credentials=creds)
#         elif tipo_servicio == "drive":
#             return build("drive", "v3", credentials=creds)
#         else:
#             print(f"❌ Tipo no reconocido: {tipo_servicio}")
#             return None
            
#     except HttpError as error:
#         print(f"❌ Error HTTP: {error}")
#         return None

# def listar_todos_los_archivos_drive():
#     """
#     Lista TODOS los archivos en tu Google Drive
#     """
#     service = obtener_servicio(tipo_servicio="drive")
    
#     if not service:
#         print("❌ No se pudo obtener el servicio de Drive")
#         return []
    
#     try:
#         print("🔍 Buscando archivos en Google Drive...")
        
#         results = service.files().list(
#             pageSize=100,  # Número de resultados por página
#             fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, webViewLink, parents)"
#         ).execute()
        
#         items = results.get('files', [])
        
#         if not items:
#             print('⚠️ No se encontraron archivos.')
#             return []
        
#         print(f'\n📂 Archivos encontrados: {len(items)}\n')
#         print("=" * 80)
        
#         for item in items:
#             print(f"📄 Nombre: {item['name']}")
#             print(f"   ID: {item['id']}")
#             print(f"   Tipo: {item['mimeType']}")
#             print(f"   Link: {item.get('webViewLink', 'N/A')}")
#             print(f"   Modificado: {item.get('modifiedTime', 'N/A')}")
#             if 'size' in item:
#                 size_mb = int(item['size']) / (1024 * 1024)
#                 print(f"   Tamaño: {size_mb:.2f} MB")
#             print("-" * 80)
        
#         return items
        
#     except HttpError as error:
#         print(f'❌ Error listando archivos: {error}')
#         return []

# def buscar_archivos_por_tipo(mime_type=None, nombre_contiene=None):
#     """
#     Busca archivos específicos en Drive
#     mime_type: 'application/pdf', 'application/vnd.google-apps.spreadsheet', etc.
#     nombre_contiene: texto que debe estar en el nombre
#     """
#     service = obtener_servicio(tipo_servicio="drive")
    
#     if not service:
#         return []
    
#     try:
#         # Construir query
#         query_parts = []
        
#         if mime_type:
#             query_parts.append(f"mimeType='{mime_type}'")
        
#         if nombre_contiene:
#             query_parts.append(f"name contains '{nombre_contiene}'")
        
#         query = " and ".join(query_parts) if query_parts else None
        
#         print(f"🔍 Buscando archivos con query: {query}")
        
#         results = service.files().list(
#             q=query,
#             pageSize=100,
#             fields="files(id, name, mimeType, webViewLink, modifiedTime)"
#         ).execute()
        
#         items = results.get('files', [])
        
#         print(f"✅ Encontrados: {len(items)} archivos")
        
#         for item in items:
#             print(f"\n📄 {item['name']}")
#             print(f"   ID: {item['id']}")
#             print(f"   Link: {item.get('webViewLink', 'N/A')}")
        
#         return items
        
#     except HttpError as error:
#         print(f'❌ Error: {error}')
#         return []

# # Script de prueba
# # if __name__ == "__main__":
# #     print("=" * 80)
# #     print("CONFIGURACIÓN DE GOOGLE DRIVE")
# #     print("=" * 80)
    
# #     # Opción 1: Generar token por primera vez (solo si no existe)
# #     # generar_token_inicial()
    
# #     # Opción 2: Listar todos los archivos
# #     archivos = listar_todos_los_archivos_drive()
    
#     # Opción 3: Buscar PDFs
#     # pdfs = buscar_archivos_por_tipo(mime_type='application/pdf')
    
#     # Opción 4: Buscar por nombre
#     # archivos = buscar_archivos_por_tipo(nombre_contiene='reporte')

# # from google_auth_oauthlib.flow import InstalledAppFlow
# # import os

# # SCOPES = [
# #     # "https://www.googleapis.com/auth/spreadsheets",
# #     "https://www.googleapis.com/auth/drive",
# #     "https://www.googleapis.com/auth/drive.file",
# #     "https://www.googleapis.com/auth/drive.readonly"
# # ]

# # # Crear el flow
# # flow = InstalledAppFlow.from_client_secrets_file(
# #     DRIVE_CREDENTIALS, 
# #     SCOPES,
# #     redirect_uri='urn:ietf:wg:oauth:2.0:oob'
# # )

# # # Generar URL de autorización
# # auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

# # print("=" * 80)
# # print("🔗 ENVÍA ESTE LINK A TU CLIENTE:")
# # print("=" * 80)
# # print(f"\n{auth_url}\n")
# # print("=" * 80)

# # # Esperar el código del cliente
# # codigo = input("\n📋 Pega aquí el código que te dio tu cliente: ").strip()

# # # Intercambiar código por token
# # flow.fetch_token(code=codigo)

# # # Guardar token
# # with open(DRIVE_TOKENS, "w") as token:
# #     token.write(flow.credentials.to_json())

# # print(f"\n✅ Token guardado en: {DRIVE_TOKENS}")
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly"
]

flow = InstalledAppFlow.from_client_secrets_file(
    "DRIVE_CREDENTIALS.json",  # El JSON que te dio tu cliente
    SCOPES,
    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
)

auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

print("Envía este link a tu cliente:")
print(auth_url)

codigo = input("Pega el código que te dio: ")

flow.fetch_token(code=codigo)

with open("token.json", "w") as token:
    token.write(flow.credentials.to_json())

print("✅ Token generado: token.json")