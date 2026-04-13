from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory="agente_rolplay/templates")


@router.get("/privacy", response_class=HTMLResponse)
def privacy_policy():
    """Privacy Policy for OpenAI GPT"""
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


@router.get("/", tags=["pages"])
def home():
    return FileResponse("agente_rolplay/templates/index.html")


@router.get("/login", tags=["pages"])
def login_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request, "initial_mode": "login"})


@router.get("/signup", tags=["pages"])
def signup_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request, "initial_mode": "signup"})


def _require_auth(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login", status_code=302)
    return None


@router.get("/dashboard", tags=["pages"])
def dashboard_page(request: Request):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "page_title": "Dashboard"}
    )


@router.get("/dashboard/users", tags=["pages"])
def users_page(request: Request):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("users.html", {"request": request})


@router.get("/dashboard/documents", tags=["pages"])
def documents_page(request: Request):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("documents.html", {"request": request})


@router.get("/dashboard/chat", tags=["pages"])
def chat_page(request: Request):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("chat.html", {"request": request})


@router.get("/dashboard/settings", tags=["pages"])
def settings_page(request: Request):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("settings.html", {"request": request})


# ── Admin pages ───────────────────────────────────────────────────────────────

def _require_admin(request: Request):
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/admin/login", status_code=302)
    return None


@router.get("/admin/login", tags=["admin"])
def admin_login_page(request: Request):
    if request.session.get("is_admin"):
        return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse("admin_login.html", {"request": request})


@router.get("/admin", tags=["admin"])
def admin_dashboard_page(request: Request):
    redirect = _require_admin(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})


@router.get("/admin/organizations", tags=["admin"])
def admin_orgs_page(request: Request):
    redirect = _require_admin(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("admin_orgs.html", {"request": request})


@router.get("/admin/users", tags=["admin"])
def admin_users_page(request: Request):
    redirect = _require_admin(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("admin_users.html", {"request": request})


@router.get("/dashboard/scenarios", tags=["pages"])
def scenarios_page(request: Request):
    redirect = _require_auth(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("scenarios.html", {"request": request})


@router.get("/admin/scenarios", tags=["admin"])
def admin_scenarios_page(request: Request):
    redirect = _require_admin(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("admin_scenarios.html", {"request": request})


@router.get("/admin/settings", tags=["admin"])
def admin_settings_page(request: Request):
    redirect = _require_admin(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("admin_settings.html", {"request": request})
