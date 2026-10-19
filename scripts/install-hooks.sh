#!/usr/bin/env bash
# Active les hooks Git du dépôt (à lancer une fois par PC, depuis n'importe où dans le dépôt).
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
git -C "$root" config core.hooksPath scripts/git-hooks
chmod +x "$root"/scripts/git-hooks/* 2>/dev/null || true
echo "Hooks activés (core.hooksPath = scripts/git-hooks) : push direct sur main interdit."
