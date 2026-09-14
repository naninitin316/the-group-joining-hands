"""
The Group of Joining Hands - Security & Helper Utilities
========================================================
Enterprise Security, Hashing, and Input Handling Helper Functions
"""

import hashlib
import secrets
import html
import hmac

# Secure salt generation and PBKDF2 iterations
PBKDF2_ITERATIONS = 600000

def hash_password(password: str) -> str:
    """Hash password using industry-standard PBKDF2-HMAC-SHA256 with cryptographic salt."""
    if not password:
        return ""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt}${key}"

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """
    Verify password against stored hash with zero-downtime migration support:
    - Supports new format: pbkdf2:sha256:<iter>$<salt>$<key>
    - Supports legacy format: raw SHA-256 (64 hex characters)
    """
    if not stored_hash or not provided_password:
        return False
    
    # New PBKDF2 Format
    if stored_hash.startswith("pbkdf2:sha256:"):
        try:
            parts = stored_hash.split("$")
            if len(parts) != 3:
                return False
            meta, salt, expected_key = parts
            iterations = int(meta.split(":")[-1])
            computed_key = hashlib.pbkdf2_hmac(
                'sha256',
                provided_password.encode('utf-8'),
                salt.encode('utf-8'),
                iterations
            ).hex()
            return hmac.compare_digest(expected_key, computed_key)
        except Exception:
            return False
            
    # Legacy SHA-256 Format (for existing users)
    legacy_hash = hashlib.sha256(provided_password.encode('utf-8')).hexdigest()
    return hmac.compare_digest(stored_hash, legacy_hash)

def generate_token() -> str:
    """Generate a secure cryptographic 64-character token."""
    return secrets.token_hex(32)

def sanitize_input(text: str) -> str:
    """Sanitize string input to mitigate XSS vulnerabilities."""
    if not text:
        return ""
    return html.escape(str(text))

def is_valid_image_mime(filename: str) -> bool:
    """Validate allowed static photo extensions."""
    allowed_exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    return filename.lower().endswith(allowed_exts)

def validate_image_magic_bytes(data: bytes) -> str | None:
    """
    Validate binary image header signatures (Magic Bytes).
    Returns extension (e.g. '.jpg', '.png', '.webp', '.gif') or None if invalid.
    """
    if not data or len(data) < 12:
        return None
    # JPEG: FF D8 FF
    if data[:3] == b'\xff\xd8\xff':
        return '.jpg'
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return '.png'
    # GIF: GIF87a or GIF89a
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return '.gif'
    # WEBP: RIFF....WEBP
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return '.webp'
    return None

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename against path traversal (../, ..\, null bytes) and invalid chars.
    Ensures safe filesystem usage.
    """
    if not filename:
        return f"file_{secrets.token_hex(6)}.bin"
    # Remove null bytes, slashes, backslashes, and path traversal sequences
    clean = filename.replace('\x00', '').replace('/', '_').replace('\\', '_').replace('..', '')
    clean = "".join(c for c in clean if c.isalnum() or c in ('-', '_', '.')).strip('._')
    return clean if clean else f"file_{secrets.token_hex(6)}.bin"

def inspect_image_dimensions(data: bytes) -> tuple[int, int] | None:
    """
    Extract image dimensions safely from binary header to detect decompression bombs.
    Supports PNG, JPEG, GIF. Returns (width, height) or None.
    """
    if not data or len(data) < 24:
        return None
    try:
        # PNG: bytes 16-24 contain width & height as 4-byte big-endian integers
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            w = int.from_bytes(data[16:20], 'big')
            h = int.from_bytes(data[20:24], 'big')
            return w, h
        # GIF: bytes 6-10 contain width & height as 2-byte little-endian integers
        if data[:6] in (b'GIF87a', b'GIF89a'):
            w = int.from_bytes(data[6:8], 'little')
            h = int.from_bytes(data[8:10], 'little')
            return w, h
        # JPEG: SOF markers (0xFFC0 to 0xFFCF except 0xFFC4/0xFFC8)
        if data[:3] == b'\xff\xd8\xff':
            idx = 2
            while idx < len(data) - 9:
                if data[idx] == 0xff:
                    marker = data[idx + 1]
                    if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                        h = int.from_bytes(data[idx + 5:idx + 7], 'big')
                        w = int.from_bytes(data[idx + 7:idx + 9], 'big')
                        return w, h
                    length = int.from_bytes(data[idx + 2:idx + 4], 'big')
                    idx += 2 + length
                else:
                    idx += 1
    except Exception:
        pass
    return None

