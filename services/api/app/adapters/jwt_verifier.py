"""Vérification des jetons émis par le service `auth` (JWT HS256, secret partagé)."""

from __future__ import annotations

from uuid import UUID

import jwt


class JwtTokenVerifier:
    """Implémente le port `TokenVerifier`."""

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def user_id(self, token: str) -> UUID | None:
        if not self._secret:
            return None  # sans secret configuré, aucun jeton n'est accepté
        try:
            # L'algorithme est figé : jamais celui que le jeton annonce (attaque `alg`).
            claims = jwt.decode(
                token, self._secret, algorithms=["HS256"], options={"require": ["sub", "exp"]}
            )
            return UUID(claims["sub"])
        except (jwt.InvalidTokenError, ValueError):
            return None
