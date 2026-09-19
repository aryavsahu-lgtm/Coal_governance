import os
import uuid
from pathlib import Path
from typing import BinaryIO, Optional
from werkzeug.utils import secure_filename
from app.config import Config
from app.storage.base import StorageService


class LocalStorageService(StorageService):
    """Local disk implementation of StorageService."""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = Path(base_path or Config.UPLOAD_FOLDER)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload(self, file_obj: BinaryIO, filename: str, subfolder: str = "general") -> dict:
        clean_name = secure_filename(filename)
        extension = clean_name.rsplit(".", 1)[-1].lower() if "." in clean_name else "dat"
        unique_name = f"{uuid.uuid4().hex}_{clean_name}"
        
        target_dir = self.base_path / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        destination = target_dir / unique_name
        
        # Save file
        if hasattr(file_obj, "save"):
            file_obj.save(str(destination))
            size = destination.stat().st_size
        else:
            data = file_obj.read()
            with open(destination, "wb") as f:
                f.write(data)
            size = len(data)

        relative_path = f"{subfolder}/{unique_name}".replace("\\", "/")
        return {
            "filename": clean_name,
            "stored_filename": unique_name,
            "relative_path": relative_path,
            "absolute_path": str(destination),
            "size_bytes": size,
            "url": f"/api/documents/file/{relative_path}",
            "extension": extension
        }

    def download(self, file_path: str) -> Optional[bytes]:
        full_path = self.base_path / file_path.replace("/", os.sep)
        if full_path.exists() and full_path.is_file():
            with open(full_path, "rb") as f:
                return f.read()
        return None

    def delete(self, file_path: str) -> bool:
        full_path = self.base_path / file_path.replace("/", os.sep)
        if full_path.exists() and full_path.is_file():
            full_path.unlink()
            return True
        return False

    def get_url(self, file_path: str) -> str:
        clean_rel = file_path.replace("\\", "/")
        return f"/api/documents/file/{clean_rel}"


# Singleton instance
storage_service = LocalStorageService()
