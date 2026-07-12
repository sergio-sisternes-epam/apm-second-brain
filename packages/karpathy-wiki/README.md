# karpathy-wiki

Karpathy persistent-wiki engine over a strict OKF bundle

Part of the [apm-second-brain](../../README.md) public demo monorepo.

## Status

Under development. See the root [CHANGELOG.md](../../CHANGELOG.md) for progress.

## Knowledge Graph Canvas

The Knowledge Graph Canvas is an interactive, read-only visualisation of a
Karpathy wiki OKF bundle. It renders concept nodes, directed link edges, orphan
detection, and live filtering directly in the Copilot desktop app.

### Availability

**Copilot desktop app only (v1).** The canvas is not available in Claude Code
or other agent runtimes in this release.

### Installation with canvas support

Canvas extensions require the APM experimental canvas feature and an explicit
trust approval:

```sh
# 1. Enable the canvas experimental feature (one-time, per machine)
apm experimental enable canvas

# 2. Install the package (canvas extension is included)
apm install <path-to-karpathy-wiki>

# 3. Approve the canvas extension executable
apm approve knowledge-graph
```

The trust workflow follows the APM 0.25 approval model: `apm approve` grants
the `knowledge-graph` extension permission to run as a local process. Without
approval, the canvas will not load.

The deployed bundle lands in `.github/extensions/knowledge-graph/` -- the
Copilot-only target path. It is intentionally omitted from Claude Code and
all other non-Copilot targets.

### Agent actions

All actions are **read-only**. The canvas never modifies any wiki file.

| Action | Description |
|--------|-------------|
| `open_graph` | Open or focus the graph with a validated wiki bundle path. |
| `refresh_graph` | Re-parse concept files from disk after wiki changes. |
| `get_statistics` | Return node count, edge count, orphan count, most-connected concepts. |
| `search_nodes` | Search by title, concept path, description, or tag. |
| `set_filter` | Set filters: type, tag, status, directory, connected/orphan state, free text. |
| `clear_filters` | Reset all active filters and show the full graph. |
| `focus_node` | Focus a concept by path; return its inbound and outbound neighbourhood. |

### Graph model

- **One node per OKF concept file** with valid frontmatter (`id`, `title`, `type`).
- **Directed edges** from standard Markdown links between concept files.
- **Orphan concepts** (no inbound or outbound links) are flagged with a distinct style.
- **Broken links** (links to missing files) are shown as warning edges and do not
  break the graph.
- `index.md` and `log.md` are excluded as concept nodes (structural files).

## Licence

Apache-2.0 -- see [LICENSE](../../LICENSE).
