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

# #         expected_columns = [
# #             'id',
# #             'development',
# #             'type',
# #             'bedrooms',
# #             'bathrooms',
# #             'price',
# #             'zone',
# #             'property_features',
# #             'development_amenities',
# #             'exact_location',
# #             'nearby_references'
# #         ]

# #         columnas_presentes = [col for col in columnas_esperadas if col in df.columns]
# #         columnas_faltantes = [col for col in columnas_esperadas if col not in df.columns]

# #         if columnas_faltantes:
# #             print(f"Warning: Missing columns: {columnas_faltantes}")

# #         print(f"Columns found: {columnas_presentes}")
# #         print(f"Total properties: {len(df)}")

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

#     # If token exists, load it
#     if os.path.exists(TOKENS_PATH):
#         creds = Credentials.from_authorized_user_file(
#             TOKENS_PATH, SCOPES
#         )
#         print("Token loaded from file")

#     # If no valid credentials
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             print("Token expired, refreshing...")
#             creds.refresh(Request())

#             # Save updated token
#             with open(TOKENS_PATH, "w") as token:
#                 token.write(creds.to_json())
#             print("Token refreshed successfully")
#         else:
#             print("No valid token. Run generar_token.py first")
#             return None

#     try:
#         # Build service as requested
#         if tipo_servicio == "sheets":
#             service = build("sheets", "v4", credentials=creds)
#             print("Google Sheets service obtained")
#             return service
#         elif tipo_servicio == "drive":
#             service = build("drive", "v3", credentials=creds)
#             print("Google Drive service obtained")
#             return service
#         else:
#             print(f"Unknown service type: {tipo_servicio}")
#             return None

#     except HttpError as error:
#         print(f"HTTP Error: {error}")
#         return None

# obtener_servicio()

# # from google.oauth2.credentials import Credentials
# # from google_auth_oauthlib.flow import InstalledAppFlow
# # from googleapiclient.discovery import build
# # from googleapiclient.errors import HttpError
# # from google.auth.transport.requests import Request
# # import os

# # # Name of the file you downloaded
# # DRIVE_CREDENTIALS = os.getenv("DRIVE_CREDENTIALS", "DRIVE_CREDENTIALS.json")
# # # Name of the token that will be generated
# # DRIVE_TOKENS = os.getenv("DRIVE_TOKENS", "token.json")


# # this is the working one
# def generar_token_inicial():
#     """
#     Generates token.json for the first time using credentials.json
#     Only need to run this ONCE
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
#         print(f"ERROR: File {CREDENTIALS_PATH} does not exist")
#         print(f"Download the credentials file from Google Cloud Console")
#         return None

#     print("Starting authorization process...")
#     print("Your browser will open to authorize the application")

#     try:
#         flow = InstalledAppFlow.from_client_secrets_file(
#             CREDENTIALS_PATH, SCOPES
#         )
#         # This opens browser to authorize
#         creds = flow.run_local_server(port=8080)

#         # Save generated token
#         with open(TOKENS_PATH, "w") as token:
#             token.write(creds.to_json())

#         print(f"Token generated successfully: {TOKENS_PATH}")
#         print("Now you can use obtener_servicio() normally")
#         return creds

#     except Exception as e:
#         print(f"ERROR generating token: {e}")
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

#     # If token exists, use it
#     if os.path.exists(TOKENS_PATH):
#         creds = Credentials.from_authorized_user_file(TOKENS_PATH, SCOPES)

#     # If no valid credentials, generate them
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             print("Token expired, refreshing...")
#             creds.refresh(Request())

#             # Save updated token
#             with open(TOKENS_PATH, "w") as token:
#                 token.write(creds.to_json())
#             print("Token refreshed")
#         else:
#             # First time: generate token
#             print("No valid token. Generating new one...")
#             if not os.path.exists(CREDENTIALS_PATH):
#                 print(f"ERROR: {CREDENTIALS_PATH} does not exist")
#                 return None

#             flow = InstalledAppFlow.from_client_secrets_file(
#                 CREDENTIALS_PATH, SCOPES
#             )
#             creds = flow.run_local_server(port=8080)

#             with open(TOKENS_PATH, "w") as token:
#                 token.write(creds.to_json())
#             print("Token generated successfully")

#     try:
#         if tipo_servicio == "sheets":
#             return build("sheets", "v4", credentials=creds)
#         elif tipo_servicio == "drive":
#             return build("drive", "v3", credentials=creds)
#         else:
#             print(f"Unknown type: {tipo_servicio}")
#             return None

#     except HttpError as error:
#         print(f"HTTP Error: {error}")
#         return None

# def listar_todos_los_archivos_drive():
#     """
#     List ALL files in your Google Drive
#     """
#     service = obtener_servicio(tipo_servicio="drive")

#     if not service:
#         print("Could not get Drive service")
#         return []

#     try:
#         print("Searching files in Google Drive...")

#         results = service.files().list(
#             pageSize=100,  # Number of results per page
#             fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, webViewLink, parents)"
#         ).execute()

#         items = results.get('files', [])

#         if not items:
#             print('No files found.')
#             return []

#         print(f'\nFiles found: {len(items)}\n')
#         print("=" * 80)

#         for item in items:
#             print(f"Name: {item['name']}")
#             print(f"   ID: {item['id']}")
#             print(f"   Type: {item['mimeType']}")
#             print(f"   Link: {item.get('webViewLink', 'N/A')}")
#             print(f"   Modified: {item.get('modifiedTime', 'N/A')}")
#             if 'size' in item:
#                 size_mb = int(item['size']) / (1024 * 1024)
#                 print(f"   Size: {size_mb:.2f} MB")
#             print("-" * 80)

#         return items

#     except HttpError as error:
#         print(f'Error listing files: {error}')
#         return []

# def buscar_archivos_por_tipo(mime_type=None, nombre_contiene=None):
#     """
#     Search for specific files in Drive
#     mime_type: 'application/pdf', 'application/vnd.google-apps.spreadsheet', etc.
#     nombre_contiene: text that should be in the name
#     """
#     service = obtener_servicio(tipo_servicio="drive")

#     if not service:
#         return []

#     try:
#         # Build query
#         query_parts = []

#         if mime_type:
#             query_parts.append(f"mimeType='{mime_type}'")

#         if nombre_contiene:
#             query_parts.append(f"name contains '{nombre_contiene}'")

#         query = " and ".join(query_parts) if query_parts else None

#         print(f"Searching files with query: {query}")

#         results = service.files().list(
#             q=query,
#             pageSize=100,
#             fields="files(id, name, mimeType, webViewLink, modifiedTime)"
#         ).execute()

#         items = results.get('files', [])

#         print(f"Found: {len(items)} files")

#         for item in items:
#             print(f"\n{item['name']}")
#             print(f"   ID: {item['id']}")
#             print(f"   Link: {item.get('webViewLink', 'N/A')}")

#         return items

#     except HttpError as error:
#         print(f'Error: {error}')
#         return []

# # Test script
# # if __name__ == "__main__":
# #     print("=" * 80)
# #     print("GOOGLE DRIVE CONFIGURATION")
# #     print("=" * 80)

# #     # Option 1: Generate token for first time (only if it doesn't exist)
# #     # generar_token_inicial()

# #     # Option 2: List all files
# #     archivos = listar_todos_los_archivos_drive()

#     # Option 3: Search PDFs
#     # pdfs = buscar_archivos_por_tipo(mime_type='application/pdf')

#     # Option 4: Search by name
#     # archivos = buscar_archivos_por_tipo(nombre_contiene='reporte')

# # from google_auth_oauthlib.flow import InstalledAppFlow
# # import os

# # SCOPES = [
# #     # "https://www.googleapis.com/auth/spreadsheets",
# #     "https://www.googleapis.com/auth/drive",
# #     "https://www.googleapis.com/auth/drive.file",
# #     "https://www.googleapis.com/auth/drive.readonly"
# # ]

# # # Create the flow
# # flow = InstalledAppFlow.from_client_secrets_file(
# #     DRIVE_CREDENTIALS,
# #     SCOPES,
# #     redirect_uri='urn:ietf:wg:oauth:2.0:oob'
# # )

# # # Generate authorization URL
# # auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

# # print("=" * 80)
# # print("SEND THIS LINK TO YOUR CLIENT:")
# # print("=" * 80)
# # print(f"\n{auth_url}\n")
# # print("=" * 80)

# # # Wait for client's code
# # code = input("\nPaste the code you received from your client: ").strip()

# # # Exchange code for token
# # flow.fetch_token(code=code)

# # # Save token
# # with open(DRIVE_TOKENS, "w") as token:
# #     token.write(flow.credentials.to_json())

# # print(f"\n✅ Token guardado en: {DRIVE_TOKENS}")
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
]

flow = InstalledAppFlow.from_client_secrets_file(
    "DRIVE_CREDENTIALS.json",  # El JSON que te dio tu cliente
    SCOPES,
    redirect_uri="urn:ietf:wg:oauth:2.0:oob",
)

auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

print("Send this link to your client:")
print(auth_url)

code = input("Paste the code you received: ")

flow.fetch_token(code=code)

with open("token.json", "w") as token:
    token.write(flow.credentials.to_json())

print("Token generated: token.json")
