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


class AccountLocked(DomainError):
    """Identifiant bloqué après trop d'échecs consécutifs."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("identifiant bloqué, réessayez plus tard")
        self.retry_after_seconds = retry_after_seconds


class FaceNotRecognized(DomainError):
    """Le visage ne correspond pas au gabarit de l'identifiant (ou est absent)."""


class FaceNotVerified(DomainError):
    """Mot de passe présenté sans reconnaissance de visage valide préalable."""


class FaceCheckUnavailable(DomainError):
    """Caméra ou agent hôte en panne : échec fermé, jamais de repli sur le mot de passe seul."""
