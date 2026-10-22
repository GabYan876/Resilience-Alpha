"""Coffre de gabarits : chiffré au repos, illisible sans la bonne clé."""

from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet

from app.adapters.encrypted_templates import EncryptedTemplateStore


def test_aller_retour(tmp_path: Path) -> None:
    store = EncryptedTemplateStore(tmp_path, Fernet.generate_key())

    store.put("alice@x.fr", [0.1, 0.2, 0.3])

    assert store.get("alice@x.fr") == [0.1, 0.2, 0.3]


def test_fichier_chiffre_sans_identifiant_ni_valeurs_en_clair(tmp_path: Path) -> None:
    store = EncryptedTemplateStore(tmp_path, Fernet.generate_key())
    store.put("alice@x.fr", [0.123456, 0.2])

    raw = b"".join(p.read_bytes() for p in tmp_path.iterdir())
    names = "".join(p.name for p in tmp_path.iterdir())

    assert b"0.123456" not in raw
    assert "alice" not in names


def test_mauvaise_cle_donne_pas_de_gabarit(tmp_path: Path) -> None:
    EncryptedTemplateStore(tmp_path, Fernet.generate_key()).put("alice", [1.0])

    assert EncryptedTemplateStore(tmp_path, Fernet.generate_key()).get("alice") is None


def test_revocation(tmp_path: Path) -> None:
    store = EncryptedTemplateStore(tmp_path, Fernet.generate_key())
    store.put("alice", [1.0])

    store.delete("alice")

    assert store.get("alice") is None
