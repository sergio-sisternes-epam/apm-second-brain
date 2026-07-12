# APM Knowledge Corpus

> **Corpus not yet generated.**
>
> This directory is a placeholder. Run the knowledge build pipeline
> (see `docs/knowledge-build.md`) to populate it with OKF-formatted
> passages from the APM documentation.

## Source

| Field | Value |
|-------|-------|
| Repository | microsoft/apm |
| Tag | v0.25.0 |
| Commit | d73e6ac3645d2b9c5c813095e2e58f020f38f17a |
| Format | OKF (Open Knowledge Format) |

## Licence

The upstream APM documentation is released under the **MIT** licence.
See the upstream repository for the full licence text.

## Contents (once populated)

After running the build pipeline, this directory will contain:

- `index.json` -- OKF bundle index with entry identifiers and metadata
- `entries/` -- individual OKF-format knowledge entries (one file per topic)

Until the pipeline runs, the `apm-knowledge` skill reports
`corpus_populated: false` and returns empty passage lists.
