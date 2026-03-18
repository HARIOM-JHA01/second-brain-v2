# python3 main.py

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from agente_rolplay.config import PORT, SECRET_KEY
from agente_rolplay.routers import admin, auth, pages, rag, roles, users, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    from agente_rolplay.db.database import init_db

    init_db()
    yield


app = FastAPI(lifespan=lifespan)

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
app.include_router(roles.router)
app.include_router(admin.router)


@app.get("/health")
def health_check():
    return JSONResponse(
        content={"status": "healthy", "service": "second brain api is live"}
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=True)
