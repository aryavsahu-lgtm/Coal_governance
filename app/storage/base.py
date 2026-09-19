from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class StorageService(ABC):
    """Abstract interface for file storage operations."""

    @abstractmethod
    def upload(self, file_obj: BinaryIO, filename: str, subfolder: str = "general") -> dict:
        """
        Uploads a file.
        Returns metadata dict containing file_path, url, filename, size.
        """
        pass

    @abstractmethod
    def download(self, file_path: str) -> Optional[bytes]:
        """Downloads file contents as bytes."""
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Deletes file from storage."""
        pass

    @abstractmethod
    def get_url(self, file_path: str) -> str:
        """Returns accessible URL or URI for the stored file."""
        pass
