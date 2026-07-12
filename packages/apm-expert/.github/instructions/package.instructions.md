---
description: Provider-side read and citation-backed reasoning for the second brain system.
applyTo: "**"
---
# second-brain-think -- Provider Instructions

This package provides the internal read and citation-backed reasoning layer for
the second brain system. All skills are internal and invoked by higher-level
client skills; thinking is strictly read-only -- no wiki writes occur here.

## Internal skills

- **sb-think-handler** -- Receives a validated think request envelope, queries the
  wiki via kw-wiki-query (index-first retrieval), synthesises an answer with
  explicit citations (concept_id, title, excerpt), classifies response quality
  (answered | partial | unanswered), identifies knowledge gaps, and returns the
  think response envelope from second-brain-interfaces.

- **sb-think-validate** -- Validates a think request envelope against the
  second-brain-interfaces schema. Returns validation result: valid (true/false)
  and errors list. Called by sb-think-handler before any query.

## Invocation model

All skills have `direct-user-invocation: disabled`. They are invoked only by
the brain-think client skill from the second-brain-interfaces package.
Read-only: no calls to kw-wiki-ingest, kw-wiki-archive, sb-learn, or any write
operation are permitted in this package.
