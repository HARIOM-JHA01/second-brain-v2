# python3 app.py

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from procesa_mensajes import procesar_mensajes_entrantes
from typing import Optional

import os
import redis
import uvicorn

load_dotenv()

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")

# app.py - AGREGAR AL INICIO (después de los imports y antes de crear la app)

from fastapi import FastAPI, Request, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google_auth_oauthlib.flow import Flow
import os
import uvicorn

# 🔥 AGREGAR ESTA VARIABLE GLOBAL
oauth_states = {}

# Variable global para SCOPES
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly"
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

r = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username="default",
    password=redis_password,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.api_route('/', methods=['GET', 'HEAD'])
def index():
    '''Route de bienvenida'''
    return 'La API del Agente con Twilio funciona correctamente.'

from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import Response
from procesa_mensajes import procesar_mensajes_entrantes

@app.post('/api/v1/webhook')
async def webhook_post(request: Request):
    """
    Recibe mensajes de Twilio WhatsApp
    """
    try:
        # Obtener form data (NO JSON)
        form_data = await request.form()
        mensaje_data = dict(form_data)
        
        print("📥 POST recibido de Twilio:", mensaje_data)
        
        # Procesar el mensaje
        procesar_mensajes_entrantes(mensaje_data)
        
        return Response(content="", status_code=200)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return Response(content="", status_code=200)

@app.post('/api/v1/webhook/status')
async def webhook_status(request: Request):
    """
    Endpoint opcional para recibir actualizaciones de estado de mensajes enviados
    """
    try:
        form_data = await request.form()
        status_data = dict(form_data)
        print("Status callback recibido:", status_data)
        
        # Aquí puedes procesar los estados: sent, delivered, failed, etc.
        
        return Response(content="", status_code=200, media_type="text/xml")
    except Exception as e:
        print(f"Error procesando status: {e}")
        return Response(content="", status_code=200, media_type="text/xml")

@app.get('/health')
def health_check():
    """Endpoint para verificar que la API está funcionando"""
    return JSONResponse(content={"status": "healthy", "service": "twilio-whatsapp-api"})

# app.py - AGREGAR ESTOS IMPORTS
from google_auth_oauthlib.flow import Flow
import json

# AGREGAR ESTA VARIABLE GLOBAL
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly"
]

@app.get('/api/v1/drive/auth')
def generar_link_autorizacion():
    """
    Genera el link de autorización para Google Drive
    """
    try:
        CREDENTIALS_PATH = "DRIVE_CREDENTIALS.json"
        
        if not os.path.exists(CREDENTIALS_PATH):
            return JSONResponse(
                content={"error": "No existe credentials.json"},
                status_code=400
            )
        
        # Crear flow con redirect a tu ngrok
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri='https://f9338d3448db.ngrok-free.app/api/v1/drive/callback'
        )
        
        # Generar URL de autorización
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return JSONResponse(content={
            "authorization_url": authorization_url,
            "state": state,
            "instructions": "Abre este link en tu navegador, autoriza la app y serás redirigido automáticamente"
        })
        
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.get('/api/v1/drive/callback')
async def callback_autorizacion(request: Request):
    """
    Recibe el callback de Google después de autorizar
    """
    try:
        # Obtener el código de la URL
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')
        
        # Si el usuario canceló o hubo error
        if error:
            return JSONResponse(
                content={
                    "error": f"Autorización cancelada o error: {error}",
                    "message": "El usuario no autorizó la aplicación"
                },
                status_code=400
            )
        
        if not code:
            return JSONResponse(
                content={"error": "No se recibió código de autorización"},
                status_code=400
            )
        
        # 🔥 SIN VALIDACIÓN DE STATE (para simplificar)
        
        CREDENTIALS_PATH = "DRIVE_CREDENTIALS.json"
        
        # Crear flow
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri='https://f9338d3448db.ngrok-free.app/api/v1/drive/callback'
        )
        
        # Intercambiar código por token
        print(f"🔄 Intercambiando código por token...")
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Guardar token en archivo
        TOKENS_PATH = "token.json"
        with open(TOKENS_PATH, "w") as token:
            token.write(creds.to_json())
        
        print(f"✅ Token guardado en: {TOKENS_PATH}")
        
        return JSONResponse(content={
            "success": True,
            "message": "✅ Token generado exitosamente! Ya puedes usar Google Drive",
            "token_saved": TOKENS_PATH,
            "next_steps": "Verifica que existe el archivo token.json en tu servidor"
        })
        
    except Exception as e:
        print(f"❌ Error en callback: {e}")
        return JSONResponse(
            content={
                "error": str(e),
                "message": "Hubo un error al procesar la autorización"
            },
            status_code=500
        )

@app.get('/api/v1/drive/status')
def verificar_token():
    """
    Verifica si existe un token válido
    """
    TOKENS_PATH = "token.json"
    
    if os.path.exists(TOKENS_PATH):
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(TOKENS_PATH, SCOPES)
            
            if creds and creds.valid:
                return JSONResponse(content={
                    "status": "valid",
                    "message": "✅ Token válido y listo para usar",
                    "file": TOKENS_PATH
                })
            elif creds and creds.expired:
                return JSONResponse(content={
                    "status": "expired",
                    "message": "⚠️ Token expirado, necesita refrescarse",
                    "file": TOKENS_PATH
                })
            else:
                return JSONResponse(content={
                    "status": "invalid",
                    "message": "❌ Token inválido",
                    "file": TOKENS_PATH
                })
        except Exception as e:
            return JSONResponse(content={
                "status": "error",
                "message": f"❌ Error leyendo token: {str(e)}"
            })
    else:
        return JSONResponse(content={
            "status": "not_found",
            "message": "❌ No existe token.json. Necesitas autorizar primero."
        })

from fastapi.responses import HTMLResponse

@app.get('/privacy', response_class=HTMLResponse)
def privacy_policy():
    """
    Privacy Policy para OpenAI GPT
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Privacy Policy - Second Brain API</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                line-height: 1.6;
            }
            h1 { color: #333; }
            h2 { color: #666; margin-top: 30px; }
        </style>
    </head>
    <body>
        <h1>Privacy Policy</h1>
        <p><strong>Last updated:</strong> November 25, 2024</p>
        
        <h2>Information We Collect</h2>
        <p>Our API processes:</p>
        <ul>
            <li>Text queries and search requests</li>
            <li>Document metadata (file names, IDs)</li>
            <li>Temporary conversation context</li>
        </ul>
        
        <h2>How We Use Information</h2>
        <p>We use the information to:</p>
        <ul>
            <li>Provide document search and retrieval services</li>
            <li>Maintain API functionality</li>
            <li>Ensure service security</li>
        </ul>
        
        <h2>Data Storage</h2>
        <p>Data is stored securely using:</p>
        <ul>
            <li>Encrypted vector databases</li>
            <li>Secure cloud storage (Google Drive)</li>
            <li>Temporary caching with automatic expiration</li>
        </ul>
        
        <h2>Data Sharing</h2>
        <p>We do not share your data with third parties except as required by our service providers (Google Drive, database hosting) and when required by law.</p>
        
        <h2>Data Retention</h2>
        <p>Temporary data is automatically deleted. Stored documents remain until manually removed.</p>
        
        <h2>Your Rights</h2>
        <p>You have the right to:</p>
        <ul>
            <li>Access your data</li>
            <li>Request data deletion</li>
            <li>Receive information about data processing</li>
        </ul>
        
        <h2>Contact</h2>
        <p>For privacy concerns or data requests, contact: <a href="mailto:alejandro@entropia.ai">alejandro@entropia.ai</a></p>
        
        <h2>Changes to This Policy</h2>
        <p>We may update this policy from time to time. The "Last updated" date will reflect any changes.</p>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)