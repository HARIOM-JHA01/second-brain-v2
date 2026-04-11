# python3 main.py

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from agente_rolplay.config import PORT, SECRET_KEY
from agente_rolplay.routers import admin, auth, pages, rag, roles, users, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    from agente_rolplay.db.database import init_db
    from agente_rolplay.banco_poller import start_poller

    init_db()
    start_poller()
    yield


app = FastAPI(lifespan=lifespan)

REACT_DIST_DIR = "agente_rolplay/static/react"


def get_react_file_path(path: str) -> str:
    file_path = os.path.join(REACT_DIST_DIR, path)
    if os.path.isfile(file_path):
        return file_path
    index_html = os.path.join(REACT_DIST_DIR, "index.html")
    if os.path.isfile(index_html):
        return index_html
    return None


@app.get("/app/{path:path}")
async def serve_react_app(path: str):
    file_path = get_react_file_path(path)
    if file_path:
        return FileResponse(file_path)
    index_path = os.path.join(REACT_DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/app")
async def serve_react_app_root():
    index_path = os.path.join(REACT_DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="React app not found")


app.mount("/static", StaticFiles(directory="agente_rolplay/static"), name="static")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(rag.router)
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(users.scenarios_router)
app.include_router(roles.router)
app.include_router(admin.router)


@app.get("/health")
def health_check():
    return JSONResponse(
        content={"status": "healthy", "service": "second brain api is live"}
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=True)
