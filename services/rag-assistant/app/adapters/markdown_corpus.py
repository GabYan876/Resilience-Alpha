"""Corpus = fichiers Markdown d'un dossier monté en lecture seule."""

from __future__ import annotations

from pathlib import Path

from app.domain.models import Document


class MarkdownCorpus:
    def __init__(self, root: Path, max_bytes: int = 1_000_000) -> None:
        self._root = root
        self._max_bytes = max_bytes

    def read_all(self) -> list[Document]:
        root = self._root.resolve()
        documents = []
        for path in sorted(root.rglob("*.md")):
            resolved = path.resolve()
            # Un lien symbolique ne doit jamais faire lire un fichier hors du corpus.
            if not resolved.is_relative_to(root) or not resolved.is_file():
                continue
            if resolved.stat().st_size > self._max_bytes:
                continue
            text = resolved.read_text(encoding="utf-8", errors="replace")
            if text.strip():
                documents.append(Document(path.relative_to(root).as_posix(), text))
        return documents
