"""Composition root de l'agent : câble OpenCV, le coffre de gabarits et l'API."""

from __future__ import annotations

from fastapi import FastAPI

from app.adapters.encrypted_templates import EncryptedTemplateStore
from app.adapters.opencv_camera import OpenCvCamera
from app.adapters.opencv_embedder import OpenCvFaceEmbedder
from app.api.routes import build_router
from app.application.face_agent import FaceAgent
from app.config import Settings


def build_agent(settings: Settings) -> FaceAgent:
    return FaceAgent(
        OpenCvCamera(settings.camera_index),
        OpenCvFaceEmbedder(settings.detector_path, settings.recognizer_path),
        EncryptedTemplateStore(settings.templates_dir, settings.template_key),
        settings.threshold,
    )


def create_app() -> FastAPI:
    settings = Settings.from_env()
    app = FastAPI(title="host-agent-camera", docs_url=None, redoc_url=None)
    app.include_router(build_router(build_agent(settings), settings.token))
    return app
