"""Adaptateur JWT du back-office : audience séparée du jeton client."""

from __future__ import annotations

from uuid import uuid4

import jwt
import pytest

from app.adapters.security import JwtAdminTokens, JwtTokenIssuer

SECRET = "x" * 32


def test_jeton_de_back_office_aller_retour() -> None:
    tokens = JwtAdminTokens(SECRET, 60)

    assert tokens.verify_admin(tokens.issue_admin("admin@resilience.test")) == (
        "admin@resilience.test"
    )


def test_jeton_client_refuse_par_le_back_office() -> None:
    customer = JwtTokenIssuer(SECRET, 60).issue(uuid4())

    assert JwtAdminTokens(SECRET, 60).verify_admin(customer) is None


def test_jeton_de_back_office_refuse_par_une_verification_cliente() -> None:
    # Même appel que services/api/app/adapters/jwt_verifier.py (pas d'audience attendue).
    token = JwtAdminTokens(SECRET, 60).issue_admin("admin@resilience.test")

    with pytest.raises(jwt.InvalidAudienceError):
        jwt.decode(token, SECRET, algorithms=["HS256"], options={"require": ["sub", "exp"]})


def test_jeton_expire_ou_autre_secret_refuse() -> None:
    expired = JwtAdminTokens(SECRET, -10).issue_admin("admin@resilience.test")
    other = JwtAdminTokens("y" * 32, 60).issue_admin("admin@resilience.test")

    assert JwtAdminTokens(SECRET, 60).verify_admin(expired) is None
    assert JwtAdminTokens(SECRET, 60).verify_admin(other) is None
