"""Erreurs de l'agent hôte."""

from __future__ import annotations


class CameraError(Exception):
    """Caméra absente, non ouverte ou muette : la connexion reste fermée (échec fermé)."""
