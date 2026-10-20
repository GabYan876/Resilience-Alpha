"""Outils hors ligne : `collect` (trafic normal -> CSV) puis `train` (CSV -> modèle).

python -m app.cli collect --count 120 --interval 5
python -m app.cli train
python -m app.cli evaluate --normal /data/holdout.csv --attack /data/attack.csv
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import httpx

from app.adapters.csv_dataset import CsvDataset
from app.adapters.isolation_forest import IsolationForestTrainer, JoblibModelStore
from app.adapters.prometheus_source import PrometheusMetricsSource
from app.application.evaluation import EvaluationReport, evaluate_model
from app.application.training import collect_samples, train_model
from app.config import Settings


def format_report(report: EvaluationReport, confirmations: int) -> str:
    lines = [
        f"trafic normal : {report.normal_samples} mesures, "
        f"{report.false_positive_samples} jugées anormales "
        f"({report.false_positive_rate:.1%}), "
        f"{report.false_alarms} fausse(s) alerte(s) après {confirmations} confirmations",
    ]
    if report.attack_samples:
        delay = report.detection_delay_samples
        lines.append(
            f"attaque : {report.attack_samples} mesures, {report.detected_samples} jugées "
            f"anormales ({report.detection_rate:.1%}), "
            + (f"alerte à la mesure {delay}" if report.attack_detected else "AUCUNE alerte")
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="anomaly-detector")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="enregistre du trafic NORMAL depuis Prometheus")
    collect.add_argument("--count", type=int, default=120)
    collect.add_argument("--interval", type=float, default=5.0)
    commands.add_parser("train", help="entraîne le modèle sur le jeu de données")
    evaluate = commands.add_parser(
        "evaluate", help="mesure faux positifs (trafic normal) et détection (attaque)"
    )
    evaluate.add_argument("--normal", type=Path, required=True, help="CSV de trafic normal inédit")
    evaluate.add_argument("--attack", type=Path, help="CSV de mesures prises pendant une attaque")
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
    elif args.command == "evaluate":
        model = JoblibModelStore(settings.model_path).load()
        attack = CsvDataset(args.attack).read_all() if args.attack else []
        report = evaluate_model(
            model,
            CsvDataset(args.normal).read_all(),
            attack,
            confirmations=settings.confirmations,
        )
        print(format_report(report, settings.confirmations))
    else:
        count = train_model(
            dataset, IsolationForestTrainer(), JoblibModelStore(settings.model_path)
        )
        print(f"modèle entraîné sur {count} échantillons : {settings.model_path}")


if __name__ == "__main__":
    main()
