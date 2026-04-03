from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from api.routes.projects import router as projects_router
from api.routes.metrics import router as metrics_router
from api.routes.tasks import router as tasks_router
from api.routes.webhooks import router as webhooks_router
from api.routes.integrations import router as integrations_router
from api.routes.agents import router as agents_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from api.deps import get_firebase_app
    get_firebase_app()
    yield


app = FastAPI(
    title="Hapura Command Center API",
    description="Revenue War Room — central management for all Hapura products",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hapura-command", "version": "1.0.0"}
