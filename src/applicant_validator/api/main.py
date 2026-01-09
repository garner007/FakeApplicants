"""FastAPI application entry point."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from applicant_validator.api.routes.admin import router as admin_router
from applicant_validator.api.routes.applicants import router as applicants_router
from applicant_validator.api.routes.revalidate import router as revalidate_router
from applicant_validator.api.routes.rules import router as rules_router
from applicant_validator.api.routes.settings import router as settings_router
from applicant_validator.api.routes.sync import router as sync_router
from applicant_validator.api.routes.validation_data import router as validation_data_router
from applicant_validator.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Applicant Validator API",
    description="API for validating job applicants and detecting fraud",
    version="0.1.0",
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
app.include_router(revalidate_router, prefix="/api")
app.include_router(rules_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
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
