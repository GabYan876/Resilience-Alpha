"""Caméra USB via OpenCV (DirectShow sous Windows)."""

from __future__ import annotations

import sys
import time

import cv2

from app.domain.errors import CameraError
from app.domain.ports import Frame


class OpenCvCamera:
    def __init__(self, index: int = 0, warmup_frames: int = 5) -> None:
        self._index = index
        self._warmup_frames = warmup_frames
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        capture = cv2.VideoCapture(self._index, backend)
        if not capture.isOpened():
            capture.release()
            raise CameraError("caméra introuvable")
        self._capture = capture
        for _ in range(
            self._warmup_frames
        ):  # l'auto-exposition met quelques images à se stabiliser
            capture.read()
            time.sleep(0.03)

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()  # éteint le voyant de la caméra
            self._capture = None

    def read(self) -> Frame:
        if self._capture is None:
            raise CameraError("caméra non ouverte")
        ok, frame = self._capture.read()
        if not ok:
            raise CameraError("la caméra ne renvoie pas d'image")
        return frame
