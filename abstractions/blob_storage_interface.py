from abc import ABC, abstractmethod
from typing import Optional

class BlobStorageInterface(ABC):
    @abstractmethod
    def upload_blob(self, content: str, filename: str) -> str:
        pass
    
    @abstractmethod
    def download_blob(self, blob_url: str) -> Optional[str]:
        pass