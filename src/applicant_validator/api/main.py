"""FastAPI application entry point."""

import contextlib
from collections.abc import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from applicant_validator.api.routes.admin import router as admin_router
from applicant_validator.api.routes.applicants import router as applicants_router
from applicant_validator.api.routes.auth import router as auth_router
from applicant_validator.api.routes.revalidate import router as revalidate_router
from applicant_validator.api.routes.rules import router as rules_router
from applicant_validator.api.routes.settings import router as settings_router
from applicant_validator.api.routes.sync import router as sync_router
from applicant_validator.api.routes.users import router as users_router
from applicant_validator.api.routes.validation_data import router as validation_data_router
from applicant_validator.config import get_settings
from applicant_validator.database import get_session
from applicant_validator.services.auth_settings import (
    ensure_auth_settings,
    get_auth_settings_cache,
)

logger = structlog.get_logger()
settings = get_settings()


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler - runs on startup/shutdown."""
    # Startup: Load auth settings from database
    logger.info("Loading auth settings from database...")
    async with get_session() as session:
        # Ensure default settings exist and load cache
        await ensure_auth_settings(session)
        await session.commit()

        # Load settings into cache
        cache = get_auth_settings_cache()
        await cache.load(session)

    logger.info("Auth settings loaded successfully")

    yield

    # Shutdown: Nothing to clean up


app = FastAPI(
    title="Applicant Validator API",
    description="API for validating job applicants and detecting fraud",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin_router, prefix="/api")
app.include_router(applicants_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(revalidate_router, prefix="/api")
app.include_router(rules_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(validation_data_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


def run() -> None:
    """Run the API server."""
    uvicorn.run(
        "applicant_validator.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_debug,
    )


if __name__ == "__main__":
    run()
