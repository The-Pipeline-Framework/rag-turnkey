#!/usr/bin/env bash
set -euo pipefail

read -r -a maven_args <<< "${MAVEN_ARGS:-}" || true
if [[ ${#maven_args[@]} -eq 0 ]]; then
  maven_args=("-Dmaven.repo.local=$PWD/.m2/repository")
fi
QUARKUS_OTEL_SDK_DISABLED="${QUARKUS_OTEL_SDK_DISABLED:-true}" \
  ./mvnw -B verify -Dquarkus.container-image.build=false --no-transfer-progress \
  "${maven_args[@]}"
