"""Détection (YuNet) et gabarit (SFace) d'OpenCV : CPU seul, deux modèles ONNX (~39 Mo)."""

from __future__ import annotations

from pathlib import Path

import cv2

from app.domain.ports import Embedding, Frame


class OpenCvFaceEmbedder:
    def __init__(self, detector_path: Path, recognizer_path: Path) -> None:
        self._detector = cv2.FaceDetectorYN.create(str(detector_path), "", (320, 320), 0.85)
        self._recognizer = cv2.FaceRecognizerSF.create(str(recognizer_path), "")

    def embed(self, frame: Frame) -> Embedding | None:
        height, width = frame.shape[:2]
        self._detector.setInputSize((width, height))
        _, faces = self._detector.detect(frame)
        if faces is None or len(faces) != 1:  # exactement un visage : pas d'ambiguïté
            return None
        aligned = self._recognizer.alignCrop(frame, faces[0])
        return self._recognizer.feature(aligned)[0].tolist()
