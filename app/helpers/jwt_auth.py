"""
The Group of Joining Hands - Enterprise JWT Cryptographic Engine
================================================================
RFC 7519 Compliant JSON Web Token Implementation (HMAC-SHA256 / HS256)
Zero external dependencies, pure Python cryptographic implementation.
"""

import json
import base64
import hmac
import hashlib
import time
import secrets
from typing import Tuple, Dict, Any, Optional

from app.config.config import JWT_SECRET, SECRET_KEY
from app.database.db import get_db

# Effective JWT secret key
EFFECTIVE_JWT_SECRET = JWT_SECRET or SECRET_KEY
DEFAULT_TOKEN_TTL_SECONDS = 86400  # 24 Hours
TOKEN_ISSUER = "joining-hands-auth-v1"


def _base64url_encode(data: bytes) -> str:
    """Encode bytes into standard URL-safe Base64 without '=' padding."""
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')


def _base64url_decode(data: str) -> bytes:
    """Decode standard URL-safe Base64 with padding auto-adjustment."""
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data.encode('utf-8'))


def generate_jwt(
    user_id: int,
    email: str,
    role: str = "member",
    is_admin: bool = False,
    full_name: str = "",
    expires_in: int = DEFAULT_TOKEN_TTL_SECONDS
) -> str:
    """
    Generate an RFC 7519 compliant JSON Web Token (HS256).
    Claims: sub, email, role, is_admin, name, iat, exp, iss, jti
    """
    now = int(time.time())
    jti = secrets.token_hex(16)

    header = {
        "alg": "HS256",
        "typ": "JWT"
    }

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "is_admin": bool(is_admin),
        "name": full_name,
        "iat": now,
        "exp": now + expires_in,
        "iss": TOKEN_ISSUER,
        "jti": jti
    }

    header_bytes = json.dumps(header, separators=(',', ':'), sort_keys=True).encode('utf-8')
    payload_bytes = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')

    encoded_header = _base64url_encode(header_bytes)
    encoded_payload = _base64url_encode(payload_bytes)

    signing_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
    signature = hmac.new(EFFECTIVE_JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    encoded_signature = _base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def verify_jwt(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Verify signature, algorithm, expiration, and blacklist status of a JWT token.
    Returns: (is_valid: bool, payload_dict or None, error_message or None)
    """
    if not token or not isinstance(token, str):
        return False, None, "Empty or invalid token format"

    token = token.strip()
    parts = token.split('.')
    if len(parts) != 3:
        return False, None, "Invalid JWT format: Token must have 3 segments"

    encoded_header, encoded_payload, encoded_signature = parts

    try:
        header_bytes = _base64url_decode(encoded_header)
        header = json.loads(header_bytes.decode('utf-8'))
    except Exception:
        return False, None, "Malformed JWT header"

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        return False, None, "Unsupported JWT algorithm or token type"

    # Constant-time signature verification
    signing_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
    expected_sig = hmac.new(EFFECTIVE_JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    expected_encoded_sig = _base64url_encode(expected_sig)

    if not hmac.compare_digest(encoded_signature, expected_encoded_sig):
        return False, None, "Cryptographic signature verification failed"

    # Parse and validate payload
    try:
        payload_bytes = _base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode('utf-8'))
    except Exception:
        return False, None, "Malformed JWT payload"

    now = int(time.time())

    # Check expiration (exp)
    exp = payload.get("exp")
    if exp is not None and now > exp:
        return False, None, f"Token expired (expired at {exp}, current {now})"

    # Check issue time (iat) for clock skew / future tokens
    iat = payload.get("iat")
    if iat is not None and iat > now + 300:  # Allow 5 minutes clock skew
        return False, None, "Token issued in the future"

    # Check Token Revocation / Blacklist in Database
    jti = payload.get("jti")
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    if is_token_blacklisted(jti=jti, token_hash=token_hash):
        return False, None, "Token has been revoked"

    return True, payload, None


def is_token_blacklisted(jti: Optional[str] = None, token_hash: Optional[str] = None) -> bool:
    """Check if token or jti exists in token_blacklist table."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        if jti and token_hash:
            cursor.execute('SELECT 1 FROM token_blacklist WHERE jti = ? OR token_hash = ?', (jti, token_hash))
        elif jti:
            cursor.execute('SELECT 1 FROM token_blacklist WHERE jti = ?', (jti,))
        elif token_hash:
            cursor.execute('SELECT 1 FROM token_blacklist WHERE token_hash = ?', (token_hash,))
        else:
            conn.close()
            return False
            
        row = cursor.fetchone()
        conn.close()
        return bool(row)
    except Exception:
        return False


def revoke_token(token: str, user_id: Optional[int] = None, reason: str = "User logout") -> bool:
    """
    Revoke a JWT token by adding its signature hash and jti to the blacklist.
    """
    if not token:
        return False

    is_valid, payload, _ = verify_jwt(token)
    jti = payload.get("jti") if payload else None
    u_id = user_id or (int(payload.get("sub")) if payload and payload.get("sub") and payload.get("sub").isdigit() else None)
    exp = payload.get("exp") if payload else int(time.time()) + DEFAULT_TOKEN_TTL_SECONDS
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO token_blacklist (jti, token_hash, user_id, revoked_at, expires_at, reason)
            VALUES (?, ?, ?, datetime('now'), datetime(?, 'unixepoch'), ?)
        ''', (jti or token_hash[:32], token_hash, u_id, exp, reason))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def decode_jwt_unverified(token: str) -> Optional[Dict[str, Any]]:
    """Decode and extract payload without signature check (for debugging/inspection)."""
    try:
        parts = token.strip().split('.')
        if len(parts) != 3:
            return None
        payload_bytes = _base64url_decode(parts[1])
        return json.loads(payload_bytes.decode('utf-8'))
    except Exception:
        return None
