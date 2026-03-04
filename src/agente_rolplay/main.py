# python3 main.py

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, HTMLResponse
from google_auth_oauthlib.flow import Flow
from src.agente_rolplay.process_messages import procesar_mensajes_entrantes
from src.agente_rolplay.cli_tools import get_text_by_relevance, anthropic_completion
from src.agente_rolplay.system_prompt import system_prompt_rag

import os
import redis
import uvicorn

load_dotenv()

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")

oauth_states = {}

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
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


@app.api_route("/", methods=["GET", "HEAD"])
def index():
    """Welcome route"""
    return "La API del Agente con Twilio funciona correctamente."


@app.post("/api/v1/webhook")
async def webhook_post(request: Request):
    """
    Receives messages from Twilio WhatsApp
    """
    try:
        form_data = await request.form()
        mensaje_data = dict(form_data)

        print("POST received from Twilio:", mensaje_data)

        procesar_mensajes_entrantes(mensaje_data)

        return Response(content="", status_code=200)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return Response(content="", status_code=200)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return Response(content="", status_code=200)


@app.post("/api/v1/webhook/status")
async def webhook_status(request: Request):
    """
    Optional endpoint to receive status updates for sent messages
    """
    try:
        form_data = await request.form()
        status_data = dict(form_data)
        print("Status callback received:", status_data)

        # Here you can process the statuses: sent, delivered, failed, etc.

        return Response(content="", status_code=200, media_type="text/xml")
    except Exception as e:
        print(f"Error processing status: {e}")
        return Response(content="", status_code=200, media_type="text/xml")


@app.get("/health")
def health_check():
    """Endpoint to verify the API is working"""
    return JSONResponse(content={"status": "healthy", "service": "twilio-whatsapp-api"})


# app.py - ADD THESE IMPORTS

# ADD THIS GLOBAL VARIABLE
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
]


@app.get("/api/v1/drive/auth")
def generar_link_autorizacion():
    """
    Generates the authorization link for Google Drive
    """
    try:
        CREDENTIALS_PATH = "DRIVE_CREDENTIALS.json"

        if not os.path.exists(CREDENTIALS_PATH):
            return JSONResponse(
                content={"error": "No existe credentials.json"}, status_code=400
            )

        # Create flow with redirect to your ngrok
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri="https://f9338d3448db.ngrok-free.app/api/v1/drive/callback",
        )

        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true"
        )

        return JSONResponse(
            content={
                "authorization_url": authorization_url,
                "state": state,
                "instructions": "Open this link in your browser, authorize the app and you will be redirected automatically",
            }
        )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/v1/drive/callback")
async def callback_autorizacion(request: Request):
    """
    Receives the callback from Google after authorization
    """
    try:
        # Get the code from URL
        code = request.query_params.get("code")
        _state = request.query_params.get("state")
        error = request.query_params.get("error")

        # If user cancelled or there was an error
        if error:
            return JSONResponse(
                content={
                    "error": f"Authorization cancelled or error: {error}",
                    "message": "El usuario no autorizó la aplicación",
                },
                status_code=400,
            )

        if not code:
            return JSONResponse(
                content={"error": "No se recibió código de autorización"},
                status_code=400,
            )

        # NO STATE VALIDATION (to simplify)

        CREDENTIALS_PATH = "DRIVE_CREDENTIALS.json"

        # Create flow
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH,
            scopes=SCOPES,
            redirect_uri="https://f9338d3448db.ngrok-free.app/api/v1/drive/callback",
        )

        # Exchange code for token
        print("Exchanging code for token...")
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Save token to file
        TOKENS_PATH = "token.json"
        with open(TOKENS_PATH, "w") as token:
            token.write(creds.to_json())

        print(f"Token saved to: {TOKENS_PATH}")

        return JSONResponse(
            content={
                "success": True,
                "message": "Token generated successfully! You can now use Google Drive",
                "token_saved": TOKENS_PATH,
                "next_steps": "Verify that token.json exists on your server",
            }
        )

    except Exception as e:
        print(f"Error in callback: {e}")
        return JSONResponse(
            content={
                "error": str(e),
                "message": "There was an error processing the authorization",
            },
            status_code=500,
        )


@app.get("/api/v1/drive/status")
def verificar_token():
    """
    Verifies if a valid token exists
    """
    TOKENS_PATH = "token.json"

    if os.path.exists(TOKENS_PATH):
        try:
            from google.oauth2.credentials import Credentials

            creds = Credentials.from_authorized_user_file(TOKENS_PATH, SCOPES)

            if creds and creds.valid:
                return JSONResponse(
                    content={
                        "status": "valid",
                        "message": "Token valid and ready to use",
                        "file": TOKENS_PATH,
                    }
                )
            elif creds and creds.expired:
                return JSONResponse(
                    content={
                        "status": "expired",
                        "message": "Token expired, needs refresh",
                        "file": TOKENS_PATH,
                    }
                )
            else:
                return JSONResponse(
                    content={
                        "status": "invalid",
                        "message": "Token invalid",
                        "file": TOKENS_PATH,
                    }
                )
        except Exception as e:
            return JSONResponse(
                content={"status": "error", "message": f"Error reading token: {str(e)}"}
            )
    else:
        return JSONResponse(
            content={
                "status": "not_found",
                "message": "No token.json found. You need to authorize first.",
            }
        )


@app.get("/privacy", response_class=HTMLResponse)
def privacy_policy():
    """
    Privacy Policy for OpenAI GPT
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


API_KEY = os.getenv("GPT_ACTIONS_API_KEY")


@app.post("/api/v1/rag/query")
async def rag_query(request: Request, authorization: str = Header(None)):
    # Bearer auth for GPT
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    pregunta = body.get("question", "")

    if not pregunta:
        return JSONResponse({"error": "Falta 'question'"}, status_code=400)

    ans = (
        anthropic_completion(
            system_prompt=system_prompt_rag,
            messages=[{"role": "user", "content": pregunta}],
        )
        .content[0]
        .text.strip()
    )
    print(f"LLM response for query: {ans}")

    contexto = get_text_by_relevance(ans)

    return JSONResponse(
        {
            "answer": contexto  # or if you want, you can format more here
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
