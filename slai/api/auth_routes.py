from __future__ import annotations

import re

from ..db import get_connection
from ..auth import (
    ALLOWED_ROLES,
    create_access_token,
    hash_password,
    verify_password,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def register_user(data: dict) -> dict:
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password")
    role = str(data.get("role", "viewer")).strip().lower()

    if not EMAIL_RE.match(email):
        raise ValueError("valid email is required")

    if role not in ALLOWED_ROLES:
        raise ValueError("unsupported role")

    password_hash = hash_password(password)

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if existing:
            raise ValueError("email already registered")

        cursor = conn.execute(
            """
            INSERT INTO users (email, password_hash, role)
            VALUES (?, ?, ?)
            """,
            (email, password_hash, role),
        )
        user_id = cursor.lastrowid

    token = create_access_token(
        user_id=user_id,
        email=email,
        role=role,
    )

    return {
        "status": "registered",
        "user": {
            "id": user_id,
            "email": email,
            "role": role,
        },
        "access_token": token,
        "token_type": "Bearer",
    }


def login_user(data: dict) -> dict:
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password")

    if not email or not password:
        raise ValueError("email and password are required")

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, email, password_hash, role
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if row is None or not verify_password(
        password,
        row["password_hash"],
    ):
        raise ValueError("invalid email or password")

    token = create_access_token(
        user_id=row["id"],
        email=row["email"],
        role=row["role"],
    )

    return {
        "status": "authenticated",
        "user": {
            "id": row["id"],
            "email": row["email"],
            "role": row["role"],
        },
        "access_token": token,
        "token_type": "Bearer",
    }
