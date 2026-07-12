# apm-expert

> **SCAFFOLD STATUS: NOT READY FOR USE**
>
> This package is a scaffold. The APM documentation corpus has **not** been
> built or ingested. The `apm-expert` agent will return `quality: unanswered`
> for every query until all of the following gates have passed:
>
> 1. **Build corpus** -- clone microsoft/apm at d73e6ac3, convert docs to OKF format
> 2. **Validate OKF conformance** -- `apm run okf-bundle-validate`
> 3. **Run integrity checks** -- verify MANIFEST.json integrityHash
> 4. **Run conformance tests** -- all tests in `packages/apm-expert/tests/` pass
> 5. **Register** -- invoke `akn-register` only after all above gates pass
>
> See `docs/knowledge-build.md` for the full procedure.

APM documentation expert scaffold backed by a vendored OKF corpus (not yet built).

Part of the [apm-second-brain](../../README.md) public demo monorepo.

## Status

Scaffold. Corpus not yet populated. See the root [CHANGELOG.md](../../CHANGELOG.md)
for progress and `docs/knowledge-build.md` for the build procedure.

## Licence

Apache-2.0 (package code) -- see [LICENSE](../../LICENSE).
Corpus content: MIT -- see `docs/knowledge-build.md` and `CORPUS.md`.
