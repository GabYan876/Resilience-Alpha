"""Outils hors ligne : `collect` (trafic normal -> CSV) puis `train` (CSV -> modèle).

python -m app.cli collect --count 120 --interval 5
python -m app.cli train
"""

from __future__ import annotations

import argparse
import time

import httpx

from app.adapters.csv_dataset import CsvDataset
from app.adapters.isolation_forest import IsolationForestTrainer, JoblibModelStore
from app.adapters.prometheus_source import PrometheusMetricsSource
from app.application.training import collect_samples, train_model
from app.config import Settings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="anomaly-detector")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="enregistre du trafic NORMAL depuis Prometheus")
    collect.add_argument("--count", type=int, default=120)
    collect.add_argument("--interval", type=float, default=5.0)
    commands.add_parser("train", help="entraîne le modèle sur le jeu de données")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    dataset = CsvDataset(settings.dataset_path)
    if args.command == "collect":
        with httpx.Client(timeout=settings.http_timeout_s) as client:
            source = PrometheusMetricsSource(
                client, settings.prometheus_url, settings.target_service
            )
            written = collect_samples(
                source, dataset, count=args.count, interval_s=args.interval, sleep=time.sleep
            )
        print(f"{written} échantillons ajoutés à {settings.dataset_path}")
    else:
        count = train_model(
            dataset, IsolationForestTrainer(), JoblibModelStore(settings.model_path)
        )
        print(f"modèle entraîné sur {count} échantillons : {settings.model_path}")


if __name__ == "__main__":
    main()
