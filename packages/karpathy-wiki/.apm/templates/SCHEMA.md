# Karpathy Wiki -- Operating Schema

This file describes the layout, constraints, and operating rules for a
Karpathy persistent-wiki backed by an OKF v0.1 bundle.

It lives alongside `wiki/` -- never inside it. Nothing in this file belongs
inside the OKF bundle.

---

## Directory layout

```
<provider-project>/
  raw/             # immutable raw sources (outside OKF bundle)
  wiki/            # OKF bundle root
    index.md       # bundle index (required)
    log.md         # event log (required)
    concepts/      # concept documents
      index.md     # concepts sub-index
      <slug>.md    # one file per concept
  SCHEMA.md        # this file (alongside wiki/, not inside it)
```

### Boundary rule

Nothing Karpathy-specific goes inside `wiki/`. The `wiki/` directory is a
pure OKF bundle and must pass `okf-bundle-validate` without modification.

Specifically:
- `SCHEMA.md` must NOT appear inside `wiki/`
- `raw/` must NOT appear inside `wiki/`

---

## raw/ layout

`raw/` holds immutable snapshots of source material:

```
raw/
  <original-filename>.<ext>   # copied verbatim at ingest time
```

Files in `raw/` are **never modified** after being written. They serve as
provenance anchors. Concept files in `wiki/concepts/` may link to them using
relative paths (e.g. `../../raw/source.md`).

---

## wiki/ -- OKF bundle constraints

Every `.md` file inside `wiki/` must conform to OKF v0.1:

1. **index.md** (bundle root): frontmatter with `okf_version: "0.1"`;
   body lists all active concepts as Markdown list entries.
2. **log.md**: no frontmatter; `## YYYY-MM-DD` date headings in
   newest-first (descending) order.
3. **concepts/index.md**: no frontmatter; lists all concept files.
4. **concepts/<slug>.md**: YAML frontmatter with required fields (see below).

Use standard Markdown links (`[text](path)`) throughout. Wikilinks (`[[...]]`)
are not permitted in any `wiki/` file.

---

## Concept frontmatter

Every concept file MUST include these fields:

```yaml
---
id: <slug>          # lowercase, hyphen-separated, matches filename
title: <string>     # human-readable name
type: <string>      # Concept | Reference | Procedure | Example
created: YYYY-MM-DD # ISO date of first creation
modified: YYYY-MM-DD # ISO date of last update
---
```

Optional fields:

```yaml
status: archived    # set by kw-wiki-archive; never set manually
source: <path>      # relative path to raw/ source if applicable
tags: [tag1, tag2]  # free-form tags for search
```

---

## index.md structure (OKF progressive disclosure)

```markdown
---
okf_version: "0.1"
---
# Knowledge Index

## Concept

* [Sparse Autoencoder](concepts/sparse-autoencoder.md) - Feature decomposition via overcomplete bases

## Reference

* [Attention Is All You Need](concepts/attention-paper.md) - Original transformer architecture

## Archived

* [Outdated Concept](concepts/outdated.md) - [archived]
```

---

## log.md date-group format

```markdown
# Knowledge Log

## 2025-07-12

- [ingest] Absorbed "Sparse Autoencoders" from raw/karpathy-notes.md
  (wiki/concepts/sparse-autoencoder.md)

## 2025-07-10

- [init] wiki initialised
```

Rules:
- Newest date group first (descending order)
- Each entry: `- [<event>] <summary> (<paths>)`
- Events: `init`, `ingest`, `update`, `archive`
- No frontmatter in log.md

---

## Karpathy pattern summary

The Karpathy persistent-wiki pattern emphasises:

1. **Immutable raw sources**: originals never modified; `raw/` is the record.
2. **Curated concept store**: agent distils raw sources into structured concepts.
3. **Index-first retrieval**: queries hit `index.md` before scanning concepts.
4. **Append-only log**: every state change is recorded in `log.md`.
5. **Tombstone, not delete**: `kw-wiki-archive` preserves provenance.
6. **OKF conformance**: the wiki bundle is a pure OKF v0.1 artefact.

See: [Karpathy "How I use LLMs"](https://karpathy.beehiiv.com/p/how-i-use-llms)
for the original pattern description.
