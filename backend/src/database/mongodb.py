"""
MongoDB connection management for VendorFlow.

Exposes:
    client  — the raw MongoClient instance (or None before connect)
    db      — the selected database handle (or None before connect)
    connect_to_mongodb()       — call on app startup
    close_mongodb_connection() — call on app shutdown
"""

import os
import asyncio
import logging

import certifi
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

# Support both MONGODB_URL and legacy MONGODB_URI key names
MONGODB_URL: str = os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI", "")
DATABASE_NAME: str = os.getenv("DATABASE_NAME", "zamp")

# Module-level handles — populated by connect_to_mongodb()
client: MongoClient | None = None
db = None


async def connect_to_mongodb() -> None:
    """
    Open a PyMongo connection and verify it with a ping.
    Raises ValueError if the connection string is missing.
    Raises ServerSelectionTimeoutError if the cluster is unreachable.
    """
    global client, db

    if not MONGODB_URL:
        raise ValueError(
            "MongoDB connection string not found. "
            "Set MONGODB_URL (or MONGODB_URI) in your .env file."
        )

    logger.info("Connecting to MongoDB Atlas…")

    # Create the client (sync) — wrap in to_thread so we don't block the event loop
    client = await asyncio.to_thread(
        MongoClient,
        MONGODB_URL,
        serverSelectionTimeoutMS=5000,
        tlsCAFile=certifi.where(),
    )

    # Ping the deployment to verify the connection is live
    try:
        await asyncio.to_thread(client.admin.command, "ping")
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        logger.error("MongoDB ping failed: %s", exc)
        raise

    db = client[DATABASE_NAME]
    logger.info("Connected to MongoDB Atlas — database: '%s'", DATABASE_NAME)


async def close_mongodb_connection() -> None:
    """Close the PyMongo client on application shutdown."""
    global client
    if client is not None:
        await asyncio.to_thread(client.close)
        client = None
        logger.info("MongoDB connection closed.")

