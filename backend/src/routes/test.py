"""
Temporary database connectivity test routes.

These endpoints exist solely to verify that VendorFlow can read from and write
to MongoDB Atlas.  They should be removed (or protected) before going to
production.

Routes:
    POST  /api/test-db  — Insert a timestamped document into connection_tests
    GET   /api/test-db  — Retrieve all documents from connection_tests
"""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

import src.database.mongodb as mongo_module

router = APIRouter()


def _get_db():
    """Return the active database handle or raise 503."""
    if mongo_module.db is None:
        raise HTTPException(
            status_code=503,
            detail="Database not connected. Please try again shortly.",
        )
    return mongo_module.db


@router.post("/test-db", summary="Insert a test document into MongoDB")
async def insert_test_data():
    """
    Inserts a timestamped document into the ``connection_tests`` collection
    and returns the generated ``_id`` as a string.
    """
    db = _get_db()

    document = {
        "message": "VendorFlow database connection successful",
        "project": "VendorFlow",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    result = await asyncio.to_thread(db.connection_tests.insert_one, document)

    return {
        "message": "Test document inserted successfully.",
        "inserted_id": str(result.inserted_id),
        "collection": "connection_tests",
    }


@router.get("/test-db", summary="Retrieve all test documents from MongoDB")
async def get_test_data():
    """
    Returns every document in the ``connection_tests`` collection.
    ``_id`` fields are excluded from the response (not JSON-serialisable by
    default).
    """
    db = _get_db()

    docs = await asyncio.to_thread(
        lambda: list(db.connection_tests.find({}, {"_id": 0}))
    )

    return {
        "count": len(docs),
        "collection": "connection_tests",
        "data": docs,
    }

