"""Configuration de l'agent : seul endroit qui lit l'environnement et les fichiers de secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    token: str  # jeton partagé avec `auth`
    template_key: bytes  # clé Fernet des gabarits
    templates_dir: Path
    detector_path: Path
    recognizer_path: Path
    camera_index: int
    threshold: float  # similarité cosinus minimale ; à mesurer sur les membres consentants

    @classmethod
    def from_env(cls) -> Settings:
        token = os.environ["AGENT_TOKEN"]  # KeyError volontaire : aucun jeton par défaut
        if len(token) < 32:
            raise ValueError("AGENT_TOKEN doit contenir au moins 32 caractères")
        key_file = Path(os.environ["TEMPLATE_KEY_FILE"])
        models = Path(os.environ.get("MODELS_DIR", _ROOT / "models"))
        return cls(
            token=token,
            template_key=key_file.read_text(encoding="utf-8").strip().encode(),
            templates_dir=Path(os.environ.get("TEMPLATES_DIR", _ROOT / "data" / "templates")),
            detector_path=models / "face_detection_yunet_2023mar.onnx",
            recognizer_path=models / "face_recognition_sface_2021dec.onnx",
            camera_index=int(os.environ.get("CAMERA_INDEX", "0")),
            threshold=float(os.environ.get("FACE_THRESHOLD", "0.363")),
        )
