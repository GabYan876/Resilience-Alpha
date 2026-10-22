"""Test de fumée des modèles ONNX réels (ignoré tant que les modèles ne sont pas téléchargés)."""

from __future__ import annotations

from pathlib import Path

import pytest

MODELS = Path(__file__).resolve().parent.parent / "models"
DETECTOR = MODELS / "face_detection_yunet_2023mar.onnx"
RECOGNIZER = MODELS / "face_recognition_sface_2021dec.onnx"

pytestmark = pytest.mark.skipif(
    not (DETECTOR.exists() and RECOGNIZER.exists()),
    reason="modèles absents : python scripts/download_models.py",
)


def test_image_sans_visage_donne_pas_de_gabarit() -> None:
    import numpy as np

    from app.adapters.opencv_embedder import OpenCvFaceEmbedder

    blank = np.zeros((480, 640, 3), dtype=np.uint8)

    assert OpenCvFaceEmbedder(DETECTOR, RECOGNIZER).embed(blank) is None
