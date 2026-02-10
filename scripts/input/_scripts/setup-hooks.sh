#!/usr/bin/env bash
set -euo pipefail

# Configure git to use repo-committed hooks.

# Parent repo hooks (guards against committing private content under input/).
git config core.hooksPath .githooks
echo "Configured: git config core.hooksPath .githooks"

# Nested input/ repo hooks (input/ is its own git repo).
git -C input config core.hooksPath .githooks
echo "Configured: git -C input config core.hooksPath .githooks"
