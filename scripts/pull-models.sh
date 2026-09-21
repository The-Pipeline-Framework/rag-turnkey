#!/usr/bin/env bash
set -euo pipefail
ollama_url="${OLLAMA_BASE_URL:-http://localhost:11435}"
ollama_url="${ollama_url%/}"
curl --fail --silent --show-error "$ollama_url/api/pull" -d '{"name":"nomic-embed-text"}'
curl --fail --silent --show-error "$ollama_url/api/pull" -d '{"name":"qwen3:8b"}'
