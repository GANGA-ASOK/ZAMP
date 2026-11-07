"""
Global pytest configuration and fixtures for VendorFlow tests.
Ensures tests run isolated in-memory without contacting external MongoDB Atlas.
"""

import os
import sys

# ── Set env vars FIRST before any application module is imported ──────────────
os.environ["NVIDIA_MOCK_MODE"] = "true"
os.environ["NVIDIA_API_KEY"] = "mock_test_key"
os.environ["NVIDIA_API"] = "mock_test_key"
# Provide a dummy MongoDB URL so the config parser doesn't raise ValueError,
# but the actual connect function is replaced before it can be called.
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/zamp_test_dummy")
os.environ.setdefault("DATABASE_NAME", "zamp_test")

# ── Set up mongomock BEFORE importing the application ─────────────────────────
import mongomock
import mongomock.gridfs

mongomock.gridfs.enable_gridfs_integration()

_mock_client = mongomock.MongoClient()
_mock_db = _mock_client["zamp_test"]

# ── Patch the database module before the app is imported ─────────────────────
import src.database.mongodb as mongo_module

mongo_module.db = _mock_db
mongo_module.client = _mock_client


async def _noop_connect() -> None:
    """Replace real Atlas connection with the in-memory mock."""
    mongo_module.db = _mock_db
    mongo_module.client = _mock_client


async def _noop_close() -> None:
    pass


# Patch at the module level so any import of these names gets the noop.
mongo_module.connect_to_mongodb = _noop_connect
mongo_module.close_mongodb_connection = _noop_close

# ── NOW import the application (lifespan will use the patched connect) ────────
import src.main as main_module  # noqa: E402

# Patch the names that main.py captured at import-time via `from ... import`
main_module.connect_to_mongodb = _noop_connect
main_module.close_mongodb_connection = _noop_close

# ── Patch service constructors so they always use the mock db ─────────────────
import src.services.vendor_service as _vs_mod
import src.services.document_service as _ds_mod
import src.services.auth_service as _as_mod
import src.services.verification_service as _vfs_mod
import src.services.workflow_service as _wfs_mod

_orig_vs_init = _vs_mod.VendorService.__init__
_orig_as_init = _as_mod.AuthService.__init__
_orig_vfs_init = _vfs_mod.VerificationService.__init__
_orig_wfs_init = _wfs_mod.WorkflowService.__init__


def _patched_vs_init(self, db=None):
    _orig_vs_init(self, db=db or _mock_db)


def _patched_as_init(self, db=None):
    _orig_as_init(self, db=db or _mock_db)


def _patched_vfs_init(self, db=None):
    _orig_vfs_init(self, db=db or _mock_db)


def _patched_wfs_init(self, db=None):
    _orig_wfs_init(self, db=db or _mock_db)


_vs_mod.VendorService.__init__ = _patched_vs_init
_as_mod.AuthService.__init__ = _patched_as_init
_vfs_mod.VerificationService.__init__ = _patched_vfs_init
_wfs_mod.WorkflowService.__init__ = _patched_wfs_init

# DocumentService reads mongo_module.db directly — already patched above.

import pytest  # noqa: E402
