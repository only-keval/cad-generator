from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import os
import hashlib
import binascii

JWT_SECRET = os.environ.get("JWT_SECRET", "cad-gen-dev-secret-change-in-prod-32chars")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 72


def hash_password(password: str) -> str:
    """Hash a password with SHA-256 + random salt (bcrypt alternative for zero deps)."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(key).decode()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        salt_hex, key_hex = stored.split("$")
        salt = binascii.unhexlify(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return binascii.hexlify(key).decode() == key_hex
    except (ValueError, AttributeError):
        return False


def create_jwt(user_id: int) -> str:
    """Create a JWT token for a user."""
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    return pyjwt.encode({"sub": str(user_id), "exp": exp}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> int:
    """Decode a JWT and return the user_id. Raises on invalid/expired."""
    payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return int(payload["sub"])
