"""Cas d'usage : ouvrir/fermer la caméra, vérifier un visage 1:1, enrôler un gabarit."""

from __future__ import annotations

import threading

from app.domain.errors import CameraError
from app.domain.ports import Embedding, FaceEmbedder, FrameSource, TemplateStore
from app.domain.similarity import cosine


class FaceAgent:
    def __init__(
        self,
        source: FrameSource,
        embedder: FaceEmbedder,
        templates: TemplateStore,
        threshold: float,
        attempts: int = 8,
    ) -> None:
        self._source = source
        self._embedder = embedder
        self.templates = templates
        self.threshold = threshold
        self._attempts = attempts
        self._lock = threading.Lock()  # une seule session de caméra à la fois
        self._is_open = False

    def start(self) -> None:
        with self._lock:
            if not self._is_open:
                self._source.open()
                self._is_open = True

    def stop(self) -> None:
        with self._lock:
            self._is_open = False
            self._source.close()

    def verify(self, identifier: str) -> bool:
        """Compare le visage devant la caméra au gabarit de `identifier` (1:1).

        Aucun gabarit, aucun visage ou plusieurs visages : `False`. Aucune image conservée.
        """
        with self._lock:
            self._require_open()
            template = self.templates.get(identifier)
            for _ in range(self._attempts):
                candidate = self._embedder.embed(self._source.read())
                if template is not None and candidate is not None:
                    if cosine(candidate, template) >= self.threshold:
                        return True
            return False

    def measure(self, identifier: str) -> float | None:
        """Similarité d'une image avec le gabarit (mesure du seuil), `None` si impossible."""
        with self._lock:
            self._require_open()
            template = self.templates.get(identifier)
            candidate = self._embedder.embed(self._source.read())
            if template is None or candidate is None:
                return None
            return cosine(candidate, template)

    def enroll(self, identifier: str, samples: int = 5) -> None:
        """Moyenne de `samples` gabarits ; la caméra doit être ouverte."""
        with self._lock:
            self._require_open()
            collected: list[Embedding] = []
            for _ in range(samples * 4):  # tolère les images sans visage net
                candidate = self._embedder.embed(self._source.read())
                if candidate is not None:
                    collected.append(candidate)
                if len(collected) == samples:
                    break
            if len(collected) < samples:
                raise CameraError("pas assez d'images exploitables pour l'enrôlement")
            size = len(collected[0])
            mean = [sum(c[i] for c in collected) / samples for i in range(size)]
            self.templates.put(identifier, mean)

    def _require_open(self) -> None:
        if not self._is_open:
            raise CameraError("caméra non démarrée")
