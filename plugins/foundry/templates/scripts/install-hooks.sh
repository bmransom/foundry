#!/usr/bin/env bash
# foundry-template: install-hooks v1
# One-time per clone: route git hooks through .githooks/.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
chmod +x .githooks/*
echo "hooks installed (core.hooksPath=.githooks)"
