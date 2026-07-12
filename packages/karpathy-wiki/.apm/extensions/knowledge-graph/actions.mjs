// actions.mjs -- SDK-independent action layer for the knowledge-graph canvas.
//
// Extracts the handler logic from extension.mjs so it can be unit-tested
// without the @github/copilot-sdk dependency. The instances Map is injected
// so tests can provide their own isolated state.
//
// Usage:
//   import { makeActions } from "./actions.mjs";
//   const { instances, dispatch } = makeActions();
//   await dispatch("open_graph", "inst-1", { wiki_path: "/path/to/bundle" });

import { buildGraph, applyFilters, computeStatistics, GraphError } from "./graph.mjs";
import { realpathSync } from "node:fs";
import { statSync } from "node:fs";
import { join, resolve } from "node:path";

export class ActionError extends Error {
    constructor(code, message) {
        super(message);
        this.name = "ActionError";
        this.code = code;
    }
}

function canonicalWikiRootPure(inputPath) {
    if (!inputPath || typeof inputPath !== "string") {
        throw new ActionError("invalid_path", "wiki_path must be a non-empty string.");
    }
    let canonicalRoot;
    try {
        canonicalRoot = realpathSync(resolve(inputPath));
    } catch {
        throw new ActionError("not_found", `Bundle root does not exist or cannot be resolved: ${inputPath}`);
    }
    const wikiDir = join(canonicalRoot, "wiki");
    try {
        const stat = statSync(wikiDir);
        if (!stat.isDirectory()) throw new Error();
    } catch {
        throw new ActionError("not_found", `No wiki/ directory found under: ${canonicalRoot}`);
    }
    try { statSync(join(wikiDir, "index.md")); } catch {
        throw new ActionError("not_found", `wiki/index.md missing: ${canonicalRoot}`);
    }
    try { statSync(join(canonicalRoot, "SCHEMA.md")); } catch {
        throw new ActionError("not_found", `SCHEMA.md missing: ${canonicalRoot}`);
    }
    return canonicalRoot;
}

function runGraph(fn) {
    try { return fn(); }
    catch (e) {
        if (e instanceof GraphError) throw new ActionError(e.code, e.message);
        throw e;
    }
}

/**
 * Create an isolated action environment.
 * @returns {{ instances: Map, dispatch: Function }}
 */
export function makeActions() {
    const instances = new Map();

    function requireEntry(instanceId) {
        const entry = instances.get(instanceId);
        if (!entry) throw new ActionError("not_open", `Instance not open: ${instanceId}`);
        return entry;
    }

    function activeGraph(entry) { return entry.graph; }

    const handlers = {
        async open_graph(instanceId, input) {
            const wikiRoot = canonicalWikiRootPure(input.wiki_path);
            let entry = instances.get(instanceId);
            if (!entry) {
                entry = { wikiRoot, graph: null, filters: {}, includeArchived: false };
                instances.set(instanceId, entry);
            } else {
                entry.wikiRoot = wikiRoot;
                entry.filters = {};
                entry.includeArchived = false;
            }
            entry.graph = runGraph(() => buildGraph(wikiRoot, { includeArchived: false }));
            const stats = computeStatistics(activeGraph(entry));
            return { ok: true, wikiRoot, nodeCount: stats.nodeCount, edgeCount: stats.edgeCount, orphanCount: stats.orphanCount };
        },

        async refresh_graph(instanceId, _input) {
            const entry = requireEntry(instanceId);
            entry.graph = runGraph(() => buildGraph(entry.wikiRoot, { includeArchived: entry.includeArchived }));
            const stats = computeStatistics(activeGraph(entry));
            return { ok: true, nodeCount: stats.nodeCount, edgeCount: stats.edgeCount };
        },

        async get_statistics(instanceId, _input) {
            const entry = requireEntry(instanceId);
            return computeStatistics(activeGraph(entry));
        },

        async search_nodes(instanceId, input) {
            const entry = requireEntry(instanceId);
            const q = (input.query || "").toLowerCase();
            const results = activeGraph(entry).nodes.filter((n) =>
                n.title.toLowerCase().includes(q) ||
                n.description.toLowerCase().includes(q) ||
                n.conceptPath.toLowerCase().includes(q) ||
                n.tags.some((t) => t.toLowerCase().includes(q))
            );
            return { count: results.length, nodes: results.map((n) => ({ id: n.id, title: n.title, type: n.type, path: n.conceptPath, isOrphan: n.isOrphan })) };
        },

        async set_filter(instanceId, input) {
            const entry = requireEntry(instanceId);
            const { includeArchived: newIncludeArchived, ...viewFilters } = input;
            if (newIncludeArchived !== undefined) {
                const next = !!newIncludeArchived;
                if (next !== entry.includeArchived) {
                    entry.includeArchived = next;
                    delete entry.filters._focusId;
                    entry.graph = runGraph(() => buildGraph(entry.wikiRoot, { includeArchived: entry.includeArchived }));
                }
            }
            entry.filters = { ...entry.filters, ...viewFilters };
            const filtered = applyFilters(activeGraph(entry), entry.filters);
            return { ok: true, visibleNodes: filtered.nodes.length, visibleEdges: filtered.edges.length, activeFilters: entry.filters, includeArchived: entry.includeArchived };
        },

        async clear_filters(instanceId, _input) {
            const entry = requireEntry(instanceId);
            entry.filters = {};
            if (entry.includeArchived) {
                entry.includeArchived = false;
                entry.graph = runGraph(() => buildGraph(entry.wikiRoot, { includeArchived: false }));
            }
            return { ok: true, nodeCount: activeGraph(entry).nodes.length, edgeCount: activeGraph(entry).edges.length };
        },

        async focus_node(instanceId, input) {
            const entry = requireEntry(instanceId);
            const target = activeGraph(entry).nodes.find((n) => n.conceptPath === input.concept_path);
            if (!target) return { found: false, message: `No concept found with path: ${input.concept_path}` };
            const outboundEdges = activeGraph(entry).edges.filter((e) => e.from === target.id && !e.broken);
            const inboundEdges = activeGraph(entry).edges.filter((e) => e.to === target.id && !e.broken);
            const outboundIds = new Set(outboundEdges.map((e) => e.to));
            const inboundIds = new Set(inboundEdges.map((e) => e.from));
            const outbound = activeGraph(entry).nodes.filter((n) => outboundIds.has(n.id)).map((n) => ({ id: n.id, title: n.title, path: n.conceptPath }));
            const inbound = activeGraph(entry).nodes.filter((n) => inboundIds.has(n.id)).map((n) => ({ id: n.id, title: n.title, path: n.conceptPath }));
            entry.filters = { ...entry.filters, _focusId: target.id };
            return {
                found: true,
                node: { id: target.id, title: target.title, type: target.type, path: target.conceptPath, isOrphan: target.isOrphan, tags: target.tags, status: target.status },
                inbound,
                outbound,
            };
        },
    };

    async function dispatch(actionName, instanceId, input = {}) {
        const handler = handlers[actionName];
        if (!handler) throw new ActionError("unknown_action", `Unknown action: ${actionName}`);
        return handler(instanceId, input);
    }

    return { instances, dispatch };
}
