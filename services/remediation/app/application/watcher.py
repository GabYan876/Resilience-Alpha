"""Boucle d'arrière-plan : fait tourner le détecteur du pipeline à intervalle régulier."""

from __future__ import annotations

import logging
import threading

from app.application.pipeline import RemediationPipeline

logger = logging.getLogger(__name__)


class PipelineWatcher:
    def __init__(self, pipeline: RemediationPipeline, interval_s: float) -> None:
        self._pipeline = pipeline
        self._interval_s = interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="pipeline-watcher", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=self._interval_s + 5)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._pipeline.run_once()
            except Exception:  # la surveillance ne doit jamais mourir sur une erreur isolée
                logger.exception("watcher : échec d'un passage")
            self._stop.wait(self._interval_s)
