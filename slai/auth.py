from __future__ import annotations

import os
import time
from typing import Any

import jwt
from passlib.hash import bcrypt

JWT_SECRET = os.getenv(
    "SLAI_JWT_SECRET",
    "dev-secret-change-me",
)

JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = 8 * 60 * 60

ALLOWED_ROLES = {
    "admin",
    "manager",
    "viewer",
}

ROLE_PERMISSIONS = {
    "admin": {
        "deal:read",
        "deal:write",
        "document:write",
        "audit:run",
        "user:manage",
    },
    "manager": {
        "deal:read",
        "deal:write",
        "document:write",
        "audit:run",
    },
    "viewer": {
        "deal:read",
    },
}


def hash_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("password must be at least 8 characters")

    return bcrypt.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(
    user_id: int,
    email: str,
    role: str,
) -> str:
    now = int(time.time())

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + JWT_TTL_SECONDS,
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    if not token:
        raise ValueError("token is required")

    payload = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
    )

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or role not in ALLOWED_ROLES:
        raise ValueError("invalid token payload")

    return payload


def has_permission(user: dict[str, Any], permission: str) -> bool:
    role = user.get("role")

    return permission in ROLE_PERMISSIONS.get(role, set())
