"""Actions de remédiation : une classe = une stratégie (OCP).

Chaque action ne dépend que du petit port dont elle a besoin (ISP).
"""

from __future__ import annotations

from app.domain.models import ActionResult, Incident
from app.domain.ports import ContainerRestarter, IpBlocker, SecretRotator, ServiceScaler


class BlockIpAction:
    name = "block_ip"

    def __init__(self, blocker: IpBlocker) -> None:
        self._blocker = blocker

    def execute(self, incident: Incident) -> ActionResult:
        ip = incident.anomaly.attacker_ip
        if ip is None:
            return ActionResult(self.name, False, "aucune IP source identifiée")
        self._blocker.block(ip)
        return ActionResult(self.name, True, f"ip={ip}")


class RestartServiceAction:
    name = "restart_service"

    def __init__(self, restarter: ContainerRestarter) -> None:
        self._restarter = restarter

    def execute(self, incident: Incident) -> ActionResult:
        service = incident.anomaly.target_service
        self._restarter.restart(service)
        return ActionResult(self.name, True, f"service={service}")


class ScaleServiceAction:
    name = "scale_service"

    def __init__(self, scaler: ServiceScaler, replicas: int = 2) -> None:
        self._scaler = scaler
        self._replicas = replicas

    def execute(self, incident: Incident) -> ActionResult:
        service = incident.anomaly.target_service
        self._scaler.scale(service, self._replicas)
        return ActionResult(self.name, True, f"service={service} replicas={self._replicas}")


class RotateSecretAction:
    name = "rotate_secret"

    def __init__(self, rotator: SecretRotator, secret_name: str) -> None:
        self._rotator = rotator
        self._secret_name = secret_name

    def execute(self, incident: Incident) -> ActionResult:
        self._rotator.rotate(self._secret_name)
        # Le nom du secret est loggé, jamais sa valeur.
        return ActionResult(self.name, True, f"secret={self._secret_name}")
