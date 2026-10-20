"""Actions de remédiation : une classe = une stratégie (OCP).

Chaque action ne dépend que du petit port dont elle a besoin (ISP).
"""

from __future__ import annotations

from datetime import timedelta

from app.domain.models import ActionResult, Incident
from app.domain.ports import (
    ContainerRestarter,
    DatabaseRestorer,
    IpBlocker,
    SecretRotator,
    ServiceScaler,
    SubjectBlocker,
)


class BlockIpAction:
    name = "block_ip"
    required = False

    def __init__(self, blocker: IpBlocker) -> None:
        self._blocker = blocker

    def execute(self, incident: Incident) -> ActionResult:
        ip = incident.anomaly.attacker_ip
        if ip is None:
            return ActionResult(self.name, False, "aucune IP source identifiée")
        self._blocker.block(ip)
        return ActionResult(self.name, True, f"ip={ip}")


class BlockSubjectAction:
    name = "block_subject"
    required = False

    def __init__(self, blocker: SubjectBlocker) -> None:
        self._blocker = blocker

    def execute(self, incident: Incident) -> ActionResult:
        subject = incident.anomaly.attacker_subject
        if subject is None:
            return ActionResult(self.name, False, "aucun compte source identifié")
        self._blocker.block(subject)
        return ActionResult(self.name, True, f"subject={subject}")


class RestartServiceAction:
    name = "restart_service"
    required = False

    def __init__(self, restarter: ContainerRestarter) -> None:
        self._restarter = restarter

    def execute(self, incident: Incident) -> ActionResult:
        service = incident.anomaly.target_service
        self._restarter.restart(service)
        return ActionResult(self.name, True, f"service={service}")


class RestoreDatabaseAction:
    name = "restore_database"
    required = True

    def __init__(self, restorer: DatabaseRestorer, safety_margin_s: float = 0.0) -> None:
        self._restorer = restorer
        self._margin = timedelta(seconds=safety_margin_s)

    def execute(self, incident: Incident) -> ActionResult:
        # La corruption précède la détection : on exclut les archives prises après, sinon on
        # restaurerait la donnée déjà altérée.
        before = incident.anomaly.detected_at - self._margin
        self._restorer.restore_latest(before)
        return ActionResult(
            self.name, True, f"restauration=derniere_sauvegarde_avant:{before.isoformat()}",
            required=self.required,
        )


class ScaleServiceAction:
    name = "scale_service"
    required = False

    def __init__(self, scaler: ServiceScaler, replicas: int = 2) -> None:
        self._scaler = scaler
        self._replicas = replicas

    def execute(self, incident: Incident) -> ActionResult:
        service = incident.anomaly.target_service
        self._scaler.scale(service, self._replicas)
        return ActionResult(self.name, True, f"service={service} replicas={self._replicas}")


class RotateSecretAction:
    name = "rotate_secret"
    required = False

    def __init__(self, rotator: SecretRotator, secret_name: str) -> None:
        self._rotator = rotator
        self._secret_name = secret_name

    def execute(self, incident: Incident) -> ActionResult:
        self._rotator.rotate(self._secret_name)
        # Le nom du secret est loggé, jamais sa valeur.
        return ActionResult(self.name, True, f"secret={self._secret_name}")
