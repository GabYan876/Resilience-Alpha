import pytest

from app.config import Settings


def test_from_env_reads_jwt_secret_from_env_var(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_FILE", raising=False)
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db/app")

    settings = Settings.from_env()
    assert settings.jwt_secret == "x" * 32


def test_from_env_prefers_jwt_secret_file_when_present(monkeypatch, tmp_path):
    live_secret = tmp_path / "jwt_secret"
    live_secret.write_text("y" * 40, encoding="utf-8")

    monkeypatch.setenv("JWT_SECRET_FILE", str(live_secret))
    monkeypatch.setenv("JWT_SECRET", "x" * 32)  # valeur de secours, ignorée si le fichier existe
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db/app")

    settings = Settings.from_env()
    assert settings.jwt_secret == "y" * 40


def test_from_env_falls_back_to_env_var_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET_FILE", str(tmp_path / "does-not-exist"))
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db/app")

    settings = Settings.from_env()
    assert settings.jwt_secret == "x" * 32


def test_from_env_requires_minimum_secret_length(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_FILE", raising=False)
    monkeypatch.setenv("JWT_SECRET", "trop-court")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db/app")

    with pytest.raises(ValueError):
        Settings.from_env()


def test_from_env_reads_backoffice_admins_list(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_FILE", raising=False)
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db/app")
    monkeypatch.setenv("BACKOFFICE_ADMINS", " Admin@Resilience.local , ,ops@resilience.local")

    settings = Settings.from_env()
    assert settings.backoffice_admins == ("admin@resilience.local", "ops@resilience.local")


def test_from_env_without_backoffice_admins_is_closed(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_FILE", raising=False)
    monkeypatch.delenv("BACKOFFICE_ADMINS", raising=False)
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db/app")

    assert Settings.from_env().backoffice_admins == ()
