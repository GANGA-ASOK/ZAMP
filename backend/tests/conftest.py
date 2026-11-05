"""
Global pytest configuration and fixtures for VendorFlow tests.
Ensures tests run isolated in-memory without contacting external MongoDB Atlas.
"""

import mongomock
import pytest

import src.database.mongodb as mongo_module
import src.main as main_module

_mock_client = mongomock.MongoClient()
_mock_db = _mock_client["zamp_test"]
mongo_module.db = _mock_db


async def _noop_connect():
    mongo_module.db = _mock_db


async def _noop_close():
    pass


mongo_module.connect_to_mongodb = _noop_connect
mongo_module.close_mongodb_connection = _noop_close
main_module.connect_to_mongodb = _noop_connect
main_module.close_mongodb_connection = _noop_close
