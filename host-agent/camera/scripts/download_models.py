"""Télécharge les deux modèles ONNX d'OpenCV Zoo (licence MIT) et vérifie leur empreinte SHA-256."""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

BASE = "https://github.com/opencv/opencv_zoo/raw/main/models"
MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        f"{BASE}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    "face_recognition_sface_2021dec.onnx": (
        f"{BASE}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
}


def main() -> int:
    target = Path(__file__).resolve().parent.parent / "models"
    target.mkdir(exist_ok=True)
    for name, (url, expected) in MODELS.items():
        path = target / name
        if not path.exists():
            print(f"téléchargement de {name}")
            urllib.request.urlretrieve(url, path)  # noqa: S310 - URL fixe, https
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            path.unlink()
            print(f"empreinte inattendue pour {name} : fichier supprimé")
            return 1
    print("modèles prêts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
