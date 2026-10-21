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
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db/app")

    settings = Settings.from_env()
    assert settings.jwt_secret == "y" * 40


def test_from_env_defaults_to_empty_when_nothing_set(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_FILE", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db/app")

    settings = Settings.from_env()
    assert settings.jwt_secret == ""
