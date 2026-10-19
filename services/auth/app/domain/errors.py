"""Erreurs du domaine. Aucune dépendance framework : la couche API les traduit en HTTP."""

from __future__ import annotations


class DomainError(Exception):
    """Racine des erreurs métier ; le message est destiné à l'utilisateur."""


class EmailAlreadyUsed(DomainError):
    """Adresse e-mail déjà inscrite."""


class PhoneAlreadyUsed(DomainError):
    """Numéro de téléphone déjà inscrit."""


class InvalidCredentials(DomainError):
    """E-mail inconnu ou mot de passe faux : volontairement indiscernables."""
