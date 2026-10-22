#!/usr/bin/env python3
"""Rejoue la démonstration en boucle, sans intervention : preuve de reprise automatique.

Un cycle = remise à zéro de l'état, flood, attente de l'issue décidée par le moteur de
remédiation (événements JSON `incident.resolved` / `incident.failed`), puis transaction de test
jouée de l'extérieur par `check_transaction.sh`. Un cycle n'est réussi que si les deux sont
vrais : un conteneur qui redémarre ne prouve rien.

Le RTO est mesuré du début de l'attaque à `incident.resolved` (il inclut donc la détection) ;
il est décomposé en délai de détection et temps de remédiation.

    python scripts/demo_loop.py --runs 5

Bibliothèque standard seule. Attaque limitée aux hôtes autorisés de attack/flood_http.py (PC Hôte du consortium).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REMEDIATION_CONTAINER = "resilience-remediation"
OUTCOMES = {"incident.resolved", "incident.failed"}


@dataclass
class Run:
    index: int
    detection_s: float | None = None
    rto_s: float | None = None
    incidents: int = 0
    resolved: bool = False
    probe_ok: bool = False

    @property
    def success(self) -> bool:
        return self.resolved and self.probe_ok


def default_base_url() -> str:
    """Adresse du WAF : `WAF_BIND_HOST` (environnement, sinon `.env`), 127.0.0.1 à défaut.

    Le WAF n'écoute que sur cette adresse ; viser 127.0.0.1 alors qu'elle vaut l'IP du
    réseau privé du binôme ferait refuser le flood.
    """
    host = os.environ.get("WAF_BIND_HOST", "")
    env_file = REPO_ROOT / ".env"
    if not host and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "WAF_BIND_HOST":
                host = value.strip()
    return f"http://{host or '127.0.0.1'}:8080"


def find_bash() -> str:
    """Bash à utiliser. Sous Windows, `bash` seul désigne WSL (sans nos outils) : préférer Git Bash."""
    if os.name != "nt":
        return "bash"
    git = shutil.which("git")
    if git:
        candidate = Path(git).resolve().parent.parent / "bin" / "bash.exe"
        if candidate.exists():
            return str(candidate)
    return shutil.which("bash") or "bash"


def remediation_events(since: datetime) -> list[dict]:
    """Événements JSON du moteur émis depuis `since` (lus dans ses journaux)."""
    out = subprocess.run(
        ["docker", "logs", "--since", since.isoformat(), REMEDIATION_CONTAINER],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    events = []
    for line in (out.stdout + out.stderr).splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and "event" in event and "at" in event:
            events.append(event)
    return events


def seconds_since(start: datetime, event: dict) -> float:
    return (datetime.fromisoformat(event["at"]) - start).total_seconds()


def wait_for_outcome(start: datetime, timeout_s: float) -> list[dict]:
    """Attend que le dernier incident soit clos (résolu ou en échec)."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        events = remediation_events(start)
        opened = {e["incident_id"] for e in events if e["event"] == "incident.detected"}
        closed = {e["incident_id"] for e in events if e["event"] in OUTCOMES}
        if opened and opened <= closed:
            return events
        time.sleep(2)
    return remediation_events(start)


def run_cycle(index: int, args: argparse.Namespace) -> Run:
    run = Run(index)
    print(f"\n=== Passage {index}/{args.runs} ===", flush=True)
    if subprocess.run(
        [find_bash(), str(REPO_ROOT / "scripts/reset_demo.sh")], check=False
    ).returncode:
        print("ECHEC de la remise à zéro", file=sys.stderr)
        return run
    time.sleep(args.settle)  # laisse le détecteur revoir un état sain avant l'attaque

    start = datetime.now(UTC)
    flood = subprocess.Popen(
        [
            sys.executable,
            str(REPO_ROOT / "attack/flood_http.py"),
            "--base-url",
            args.base_url,
            "--duration",
            str(args.flood_duration),
            "--rate",
            str(args.flood_rate),
        ]
    )
    events = wait_for_outcome(start, args.timeout)
    flood.wait()

    detected = [e for e in events if e["event"] == "incident.detected"]
    resolved = [e for e in events if e["event"] == "incident.resolved"]
    failed = [e for e in events if e["event"] == "incident.failed"]
    run.incidents = len(detected)
    run.resolved = bool(resolved) and not failed
    if detected:
        run.detection_s = seconds_since(start, detected[0])
    if resolved:
        run.rto_s = seconds_since(start, resolved[-1])
    # Preuve finale, jouée de l'extérieur du moteur : API saine ET transaction réglée.
    probe = subprocess.run(
        [find_bash(), str(REPO_ROOT / "scripts/check_transaction.sh")], check=False
    )
    run.probe_ok = probe.returncode == 0
    return run


def fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.0f} s"


def report(runs: list[Run]) -> None:
    print("\n=== Bilan ===")
    print("passage | détection | RTO    | incidents | reprise | transaction | verdict")
    for r in runs:
        print(
            f"{r.index:^7} | {fmt(r.detection_s):^9} | {fmt(r.rto_s):^6} | {r.incidents:^9} | "
            f"{'oui' if r.resolved else 'NON':^7} | {'oui' if r.probe_ok else 'NON':^11} | "
            f"{'OK' if r.success else 'ECHEC'}"
        )
    rtos = [r.rto_s for r in runs if r.rto_s is not None]
    ok = sum(r.success for r in runs)
    print(f"\n{ok}/{len(runs)} reprises automatiques prouvées, 0 intervention humaine.")
    if rtos:
        print(f"RTO : moyenne {statistics.mean(rtos):.0f} s, max {max(rtos):.0f} s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument(
        "--base-url",
        default=default_base_url(),
        help="WAF visé (défaut : WAF_BIND_HOST de .env, sinon 127.0.0.1)",
    )
    parser.add_argument("--flood-duration", type=float, default=30.0, help="secondes")
    parser.add_argument(
        "--flood-rate", type=int, default=60, help="threads concurrents"
    )
    parser.add_argument(
        "--settle", type=float, default=20.0, help="pause après le reset (s)"
    )
    parser.add_argument(
        "--timeout", type=float, default=240.0, help="attente de l'issue (s)"
    )
    args = parser.parse_args()

    runs = [run_cycle(i, args) for i in range(1, args.runs + 1)]
    report(runs)
    return 0 if all(r.success for r in runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
