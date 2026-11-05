"""
VendorFlow API — application entry point.

Lifecycle:
    startup  → connect to MongoDB Atlas
    shutdown → close MongoDB connection

Middleware:
    CORS — allows the React dev server (localhost:5173) to call the API

Routes:
    GET  /           → root info
    GET  /health     → health check
    POST /api/test-db  → insert test document  (temporary)
    GET  /api/test-db  → retrieve test documents (temporary)
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env BEFORE importing any module that reads env vars
load_dotenv()

from src.database.mongodb import connect_to_mongodb, close_mongodb_connection  # noqa: E402
from src.routes.test import router as test_router  # noqa: E402
from src.routes.vendors import router as vendors_router  # noqa: E402
from src.routes.documents import router as documents_router  # noqa: E402
from src.services.vendor_service import VendorService  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan — connects / disconnects the database
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VendorFlow API starting up…")
    await connect_to_mongodb()
    try:
        VendorService().ensure_indexes()
        logger.info("Database indexes ensured.")
    except Exception as exc:
        logger.warning("Index setup skipped or failed: %s", exc)
    yield
    logger.info("VendorFlow API shutting down…")
    await close_mongodb_connection()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="VendorFlow API",
    description="AI-powered Vendor Onboarding and Verification Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the React dev server and production origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(vendors_router, prefix="/api")
app.include_router(documents_router, prefix="/api/vendors", tags=["Documents"])
app.include_router(test_router, prefix="/api", tags=["Database Testing"])


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["General"])
async def root():
    """Root endpoint — confirms the API is running."""
    return {
        "message": "Welcome to VendorFlow API",
        "status": "running",
    }


@app.get("/health", tags=["General"])
async def health():
    """Health-check endpoint."""
    return {"status": "healthy"}
