from app.adapters.secret_rotation import SopsSecretRotator


def test_rotate_calls_sops_and_writes_live_file(tmp_path):
    live_path = tmp_path / "jwt_secret"
    calls: list[list[str]] = []

    rotator = SopsSecretRotator(
        encrypted_path="/secrets/jwt.enc.yaml",
        live_secret_path=str(live_path),
        run=calls.append,
    )
    rotator.rotate("jwt_secret")

    assert calls[0][:2] == ["sops", "--set"]
    assert calls[0][-1] == "/secrets/jwt.enc.yaml"
    assert '["jwt_secret"]' in calls[0][2]

    written = live_path.read_text(encoding="utf-8")
    assert len(written) > 32  # un token_urlsafe(48), pas une valeur vide ou tronquée


def test_rotate_generates_a_different_value_each_time(tmp_path):
    live_path = tmp_path / "jwt_secret"
    rotator = SopsSecretRotator(
        encrypted_path="/secrets/jwt.enc.yaml", live_secret_path=str(live_path), run=lambda _: None
    )

    rotator.rotate("jwt_secret")
    first = live_path.read_text(encoding="utf-8")
    rotator.rotate("jwt_secret")
    second = live_path.read_text(encoding="utf-8")

    assert first != second
