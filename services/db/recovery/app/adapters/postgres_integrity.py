"""Mesure d'intégrité du grand livre par une requête `psql` en lecture seule."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable

from app.domain.ports import IntegritySnapshot

# Une transaction saine a au moins une écriture et autant de crédit que de débit.
_QUERY = """
SELECT
  (SELECT count(*) FROM transactions),
  (SELECT count(*) FROM ledger_entries),
  (SELECT count(*) FROM transactions t WHERE
     NOT EXISTS (SELECT 1 FROM ledger_entries l WHERE l.transaction_id = t.id)
     OR (SELECT coalesce(sum(CASE l.direction WHEN 'credit' THEN l.amount_cents
                             ELSE -l.amount_cents END), 0)
         FROM ledger_entries l WHERE l.transaction_id = t.id) <> 0)
"""


class PostgresIntegrityProbe:
    def __init__(
        self,
        database: str,
        pg_host: str,
        pg_port: int,
        pg_user: str,
        pg_password: str,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._database = database
        self._env = {
            **os.environ,
            "PGHOST": pg_host,
            "PGPORT": str(pg_port),
            "PGUSER": pg_user,
            "PGPASSWORD": pg_password,
        }
        self._run = run

    def snapshot(self) -> IntegritySnapshot:
        result = self._run(
            [
                "psql",
                "--no-password",
                "--tuples-only",
                "--no-align",
                "--field-separator=,",
                f"--dbname={self._database}",
                "--command=" + _QUERY,
            ],
            env=self._env,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        counters = [int(value) for value in result.stdout.strip().split(",")]
        return IntegritySnapshot(*counters)
