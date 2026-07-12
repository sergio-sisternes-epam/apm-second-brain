# Overlay README

This directory holds consumer-authored knowledge that extends or overrides
the active baseline corpus.

## Structure

```
overlay/
  concepts/      # additional or corrective OKF concept files
  tombstones/    # list of baseline concept IDs to suppress in query results
```

## Query precedence

1. Tombstones in `tombstones/` suppress matching baseline concepts.
2. Concepts in `concepts/` take precedence over matching baseline concepts.
3. Baseline concepts from the active baseline fill remaining gaps.

## Lifecycle

The overlay is preserved across baseline refreshes. When a new baseline is
activated, existing overlay files remain unchanged.
