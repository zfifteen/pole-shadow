#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p export

pandoc technical_note.md \
  --citeproc \
  --pdf-engine=xelatex \
  --output export/pole-shadow-technical-note.pdf
