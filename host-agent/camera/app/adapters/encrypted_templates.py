"""Gabarits chiffrés au repos (Fernet) : un fichier par identifiant, jamais l'image.

Le nom de fichier est une empreinte de l'identifiant ; le contenu est illisible sans la clé.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.domain.ports import Embedding


class EncryptedTemplateStore:
    def __init__(self, directory: Path, key: bytes) -> None:
        self._directory = directory
        self._fernet = Fernet(key)
        directory.mkdir(parents=True, exist_ok=True)

    def get(self, identifier: str) -> Embedding | None:
        path = self._path(identifier)
        if not path.exists():
            return None
        try:
            return json.loads(self._fernet.decrypt(path.read_bytes()))
        except (InvalidToken, ValueError):
            return None  # clé changée ou fichier altéré : traité comme « pas de gabarit »

    def put(self, identifier: str, template: Embedding) -> None:
        payload = json.dumps(list(template)).encode()
        self._path(identifier).write_bytes(self._fernet.encrypt(payload))

    def delete(self, identifier: str) -> None:
        self._path(identifier).unlink(missing_ok=True)

    def _path(self, identifier: str) -> Path:
        return self._directory / f"{hashlib.sha256(identifier.encode()).hexdigest()}.tpl"
