# RAG Turnkey

This repository owns two independently deployable TPF applications: a queue-async document INDEXER and a
synchronous REST QUERY application. It consumes released TPF compiler, runtime, connector, and Block artifacts;
do not add source-tree fallbacks or clone other TPF repositories during the build.

## Boundaries

- `support/`: stable application identity helpers shared by INDEXER and QUERY.
- `indexer/`: object admission, deterministic document extraction Block, chunking, embedding Query, and vector
  upsert Command.
- `query/`: question embedding, vector search Query, LLM Query, and typed citation validation.
- `system-test/`: cross-application compatibility surface.
- `infra/` and `compose.yaml`: PostgreSQL/pgvector and Ollama development infrastructure.

INDEXER and QUERY share infrastructure, not execution ownership. Do not turn them into stages of one Pipeline.

## Build

Every Maven command must use the repository-local cache:

    -Dmaven.repo.local="$PWD/.m2/repository"

Primary gate:

    ./mvnw -B verify -Dquarkus.container-image.build=false -Dmaven.repo.local="$PWD/.m2/repository"

Maven profiles must not select a different source universe, module graph, or build topology. `central-publishing`
is the only permitted publication profile, should this application ever publish artifacts.
