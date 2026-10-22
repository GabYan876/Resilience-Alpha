"""Liste de sources bloquées, lue par le WAF (njs) à chaque requête.

Une entrée par ligne : `ip:<adresse>` ou `sub:<identifiant>`. Le fichier vit dans un volume
partagé : écriture ici, lecture seule côté WAF. L'écriture est atomique (fichier temporaire puis
remplacement) pour que le WAF ne lise jamais une liste tronquée.

`IpBlocklist` et `SubjectBlocklist` sont deux vues du même fichier, une par port (`IpBlocker`,
`SubjectBlocker`) : les deux ports portent la même méthode `block` mais pas le même préfixe.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock


class BlocklistFile:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._lock = Lock()  # les routes synchrones de FastAPI tournent dans un pool de threads

    def add(self, entry: str) -> None:
        with self._lock:
            entries = self._read()
            if entry not in entries:
                self._write([*entries, entry])

    def remove(self, entry: str) -> None:
        with self._lock:
            self._write([e for e in self._read() if e != entry])

    def list_entries(self) -> list[str]:
        """Lecture seule, pour l'inspection (route /blocklist, démo rejouable)."""
        with self._lock:
            return self._read()

    def _read(self) -> list[str]:
        try:
            return [line for line in self._path.read_text(encoding="utf-8").splitlines() if line]
        except FileNotFoundError:
            return []

    def _write(self, entries: list[str]) -> None:
        tmp = self._path.with_name(self._path.name + ".tmp")
        tmp.write_text("".join(f"{e}\n" for e in entries), encoding="utf-8")
        os.replace(tmp, self._path)


class IpBlocklist:
    def __init__(self, file: BlocklistFile) -> None:
        self._file = file

    def block(self, ip: str) -> None:
        self._file.add(f"ip:{ip}")

    def unblock(self, ip: str) -> None:
        self._file.remove(f"ip:{ip}")


class SubjectBlocklist:
    def __init__(self, file: BlocklistFile) -> None:
        self._file = file

    def block(self, subject: str) -> None:
        self._file.add(f"sub:{subject}")

    def unblock(self, subject: str) -> None:
        self._file.remove(f"sub:{subject}")
