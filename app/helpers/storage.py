"""
The Group of Joining Hands - Persistent Media Storage Layer
============================================================
Clean storage abstraction boundary that supports current local file storage
and prepares the application for zero-code-change cloud/object storage in future.
"""

import os
import secrets
from app.config.config import UPLOADS_DIR, STORAGE_BACKEND
from app.helpers.security import validate_image_magic_bytes, is_valid_image_mime

class MediaStorageBackend:
    """Base interface for media storage backends."""
    def save(self, file_bytes: bytes, prefix: str, ext: str) -> str:
        raise NotImplementedError
        
    def exists(self, filename: str) -> bool:
        raise NotImplementedError
        
    def get_path(self, filename: str) -> str:
        raise NotImplementedError


class LocalMediaStorage(MediaStorageBackend):
    """Local filesystem media storage implementation ($0.00 cloud cost)."""
    def __init__(self, base_dir: str = UPLOADS_DIR):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
            
    def save(self, file_bytes: bytes, prefix: str, ext: str) -> str:
        filename = f"{prefix}_{secrets.token_hex(8)}{ext}"
        filepath = os.path.join(self.base_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(file_bytes)
        return f"uploads/{filename}"
        
    def exists(self, filename: str) -> bool:
        clean_name = os.path.basename(filename)
        return os.path.exists(os.path.join(self.base_dir, clean_name))
        
    def get_path(self, filename: str) -> str:
        clean_name = os.path.basename(filename)
        return os.path.join(self.base_dir, clean_name)


# Factory to retrieve active storage backend (extendable to S3 / Object storage)
def get_storage_backend() -> MediaStorageBackend:
    if STORAGE_BACKEND == 'local':
        return LocalMediaStorage()
    # Ready for future S3 / GCS cloud backends
    return LocalMediaStorage()

# Singleton storage instance
storage = get_storage_backend()
