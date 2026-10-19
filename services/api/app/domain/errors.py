"""Erreurs du domaine. Aucune dépendance framework : la couche API les traduit en HTTP."""

from __future__ import annotations


class DomainError(Exception):
    """Racine des erreurs métier."""


class AccountNotFound(DomainError):
    """Référence de compte inconnue."""


class InvalidAmount(DomainError):
    """Montant nul, négatif ou non entier (centimes)."""


class CurrencyMismatch(DomainError):
    """Devise de l'opération différente de celle du compte."""


class SameAccountTransfer(DomainError):
    """Virement d'un compte vers lui-même."""


class InsufficientFunds(DomainError):
    """Solde insuffisant : refus métier, pas une panne."""
