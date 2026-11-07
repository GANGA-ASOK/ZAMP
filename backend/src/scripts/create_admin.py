"""
Administrative Account Provisioning CLI.

Usage:
    python -m src.scripts.create_admin --email admin@vendorflow.io --name "Lead Administrator"
    (will prompt securely for password if not passed via --password or ADMIN_PASSWORD env var)

Security:
    - Never stores or logs plaintext passwords.
    - Password is hashed with Argon2id before storage.
    - Rejects duplicate admin email accounts.
    - Enforces a minimum password length of 8 characters.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from src.database.mongodb import close_mongodb_connection, connect_to_mongodb  # noqa: E402
from src.models.enums import UserRole  # noqa: E402
from src.services.auth_service import AuthService, DuplicateEmailError  # noqa: E402


async def provision_admin(name: str, email: str, password: str) -> None:
    """Connect to MongoDB and provision an administrator user."""
    print(f"Connecting to MongoDB Atlas...")
    await connect_to_mongodb()
    try:
        service = AuthService()
        service.ensure_indexes()

        user = await service.register_user(
            name=name,
            email=email,
            password=password,
            role=UserRole.ADMIN.value,
        )
        print("=" * 60)
        print("  Administrator Account Successfully Provisioned")
        print("=" * 60)
        print(f"  ID:    {user.user_id}")
        print(f"  Name:  {user.name}")
        print(f"  Email: {user.email}")
        print(f"  Role:  {user.role}")
        print("=" * 60)
    except DuplicateEmailError:
        print(f"\n[ERROR] An account with email '{email}' already exists.")
        sys.exit(1)
    except Exception as exc:
        print(f"\n[ERROR] Failed to provision administrator: {exc}")
        sys.exit(1)
    finally:
        await close_mongodb_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description="Securely provision an administrator account.")
    parser.add_argument("--name", required=True, help="Administrator's full name")
    parser.add_argument("--email", required=True, help="Administrator's unique email address")
    parser.add_argument("--password", required=False, help="Administrator's password (or leave empty to prompt)")

    args = parser.parse_args()

    name = args.name.strip()
    email = args.email.strip().lower()

    if not name:
        print("Error: Name cannot be empty.")
        sys.exit(1)

    if not email or "@" not in email:
        print("Error: A valid email address is required.")
        sys.exit(1)

    password = args.password or os.getenv("ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Enter administrator password (min 8 chars): ")
        confirm_password = getpass.getpass("Confirm administrator password: ")
        if password != confirm_password:
            print("Error: Passwords do not match.")
            sys.exit(1)

    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    asyncio.run(provision_admin(name=name, email=email, password=password))


if __name__ == "__main__":
    main()

