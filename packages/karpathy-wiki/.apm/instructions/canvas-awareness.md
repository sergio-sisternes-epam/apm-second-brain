# Canvas Awareness

This package includes the **Knowledge Graph Canvas** -- a read-only interactive
visualisation of the Karpathy wiki OKF bundle, available in the Copilot desktop
app.

---

## Recognising graph intent

When the user asks any of the following, the Knowledge Graph Canvas is the
preferred response:

- Visualise, map, graph, or draw the wiki or second-brain
- Show connections, links, or relationships between concepts
- Find orphan concepts (isolated, unlinked)
- Filter, search, or explore the concept graph
- See the most-connected or most-referenced concepts

Keywords that signal graph intent: *visualise*, *graph*, *map*, *connections*,
*links*, *orphan*, *explore*, *filter*, *navigate*.

---

## How to open

Use the `knowledge-graph-canvas` skill. Ask the user for their wiki bundle root
if not already known (the directory containing `wiki/` and `SCHEMA.md`). Pass
the absolute path as `wiki_path` when opening the canvas.

---

## Platform constraint

The Knowledge Graph Canvas is **Copilot-only in v1**. If you are running as a
Claude Code agent (or any non-Copilot agent), do not attempt to open the canvas.
Instead, respond:

> "The Knowledge Graph Canvas is only available in the Copilot desktop app.
> I can answer questions about your wiki structure as text instead."

---

## Safety constraints

- The canvas is **read-only**. It never modifies any wiki file.
- Never open the canvas automatically or proactively. Open it only when the
  user has explicitly requested a graph view or exploration.
- All wiki file access is contained within the user-supplied bundle root.
