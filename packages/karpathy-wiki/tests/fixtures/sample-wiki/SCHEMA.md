# Karpathy Wiki -- Operating Schema

This file lives alongside `wiki/` -- never inside it.
See `.apm/templates/SCHEMA.md` for the full schema reference.

## Layout

```
sample-wiki/
  raw/             # immutable raw sources (outside OKF bundle)
  wiki/            # OKF bundle root
    index.md
    log.md
    concepts/
      index.md
      example-concept.md
  SCHEMA.md        # this file -- alongside wiki/, not inside it
```

## Boundary rule

`SCHEMA.md` and `raw/` must NOT appear inside `wiki/`.
The `wiki/` directory is a pure OKF v0.1 bundle.

## Concept frontmatter (required fields)

```yaml
id: <slug>
title: <string>
type: Concept | Reference | Procedure | Example
created: YYYY-MM-DD
modified: YYYY-MM-DD
```

## log.md format

```
# Knowledge Log

## YYYY-MM-DD   (newest first)

- [event] summary (paths)
```
