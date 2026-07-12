# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Package versions advance independently using the `<package>--v<version>` tag
convention.

## [Unreleased]

- Add the `open-knowledge-format` dependency to `karpathy-wiki` through APM.
- Create and maintain `wiki/concepts/index.md` as the concepts sub-index.
- Exclude archived tombstones from normal query fallback results.
- Canonicalise ingest source paths and reject inputs outside approved roots.
- Fail lint when the concepts sub-index is missing.
