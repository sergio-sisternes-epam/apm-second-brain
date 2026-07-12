// Extension: knowledge-graph
// Read-only interactive canvas that visualises a Karpathy wiki OKF bundle
// as a knowledge graph with interactive filtering and search.
//
// Copilot-only in v1. Never modifies the wiki. All actions are read-only.

import { createServer } from "node:http";
import { statSync, realpathSync } from "node:fs";
import { join, resolve, sep } from "node:path";
import { joinSession, createCanvas, CanvasError } from "@github/copilot-sdk/extension";
import { buildGraph, applyFilters, computeStatistics, GraphError } from "./graph.mjs";

// Per-instance state: { wikiRoot, graph, filters, includeArchived, server, clients, url }
const instances = new Map();

// ---------------------------------------------------------------------------
// Path safety (CanvasError-throwing wrappers; pure containment is in graph.mjs)
// ---------------------------------------------------------------------------

function canonicalWikiRoot(inputPath) {
    if (!inputPath || typeof inputPath !== "string") {
        throw new CanvasError("invalid_path", "wiki_path must be a non-empty string.");
    }
    // Resolve symlinks on the bundle root itself so the canonical real path is
    // stored, displayed, and used for all subsequent containment checks.
    // realpathSync throws if the path does not exist -- we surface that as a
    // not_found error rather than falling back to the lexical resolved path.
    let canonicalRoot;
    try {
        canonicalRoot = realpathSync(resolve(inputPath));
    } catch {
        throw new CanvasError("not_found", `Bundle root does not exist or cannot be resolved: ${inputPath}`);
    }
    const wikiDir = join(canonicalRoot, "wiki");
    let stat;
    try { stat = statSync(wikiDir); } catch {
        throw new CanvasError("not_found", `No wiki/ directory found under: ${canonicalRoot}`);
    }
    if (!stat.isDirectory()) {
        throw new CanvasError("not_found", `wiki/ exists but is not a directory: ${canonicalRoot}`);
    }
    try { statSync(join(wikiDir, "index.md")); } catch {
        throw new CanvasError("not_found", `wiki/index.md missing -- not a valid OKF bundle: ${canonicalRoot}`);
    }
    try { statSync(join(canonicalRoot, "SCHEMA.md")); } catch {
        throw new CanvasError("not_found", `SCHEMA.md missing alongside wiki/ -- not a valid OKF bundle: ${canonicalRoot}`);
    }
    return canonicalRoot;
}

// Convert GraphError (from pure graph.mjs functions) to CanvasError.
function runGraph(fn) {
    try { return fn(); }
    catch (e) {
        if (e instanceof GraphError) throw new CanvasError(e.code, e.message);
        throw e;
    }
}

// Returns the active (non-archived) graph for the given instance.
// entry.graph is always the result of buildGraph with the instance's
// includeArchived flag (default: false).  This accessor makes the
// active-view contract explicit at every call site so that statistics,
// search, focus, and edge queries cannot accidentally read raw data.
function activeGraph(entry) { return entry.graph; }

// ---------------------------------------------------------------------------
// HTML renderer
// ---------------------------------------------------------------------------

function renderGraphHtml(graph, filters, stats, wikiRoot, includeArchived) {
    const filteredGraph = applyFilters(graph, filters);
    const { focusedId } = filteredGraph;

    const nodeList = filteredGraph.nodes.map((n) => {
        const isFocused = focusedId && n.id === focusedId;
        return `
      <div class="node ${n.isOrphan ? "orphan" : ""} ${isFocused ? "focused" : ""}" data-id="${esc(n.id)}" title="${esc(n.description || n.title)}">
        <span class="node-type">${esc(n.type)}</span>
        <span class="node-title">${esc(n.title)}</span>
        ${isFocused ? '<span class="badge focus-badge">focus</span>' : ""}
        ${n.isOrphan ? '<span class="badge orphan-badge">orphan</span>' : ""}
        ${n.status ? `<span class="badge status-badge">${esc(n.status)}</span>` : ""}
        <span class="node-path">${esc(n.conceptPath)}</span>
        <span class="conn-counts">&#8593;${n.inboundCount} &#8595;${n.outboundCount}</span>
      </div>`;
    }).join("\n");

    const edgeList = filteredGraph.edges.map((e) => `
      <tr class="${e.broken ? "broken-edge" : ""}">
        <td>${esc(e.from)}</td>
        <td>${e.broken ? "&#x26A0;" : "&rarr;"}</td>
        <td>${esc(e.to)}</td>
        <td>${esc(e.label)}</td>
      </tr>`).join("\n");

    return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Knowledge Graph</title>
    <style>
      *{box-sizing:border-box}
      body{margin:0;padding:0;background:var(--background-color-default,#fff);color:var(--text-color-default,#1f2328);font-family:var(--font-sans,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif);font-size:13px}
      header{padding:.75rem 1rem;border-bottom:1px solid var(--border-color-default,#d1d9e0);display:flex;align-items:baseline;gap:.75rem}
      h1{margin:0;font-size:1rem;font-weight:600}
      .muted{color:var(--text-color-muted,#59636e);font-size:.8rem}
      .badge{display:inline-block;padding:.1rem .35rem;border-radius:4px;font-size:.7rem;font-weight:600;background:var(--true-color-blue-muted,#ddf4ff)}
      .orphan-badge{background:var(--true-color-orange-muted,#fff0d3);color:#814101}
      .status-badge{background:var(--true-color-green-muted,#d4edda);color:#0f5132}
      .panels{display:grid;grid-template-columns:1fr 1fr;gap:.5rem;padding:.75rem 1rem}
      @media(max-width:700px){.panels{grid-template-columns:1fr}}
      .panel{border:1px solid var(--border-color-default,#d1d9e0);border-radius:6px;overflow:hidden}
      .panel-head{padding:.4rem .6rem;background:var(--background-color-subtle,#f6f8fa);font-weight:600;font-size:.8rem;border-bottom:1px solid var(--border-color-default,#d1d9e0)}
      .panel-body{padding:.4rem .6rem;max-height:420px;overflow-y:auto}
      .node{padding:.3rem .4rem;border-bottom:1px solid var(--border-color-subtle,#eaeef2);display:flex;flex-wrap:wrap;gap:.3rem;align-items:baseline}
      .node:last-child{border-bottom:none}
      .node.orphan{background:var(--true-color-orange-muted,#fff0d3)}
      .node.focused{border-left:3px solid var(--true-color-blue-500,#0969da);background:var(--true-color-blue-muted,#ddf4ff)}
      .focus-badge{background:var(--true-color-blue-500,#0969da);color:#fff}
      .node-type{font-size:.65rem;text-transform:uppercase;color:var(--text-color-muted,#59636e);min-width:3.5rem}
      .node-title{font-weight:600;flex:1}
      .node-path{font-size:.7rem;color:var(--text-color-muted,#59636e);flex-basis:100%}
      .conn-counts{font-size:.7rem;color:var(--text-color-muted,#59636e);margin-left:auto}
      table{width:100%;border-collapse:collapse;font-size:.75rem}
      th{text-align:left;padding:.2rem .4rem;background:var(--background-color-subtle,#f6f8fa);border-bottom:1px solid var(--border-color-default,#d1d9e0)}
      td{padding:.2rem .4rem;border-bottom:1px solid var(--border-color-subtle,#eaeef2);word-break:break-all}
      .broken-edge td{color:#cf222e;text-decoration:line-through}
      .stats{display:flex;gap:1rem;padding:.5rem 1rem;flex-wrap:wrap;border-bottom:1px solid var(--border-color-default,#d1d9e0)}
      .stat-chip{background:var(--background-color-subtle,#f6f8fa);border:1px solid var(--border-color-default,#d1d9e0);border-radius:4px;padding:.2rem .5rem;font-size:.75rem}
      .stat-num{font-weight:700;font-size:1rem}
      .filter-bar{padding:.5rem 1rem;border-bottom:1px solid var(--border-color-default,#d1d9e0);display:flex;flex-wrap:wrap;gap:.4rem;align-items:center}
      select,input[type=text]{font:inherit;font-size:.8rem;padding:.2rem .4rem;border:1px solid var(--border-color-default,#d1d9e0);border-radius:4px;background:var(--background-color-default,#fff);color:var(--text-color-default,#1f2328)}
      button.reset-btn{font:inherit;font-size:.75rem;padding:.2rem .5rem;border:1px solid var(--border-color-default,#d1d9e0);border-radius:4px;cursor:pointer;background:var(--background-color-subtle,#f6f8fa)}
      .readonly-note{padding:.3rem 1rem;font-size:.7rem;color:var(--text-color-muted,#59636e);font-style:italic;background:var(--background-color-subtle,#f6f8fa)}
    </style>
  </head>
  <body>
    <header>
      <h1>Knowledge Graph</h1>
      <span class="muted">${esc(wikiRoot)}</span>
      ${includeArchived ? '<span class="badge" style="background:#fff0d3;color:#814101">showing archived</span>' : ""}
    </header>
    <div class="readonly-note">Read-only view -- the canvas never modifies your wiki.</div>
    <div class="stats">
      <div class="stat-chip"><div class="stat-num">${stats.nodeCount}</div>concepts</div>
      <div class="stat-chip"><div class="stat-num">${stats.edgeCount}</div>edges</div>
      <div class="stat-chip"><div class="stat-num">${stats.orphanCount}</div>orphans</div>
      ${stats.brokenEdgeCount > 0 ? `<div class="stat-chip" style="background:#fff0d3"><div class="stat-num">${stats.brokenEdgeCount}</div>broken links</div>` : ""}
    </div>
    ${focusedId ? `<div class="filter-bar" style="background:var(--true-color-blue-muted,#ddf4ff)">
      <span style="font-size:.75rem;font-weight:600">&#x25CE; Focus:</span>
      <span class="badge focus-badge">${esc(focusedId)}</span>
      <span class="muted">showing focused node + direct neighbours &mdash; ask the agent to clear_filters to return to full view</span>
    </div>` : ""}
    <div class="filter-bar">
      <span style="font-size:.75rem;font-weight:600">Filters (agent-driven):</span>
      ${filters && (filters.type || filters.tag || filters.status || filters.directory || filters.onlyOrphans || filters.onlyConnected || filters.text)
        ? `<span class="badge" style="font-size:.7rem">type:${esc(filters.type||"*")} tag:${esc(filters.tag||"*")} status:${esc(filters.status||"*")} dir:${esc(filters.directory||"*")} orphan:${filters.onlyOrphans||false} connected:${filters.onlyConnected||false} q:${esc(filters.text||"")}</span>`
        : "<span class='muted'>none -- ask the agent to filter</span>"}
    </div>
    <div class="panels">
      <div class="panel">
        <div class="panel-head">Concepts (${filteredGraph.nodes.length}/${graph.nodes.length})</div>
        <div class="panel-body">${nodeList || '<p class="muted">No concepts match the current filters.</p>'}</div>
      </div>
      <div class="panel">
        <div class="panel-head">Links (${filteredGraph.edges.length})</div>
        <div class="panel-body">
          <table>
            <thead><tr><th>From</th><th></th><th>To</th><th>Label</th></tr></thead>
            <tbody>${edgeList || '<tr><td colspan="4" class="muted">No links in view.</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    </div>
    <div style="padding:.5rem 1rem;font-size:.7rem;color:var(--text-color-muted,#59636e)">
      <strong>Most connected:</strong>
      ${stats.mostConnected.map((c) => `${esc(c.title)} (&#8593;${c.inbound} &#8595;${c.outbound})`).join(" &bull; ")}
    </div>
    <script>
      const es = new EventSource("/events");
      es.onmessage = () => window.location.reload();
    </script>
  </body>
</html>`;
}

function esc(s) {
    if (s == null) return "";
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------------------------------------------------------------------------
// HTTP server per instance
// ---------------------------------------------------------------------------

async function startServer(entry) {
    const server = createServer((req, res) => {
        if (req.url === "/events") {
            res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" });
            res.write(": connected\n\n");
            entry.clients.add(res);
            req.on("close", () => entry.clients.delete(res));
            return;
        }
        const html = renderGraphHtml(
            activeGraph(entry), entry.filters, computeStatistics(activeGraph(entry)),
            entry.wikiRoot, entry.includeArchived
        );
        res.setHeader("Content-Type", "text/html; charset=utf-8");
        res.end(html);
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const address = server.address();
    const port = typeof address === "object" && address ? address.port : 0;
    entry.server = server;
    entry.url = `http://127.0.0.1:${port}/`;
}

function broadcastRefresh(entry) {
    const payload = "data: refresh\n\n";
    for (const res of entry.clients) res.write(payload);
}

function requireEntry(ctx) {
    const entry = instances.get(ctx.instanceId);
    if (!entry) throw new CanvasError("not_open", "Canvas is not open. Call open_graph first.");
    return entry;
}

// ---------------------------------------------------------------------------
// Session + Canvas
// ---------------------------------------------------------------------------

const session = await joinSession({
    canvases: [
        createCanvas({
            id: "knowledge-graph",
            displayName: "Knowledge Graph",
            description: "Read-only interactive canvas that visualises a Karpathy wiki OKF bundle as a knowledge graph.",
            openInputSchema: {
                type: "object",
                properties: {
                    wiki_path: {
                        type: "string",
                        description: "Absolute path to the provider wiki bundle root (the directory containing wiki/ and SCHEMA.md).",
                    },
                },
                required: ["wiki_path"],
                additionalProperties: false,
            },
            actions: [
                {
                    name: "open_graph",
                    description: "Open or focus the knowledge graph canvas for the given wiki bundle path. Parses OKF concept files and renders the graph.",
                    inputSchema: {
                        type: "object",
                        properties: {
                            wiki_path: { type: "string", description: "Absolute path to the wiki bundle root." },
                        },
                        required: ["wiki_path"],
                        additionalProperties: false,
                    },
                    handler: async (ctx) => {
                        const wikiRoot = canonicalWikiRoot(ctx.input.wiki_path);
                        let entry = instances.get(ctx.instanceId);
                        if (!entry) {
                            entry = { wikiRoot, graph: null, filters: {}, includeArchived: false, clients: new Set(), server: null, url: null };
                            instances.set(ctx.instanceId, entry);
                            await startServer(entry);
                        } else {
                            entry.wikiRoot = wikiRoot;
                            entry.filters = {};
                            entry.includeArchived = false;
                        }
                        entry.graph = runGraph(() => buildGraph(wikiRoot, { includeArchived: false }));
                        broadcastRefresh(entry);
                        const stats = computeStatistics(activeGraph(entry));
                        return { ok: true, wikiRoot, nodeCount: stats.nodeCount, edgeCount: stats.edgeCount, orphanCount: stats.orphanCount };
                    },
                },
                {
                    name: "refresh_graph",
                    description: "Re-parse all concept files from disk and refresh the graph view. Use after adding, editing, or removing concepts.",
                    handler: async (ctx) => {
                        const entry = requireEntry(ctx);
                        entry.graph = runGraph(() => buildGraph(entry.wikiRoot, { includeArchived: entry.includeArchived }));
                        broadcastRefresh(entry);
                        const stats = computeStatistics(activeGraph(entry));
                        return { ok: true, nodeCount: stats.nodeCount, edgeCount: stats.edgeCount };
                    },
                },
                {
                    name: "get_statistics",
                    description: "Return graph statistics: node count, edge count, orphan count, broken link count, and the five most-connected concepts.",
                    handler: async (ctx) => {
                        const entry = requireEntry(ctx);
                        return computeStatistics(activeGraph(entry));
                    },
                },
                {
                    name: "search_nodes",
                    description: "Search concept nodes by title, concept path, description, or tag. Returns matching nodes.",
                    inputSchema: {
                        type: "object",
                        properties: {
                            query: { type: "string", minLength: 1, description: "Search string (case-insensitive substring match)." },
                        },
                        required: ["query"],
                        additionalProperties: false,
                    },
                    handler: async (ctx) => {
                        const entry = requireEntry(ctx);
                        const q = ctx.input.query.toLowerCase();
                        const results = activeGraph(entry).nodes.filter((n) =>
                            n.title.toLowerCase().includes(q) ||
                            n.description.toLowerCase().includes(q) ||
                            n.conceptPath.toLowerCase().includes(q) ||
                            n.tags.some((t) => t.toLowerCase().includes(q))
                        );
                        return { count: results.length, nodes: results.map((n) => ({ id: n.id, title: n.title, type: n.type, path: n.conceptPath, isOrphan: n.isOrphan })) };
                    },
                },
                {
                    name: "set_filter",
                    description: "Apply one or more filters to the graph view. Setting includeArchived rebuilds the graph to include or exclude archived concepts at the data level.",
                    inputSchema: {
                        type: "object",
                        properties: {
                            type: { type: "string", description: "OKF concept type (e.g. 'concept', 'term', 'note')." },
                            tag: { type: "string", description: "Require this tag to be present on the concept." },
                            status: { type: "string", description: "Concept status (e.g. 'draft', 'stable')." },
                            directory: { type: "string", description: "Prefix filter on the concept file path." },
                            onlyOrphans: { type: "boolean", description: "Show only orphan concepts (no inbound or outbound links)." },
                            onlyConnected: { type: "boolean", description: "Show only concepts with at least one link." },
                            text: { type: "string", description: "Free-text search across title, description, path, and tags." },
                            includeArchived: { type: "boolean", description: "When true, rebuilds the graph including archived concepts. When false (default), archived concepts are absent from nodes, edges, statistics, search, and orphan calculations." },
                        },
                        additionalProperties: false,
                    },
                    handler: async (ctx) => {
                        const entry = requireEntry(ctx);
                        const { includeArchived: newIncludeArchived, ...viewFilters } = ctx.input;

                        // includeArchived is an instance-level flag that triggers a graph
                        // rebuild, not a view-level filter. When it changes, archived concepts
                        // enter or leave the graph data entirely (nodes, edges, stats, search).
                        if (newIncludeArchived !== undefined) {
                            const next = !!newIncludeArchived;
                            if (next !== entry.includeArchived) {
                                entry.includeArchived = next;
                                delete entry.filters._focusId; // stale focus; clear on rebuild
                                entry.graph = runGraph(() => buildGraph(entry.wikiRoot, { includeArchived: entry.includeArchived }));
                            }
                        }

                        entry.filters = { ...entry.filters, ...viewFilters };
                        broadcastRefresh(entry);
                        const filtered = applyFilters(activeGraph(entry), entry.filters);
                        return { ok: true, visibleNodes: filtered.nodes.length, visibleEdges: filtered.edges.length, activeFilters: entry.filters, includeArchived: entry.includeArchived };
                    },
                },
                {
                    name: "clear_filters",
                    description: "Reset all active filters and focus state; show the full active-concept graph (archived remain hidden).",
                    handler: async (ctx) => {
                        const entry = requireEntry(ctx);
                        entry.filters = {};
                        if (entry.includeArchived) {
                            // Rebuild without archived when resetting to default view.
                            entry.includeArchived = false;
                            entry.graph = runGraph(() => buildGraph(entry.wikiRoot, { includeArchived: false }));
                        }
                        broadcastRefresh(entry);
                        return { ok: true, nodeCount: activeGraph(entry).nodes.length, edgeCount: activeGraph(entry).edges.length };
                    },
                },
                {
                    name: "focus_node",
                    description: "Focus a concept node by its concept path and return its immediate neighbourhood: the node itself, all inbound nodes, and all outbound nodes.",
                    inputSchema: {
                        type: "object",
                        properties: {
                            concept_path: { type: "string", description: "Concept path (relative filename without .md extension, e.g. 'neural-networks')." },
                        },
                        required: ["concept_path"],
                        additionalProperties: false,
                    },
                    handler: async (ctx) => {
                        const entry = requireEntry(ctx);
                        const target = activeGraph(entry).nodes.find((n) => n.conceptPath === ctx.input.concept_path);
                        if (!target) {
                            return { found: false, message: `No concept found with path: ${ctx.input.concept_path}` };
                        }

                        const outboundEdges = activeGraph(entry).edges.filter((e) => e.from === target.id && !e.broken);
                        const inboundEdges = activeGraph(entry).edges.filter((e) => e.to === target.id && !e.broken);

                        const outboundIds = new Set(outboundEdges.map((e) => e.to));
                        const inboundIds = new Set(inboundEdges.map((e) => e.from));

                        const outboundNodes = activeGraph(entry).nodes.filter((n) => outboundIds.has(n.id)).map((n) => ({ id: n.id, title: n.title, path: n.conceptPath }));
                        const inboundNodes = activeGraph(entry).nodes.filter((n) => inboundIds.has(n.id)).map((n) => ({ id: n.id, title: n.title, path: n.conceptPath }));

                        // Set focus filter: canvas narrows to this node + neighbourhood
                        // and highlights the focused node with a distinct style.
                        // Call clear_filters to return to the full graph.
                        entry.filters = { ...entry.filters, _focusId: target.id };
                        broadcastRefresh(entry);

                        return {
                            found: true,
                            node: { id: target.id, title: target.title, type: target.type, path: target.conceptPath, isOrphan: target.isOrphan, tags: target.tags, status: target.status, description: target.description },
                            inbound: inboundNodes,
                            outbound: outboundNodes,
                        };
                    },
                },
            ],
            open: async (ctx) => {
                const wikiPath = ctx.input && ctx.input.wiki_path ? ctx.input.wiki_path : null;
                if (!wikiPath) {
                    throw new CanvasError("missing_input", "Please provide wiki_path: the absolute path to your wiki bundle root.");
                }
                const wikiRoot = canonicalWikiRoot(wikiPath);
                let entry = instances.get(ctx.instanceId);
                if (!entry) {
                    entry = { wikiRoot, graph: null, filters: {}, includeArchived: false, clients: new Set(), server: null, url: null };
                    instances.set(ctx.instanceId, entry);
                    await startServer(entry);
                } else {
                    entry.wikiRoot = wikiRoot;
                    entry.filters = {};
                    entry.includeArchived = false;
                }
                entry.graph = runGraph(() => buildGraph(wikiRoot, { includeArchived: false }));
                return { title: "Knowledge Graph", url: entry.url, status: "ready" };
            },
            onClose: async (ctx) => {
                const entry = instances.get(ctx.instanceId);
                if (entry) {
                    instances.delete(ctx.instanceId);
                    for (const res of entry.clients) res.end();
                    if (entry.server) {
                        await new Promise((resolve) => entry.server.close(() => resolve()));
                    }
                }
            },
        }),
    ],
});
