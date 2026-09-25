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

## Cross-repository system tests

Owner-local verification is the first gate. `.github/tpf-system-tests.json` owns the stable RAG system-suite
command. `TPF Candidate Build` and the trusted publisher create an immutable, source-only candidate manifest;
`tpf/system-tests` records compatibility evidence on that exact source SHA.

For an ordinary single-repository pull request, use the candidate publisher and singleton system-test path above.
For a coordinated change, do **not** wait for participating candidate publishers and do not merge or publish
snapshots one repository at a time. Manually run
[`TPF System Tests — Compatibility Set`](https://github.com/The-Pipeline-Framework/pipelineframework/actions/workflows/system-test-compatibility-set.yml)
with one stable set ID and 2–10 pull-request URLs, one per line. The coordinator pins each PR head and tested merge
commit, builds participating Maven reactors in dependency order into one isolated repository, and runs one product
test over the resulting set. A new commit invalidates that PR's result: rerun the same set ID with the current URLs.
Require the same `tpf/system-tests` success on every participating SHA. Do not substitute snapshots, branch heads,
source checkouts or a composite Maven reactor. See the canonical
[cross-repository system-test runbook](https://github.com/The-Pipeline-Framework/pipelineframework/blob/main/docs/evolve/cross-repository-system-tests.md).

Repository setup requires repository-scoped dispatch credentials. If the workflow exposes them as
`SYSTEM_TEST_APP_ID` and `SYSTEM_TEST_APP_PRIVATE_KEY`, they must belong to a dispatch-only App installed solely on
`pipelineframework`, never the coordinator App. This source-only publisher does not need Maven package authority;
fork publication additionally requires the
`safe-to-system-test` label. Never expose dispatch or status credentials to owner-suite jobs.

## Build

Every Maven command must use the repository-local cache:

    -Dmaven.repo.local="$PWD/.m2/repository"

Primary gate:

    ./mvnw -B verify -Dquarkus.container-image.build=false -Dmaven.repo.local="$PWD/.m2/repository"

Maven profiles must not select a different source universe, module graph, or build topology. `central-publishing`
is the only permitted publication profile, should this application ever publish artifacts.
