---
description: Provider-side write, learn, and forget implementation for the second brain system.
applyTo: "**"
---
# second-brain-learn -- Provider Instructions

This package provides the internal write and validation layer for the second
brain system. It is a provider-side implementation; all skills are
internal and are invoked by higher-level client skills, not directly by users.

## Internal skills

- **sb-learn-handler** -- Receives a validated learn request envelope, deduplicates
  by content hash, writes to the wiki via kw-wiki-ingest, and returns a learn
  receipt with status: accepted | duplicate | invalid.

- **sb-forget-handler** -- Receives a validated forget request envelope, tombstones
  the target concept via kw-wiki-archive (v1 is tombstone-only -- no destructive
  deletion), and returns a forget receipt with status: tombstoned | not_found.

- **sb-learn-validate** -- Validates a learn request envelope against the
  second-brain-interfaces schema before any wiki write. Returns
  validation result: valid (true/false) and errors list.

## Invocation model

All skills have `direct-user-invocation: disabled`. They are invoked only by
brain-learn and brain-forget client skills from the second-brain-interfaces package.
