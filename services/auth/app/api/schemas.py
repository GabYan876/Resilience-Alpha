"""Schémas Pydantic : conversion HTTP <-> domaine, aucune règle métier ici."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.application.use_cases import AuthResult
from app.domain.models import AdminSession

# Volontairement lâche : le seed utilise `.local`, que `EmailStr` refuse.
_EMAIL = r"^[^@\s]+@[^@\s]+$"


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=_EMAIL, max_length=320)
    number: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.lower()


class LoginIn(BaseModel):
    email: str = Field(pattern=_EMAIL, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.lower()


class AdminIdentifyIn(BaseModel):
    identifier: str = Field(pattern=_EMAIL, max_length=320)

    @field_validator("identifier")
    @classmethod
    def _lower(cls, value: str) -> str:
        return value.lower()


class AdminLoginIn(AdminIdentifyIn):
    password: str = Field(min_length=1, max_length=128)


class ProfileOut(BaseModel):
    id: UUID = Field(serialization_alias="_id")
    name: str
    email: str
    number: str | None
    iban: str
    balance_cents: int


class AuthOut(BaseModel):
    token: str
    resp: ProfileOut

    @classmethod
    def from_result(cls, result: AuthResult) -> AuthOut:
        p = result.profile
        return cls(
            token=result.token,
            resp=ProfileOut(
                id=p.id,
                name=p.full_name,
                email=p.email,
                number=p.phone,
                iban=p.iban_fake,
                balance_cents=p.balance_cents,
            ),
        )


class AdminSessionOut(BaseModel):
    token: str
    identifier: str
    name: str
    role: str

    @classmethod
    def from_session(cls, session: AdminSession) -> AdminSessionOut:
        return cls(
            token=session.token,
            identifier=session.identifier,
            name=session.full_name,
            role=session.role.value,
        )


class HabilitationIn(AdminIdentifyIn):
    role: Literal["admin", "operator"]


class HabilitationOut(BaseModel):
    identifier: str
    role: str


class LockoutOut(BaseModel):
    identifier: str
    locked_until: datetime


class AccessEntryOut(BaseModel):
    at: datetime
    event: str
    identifier: str
    detail: str
