# knowledge-graph-canvas

Visualise a Karpathy wiki OKF bundle as an interactive knowledge graph inside
the Copilot desktop app.

---

## When to open this canvas

Open the Knowledge Graph Canvas when the user asks to:

- Visualise or explore their wiki or second-brain
- Map connections between concepts
- Show a knowledge graph or concept graph
- Find orphan concepts (no links)
- Filter the graph by type, tag, status, or directory
- See the most-connected concepts
- Understand the link structure of their brain

**Indirect trigger phrases (examples):**

- "show my knowledge graph"
- "map this brain"
- "visualise wiki connections"
- "find orphan concepts"
- "filter the graph"
- "which concepts are most connected"
- "show me everything tagged machine-learning"
- "are there any isolated concepts"
- "draw the graph"

---

## Platform availability

**Copilot desktop app only (v1).** The canvas is shipped via the
`.github/extensions/knowledge-graph/` bundle and requires the Copilot canvas
runtime.

If the user asks to visualise the graph in **Claude Code** (not supported in v1),
do not attempt to open a UI; instead explain:

> "The Knowledge Graph Canvas is not available in this environment (Copilot
> desktop app only). I can answer questions about your wiki structure,
> run `get_statistics`, or list orphan concepts as text instead."

Never fabricate a canvas open action in a non-Copilot environment.

---

## How to open

1. Ask the user for the path to their wiki bundle root (the directory that
   contains `wiki/` and `SCHEMA.md`). Each provider has a configured
   `knowledge_root`; use that path if already known.
2. Call `open_canvas` with `canvasId: "knowledge-graph"` and
   `input.wiki_path` set to the absolute bundle root path.
3. Once the canvas is open, available agent actions are listed below.

---

## Available agent actions

All actions are **read-only**. The canvas never modifies the wiki.

| Action | Description |
|--------|-------------|
| `open_graph` | Open or focus the graph with a validated wiki bundle path. Builds active (non-archived) graph. |
| `refresh_graph` | Re-parse all concept files from disk after wiki changes. Respects current `includeArchived` state. |
| `get_statistics` | Return node count, edge count, orphan count, most-connected concepts (active graph only). |
| `search_nodes` | Search by title, concept path, description, or tag (active graph only). |
| `set_filter` | Set view filters (type, tag, status, directory, orphan/connected, text) and/or `includeArchived` (boolean; changing it rebuilds the instance graph from disk). |
| `clear_filters` | Reset all filters including focus state; reset `includeArchived` to false (default archived-excluded view). |
| `focus_node` | Focus a concept by path; return its inbound and outbound neighbourhood. |

### Action semantics

**`open_graph` / `refresh_graph`**: Build or rebuild the active graph from disk.
By default (`includeArchived: false`), concepts with `status: archived` in their
OKF frontmatter are excluded at parse time -- absent from graph data, not merely
hidden. `includeArchived` is controlled via `set_filter`, not via `open_graph` or
`refresh_graph` input parameters.

**`set_filter`**: Accepts view-level filters (type, tag, status, directory,
onlyOrphans, onlyConnected, text) plus the instance-level `includeArchived`
boolean (default: false). View filters narrow the visible graph without
rebuilding from disk. When `includeArchived` changes, the graph is **rebuilt
from disk** to add or remove archived concepts at the data level. `clear_filters`
resets ALL active filters including focus state, directory prefix, type, tag,
status, orphan/connected flags, free-text search, and resets `includeArchived`
to false, restoring the default archived-excluded view.

**`includeArchived` (field of `set_filter` input, default: false)**: Controls
whether archived concepts are included in the graph. When toggled, the graph is
**rebuilt from disk** -- this is not a view filter. Archived concepts absent from
the active graph are also absent from statistics, search results, focus
neighbourhood, and orphan calculations.

**`focus_node`**: Narrows the visible graph to the focused concept node and its
direct neighbourhood (concepts it links to and concepts that link to it). All
other nodes are dimmed or hidden. The focused node is highlighted with a blue
border and a "focus" badge. Calling `clear_filters` restores the full active
graph and clears the focus state.

**`get_statistics`**: Returns counts and rankings computed over the active graph
only. Archived concepts (excluded at parse time unless `includeArchived: true`
is set via `set_filter`) are not counted in node totals, orphan counts, or
most-connected rankings.

**Multi-instance isolation**: Each canvas instance is bound to a single wiki
bundle path for its lifetime. Filter state (including `includeArchived`), focus
state, and graph data are instance-local and do not bleed between instances
targeting different wikis.

### Filter fields for `set_filter`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | — | OKF concept type (e.g. `concept`, `term`, `note`). |
| `tag` | string | — | Require this tag on the concept. |
| `status` | string | — | Concept status (e.g. `draft`, `stable`). |
| `directory` | string | — | Prefix filter on the concept file path. |
| `onlyOrphans` | boolean | false | Show only concepts with no links. |
| `onlyConnected` | boolean | false | Show only concepts with at least one link. |
| `text` | string | — | Free-text search across title, description, path, and tags. |
| `includeArchived` | boolean | false | Include archived concepts; **triggers graph rebuild from disk** when changed. |

---

## Graph model

- **Nodes**: one per OKF concept file with valid frontmatter (`id`, `title`, `type`).
- **Edges**: directed edges from standard Markdown links between concept files.
- **Orphans**: concepts with no inbound and no outbound edges; shown with a
  distinct visual style.
- **Broken links**: links to missing concept files are shown as warning edges;
  they do not break the graph.
- `index.md` and `log.md` are excluded as concept nodes (structural files).

---

## Safety

- The canvas **never modifies the wiki**. All operations are read-only.
- Never open the canvas automatically or in the background; only open it
  when the user has explicitly requested a graph view or exploration.
- All file access is contained within the user-supplied wiki bundle root;
  path traversal outside that root is rejected.
