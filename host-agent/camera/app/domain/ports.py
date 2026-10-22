"""Ports de l'agent hôte : petits et ciblés, sans OpenCV ni système de fichiers (DIP, ISP)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

Frame = Any  # image opaque pour le domaine (tableau numpy côté adaptateur)
Embedding = Sequence[float]


class FrameSource(Protocol):
    def open(self) -> None:
        """Allume la caméra. Lève `CameraError` si elle est introuvable."""
        ...

    def close(self) -> None: ...

    def read(self) -> Frame:
        """Une image. Lève `CameraError` si la caméra n'est pas ouverte ou ne répond pas."""
        ...


class FaceEmbedder(Protocol):
    def embed(self, frame: Frame) -> Embedding | None:
        """Gabarit du visage, ou `None` s'il n'y a pas exactement un visage."""
        ...


class TemplateStore(Protocol):
    def get(self, identifier: str) -> Embedding | None: ...

    def put(self, identifier: str, template: Embedding) -> None: ...

    def delete(self, identifier: str) -> None: ...
