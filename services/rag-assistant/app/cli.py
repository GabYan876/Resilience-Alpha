"""Interrogation en ligne de commande : l'assistant n'est pas publié, on passe par `exec`.

docker compose exec rag-assistant python -m app.cli ask "Qui est le tech lead ?"
docker compose exec rag-assistant python -m app.cli index
"""

from __future__ import annotations

import argparse
import sys
import uuid

from app.config import Settings
from app.domain.models import AssistantUnavailable, InvalidQuestion
from app.main import build_services


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("index", help="reconstruit l'index")
    ask_parser = commands.add_parser("ask", help="pose une question")
    ask_parser.add_argument("question")
    args = parser.parse_args(argv)

    indexing, ask = build_services(Settings.from_env())
    trace_id = uuid.uuid4().hex
    try:
        if args.command == "index":
            print(f"{indexing.reindex(trace_id)} extraits indexés")
        else:
            answer = ask.ask(args.question, trace_id)
            print(answer.text)
            print("Sources : " + (", ".join(answer.sources) or "aucune"))
    except (InvalidQuestion, AssistantUnavailable) as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
