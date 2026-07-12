// graph.mjs -- pure graph functions, no SDK dependency.
// Importable by both extension.mjs and by unit tests (no @github/copilot-sdk import).

import { readFileSync, readdirSync, realpathSync } from "node:fs";
import { join, resolve, relative, normalize, extname, basename } from "node:path";

// ---------------------------------------------------------------------------
// GraphError -- plain error subclass; extension.mjs converts to CanvasError
// ---------------------------------------------------------------------------

export class GraphError extends Error {
    constructor(code, message) {
        super(message);
        this.name = "GraphError";
        this.code = code;
    }
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STRUCTURAL_FILES = new Set(["index.md", "log.md"]);
const FRONTMATTER_RE = /^---\n([\s\S]*?)\n---/;
const MD_LINK_RE = /\[([^\]]*)\]\(([^)]+)\)/g;

// ---------------------------------------------------------------------------
// Path containment (no CanvasError; throws GraphError)
// ---------------------------------------------------------------------------

function containmentCheck(filePath, root) {
    let realFile, realRoot;
    try { realFile = realpathSync(filePath); } catch { realFile = filePath; }
    try { realRoot = realpathSync(root); } catch { realRoot = root; }
    const rel = relative(realRoot, realFile);
    if (rel.startsWith("..") || normalize(rel) === "..") {
        throw new GraphError("path_traversal", `File path escapes wiki root: ${filePath}`);
    }
}

// ---------------------------------------------------------------------------
// OKF frontmatter parser
// ---------------------------------------------------------------------------

export function parseFrontmatter(text) {
    const match = FRONTMATTER_RE.exec(text);
    if (!match) return null;
    const block = match[1];
    const fields = {};
    for (const line of block.split("\n")) {
        const colon = line.indexOf(":");
        if (colon < 1) continue;
        const key = line.slice(0, colon).trim();
        let val = line.slice(colon + 1).trim();
        // Strip YAML inline list brackets if present
        if (val.startsWith("[") && val.endsWith("]")) {
            val = val.slice(1, -1).split(",").map((s) => s.trim().replace(/^['"]|['"]$/g, ""));
        }
        fields[key] = val;
    }
    return fields;
}

// ---------------------------------------------------------------------------
// Markdown link extractor
// ---------------------------------------------------------------------------

export function extractLinks(text, sourceDir) {
    const links = [];
    let m;
    // Reset lastIndex before use (global regex reuse safety)
    MD_LINK_RE.lastIndex = 0;
    while ((m = MD_LINK_RE.exec(text)) !== null) {
        const href = m[2].split("#")[0].trim(); // strip anchors
        if (!href || href.startsWith("http://") || href.startsWith("https://") || href.startsWith("mailto:")) {
            continue;
        }
        if (!href.endsWith(".md")) continue;
        const target = resolve(sourceDir, href);
        links.push({ label: m[1], target });
    }
    return links;
}

// ---------------------------------------------------------------------------
// Graph builder
//
// Archived concepts are excluded from the graph at parse time when
// includeArchived is false (the default).  This means they are absent from:
//   - the nodes array
//   - edge construction (links to/from them appear broken or are absent)
//   - statistics (node/edge/orphan counts reflect only active concepts)
//   - search (search_nodes searches entry.graph.nodes)
//   - orphan calculations
//
// Pass { includeArchived: true } to include archived concepts alongside
// active ones (e.g. for historical review or migration audits).
// ---------------------------------------------------------------------------

export function buildGraph(wikiRoot, { includeArchived = false } = {}) {
    const conceptsDir = join(wikiRoot, "wiki", "concepts");
    let files;
    try {
        files = readdirSync(conceptsDir).filter((f) => f.endsWith(".md"));
    } catch {
        throw new GraphError("not_found", `concepts/ directory not found under wiki/: ${wikiRoot}`);
    }

    const nodes = new Map(); // path -> node
    const rawLinks = [];     // { fromPath, toPath, label }

    for (const file of files) {
        if (STRUCTURAL_FILES.has(file)) continue;
        const filePath = join(conceptsDir, file);
        containmentCheck(filePath, wikiRoot);

        let text;
        try { text = readFileSync(filePath, "utf-8"); } catch { continue; }

        const fm = parseFrontmatter(text);
        if (!fm || !fm.id || !fm.title || !fm.type) continue;

        // Exclude archived concepts at build time so they are structurally
        // absent from edges, statistics, search, and orphan calculations.
        if (!includeArchived && fm.status === "archived") continue;

        const node = {
            id: fm.id,
            title: fm.title,
            type: fm.type,
            description: fm.description || "",
            tags: Array.isArray(fm.tags) ? fm.tags : (fm.tags ? [fm.tags] : []),
            status: fm.status || "",
            path: relative(wikiRoot, filePath),
            conceptPath: relative(join(wikiRoot, "wiki", "concepts"), filePath).replace(/\.md$/, ""),
            isOrphan: true,  // resolved after edge building
        };
        nodes.set(filePath, node);

        const links = extractLinks(text, conceptsDir);
        for (const { label, target } of links) {
            // Only include links whose resolved target is inside wiki/concepts/
            // to avoid false "broken" edges for raw/ or other non-concept files.
            const rel = relative(conceptsDir, target);
            if (rel.startsWith("..")) continue;
            rawLinks.push({ fromPath: filePath, toPath: target, label });
        }
    }

    // Also scan wiki/index.md and wiki/log.md for links to concepts.
    // These files are excluded as nodes but their outbound links still count
    // as inbound credit for target concepts (preventing false orphans).
    // Resolve relative to wiki/ (the structural file's own directory).
    const wikiDir = join(wikiRoot, "wiki");
    for (const structFile of ["index.md", "log.md"]) {
        const fp = join(wikiDir, structFile);
        let text;
        try { text = readFileSync(fp, "utf-8"); } catch { continue; }
        const links = extractLinks(text, wikiDir);
        for (const { label, target } of links) {
            const rel = relative(conceptsDir, target);
            if (rel.startsWith("..")) continue;
            rawLinks.push({ fromPath: fp, toPath: target, label });
        }
    }

    // Build edges
    const edges = [];
    const inboundCount = new Map();
    const outboundCount = new Map();
    for (const n of nodes.values()) {
        inboundCount.set(n.id, 0);
        outboundCount.set(n.id, 0);
    }

    for (const { fromPath, toPath, label } of rawLinks) {
        const fromNode = nodes.get(fromPath);
        const toNode = nodes.get(toPath);
        const broken = !toNode;

        // Structural file source (index.md, log.md): no concept fromNode.
        // Their links count as inbound credit for target concepts without
        // adding a visible graph edge, preventing false orphan marking.
        if (!fromNode) {
            if (!broken) {
                inboundCount.set(toNode.id, (inboundCount.get(toNode.id) || 0) + 1);
            }
            continue;
        }

        edges.push({
            from: fromNode.id,
            to: toNode ? toNode.id : relative(wikiRoot, toPath),
            label,
            broken,
        });

        if (!broken) {
            outboundCount.set(fromNode.id, (outboundCount.get(fromNode.id) || 0) + 1);
            inboundCount.set(toNode.id, (inboundCount.get(toNode.id) || 0) + 1);
        }
    }

    // Mark orphans: concepts with no inbound and no outbound edges
    for (const node of nodes.values()) {
        const inb = inboundCount.get(node.id) || 0;
        const out = outboundCount.get(node.id) || 0;
        node.isOrphan = inb === 0 && out === 0;
        node.inboundCount = inb;
        node.outboundCount = out;
    }

    return { nodes: [...nodes.values()], edges };
}

// ---------------------------------------------------------------------------
// Filter engine (view-level; does NOT re-exclude archived -- that is
// handled at build time by buildGraph's includeArchived parameter)
// ---------------------------------------------------------------------------

export function applyFilters(graph, filters) {
    const { type, tag, status, directory, onlyOrphans, onlyConnected, text: freeText, _focusId } = filters || {};
    let nodes = graph.nodes;

    // Focus mode: narrow to the focused node and its direct neighbourhood first,
    // then apply any additional user-level filters on top of that subset.
    // Guard against stale _focusId values (e.g. after switching to a new wiki
    // bundle): if the id is missing from the current graph, skip focus mode.
    let focusedId = null;
    if (_focusId) {
        const focusNodeExists = graph.nodes.some((n) => n.id === _focusId);
        if (focusNodeExists) {
            focusedId = _focusId;
            const outboundIds = new Set(graph.edges.filter((e) => e.from === _focusId && !e.broken).map((e) => e.to));
            const inboundIds  = new Set(graph.edges.filter((e) => e.to   === _focusId && !e.broken).map((e) => e.from));
            const neighbourhood = new Set([_focusId, ...outboundIds, ...inboundIds]);
            nodes = nodes.filter((n) => neighbourhood.has(n.id));
        }
        // Stale _focusId: silently skip focus filtering; the full graph is shown.
    }

    if (type) nodes = nodes.filter((n) => n.type === type);
    if (tag) nodes = nodes.filter((n) => n.tags.includes(tag));
    if (status) nodes = nodes.filter((n) => n.status === status);
    if (directory) nodes = nodes.filter((n) => n.path.startsWith(directory));
    if (onlyOrphans) nodes = nodes.filter((n) => n.isOrphan);
    if (onlyConnected) nodes = nodes.filter((n) => !n.isOrphan);
    if (freeText) {
        const q = freeText.toLowerCase();
        nodes = nodes.filter((n) =>
            n.title.toLowerCase().includes(q) ||
            n.description.toLowerCase().includes(q) ||
            n.conceptPath.toLowerCase().includes(q) ||
            n.tags.some((t) => t.toLowerCase().includes(q))
        );
    }

    const nodeIds = new Set(nodes.map((n) => n.id));
    const edges = graph.edges.filter(
        (e) => nodeIds.has(e.from) && (e.broken || nodeIds.has(e.to))
    );

    return { nodes, edges, focusedId };
}

// ---------------------------------------------------------------------------
// Statistics
// ---------------------------------------------------------------------------

export function computeStatistics(graph) {
    const nodeCount = graph.nodes.length;
    const edgeCount = graph.edges.length;
    const orphanCount = graph.nodes.filter((n) => n.isOrphan).length;
    const brokenEdgeCount = graph.edges.filter((e) => e.broken).length;

    const byConnections = [...graph.nodes]
        .sort((a, b) => (b.inboundCount + b.outboundCount) - (a.inboundCount + a.outboundCount))
        .slice(0, 5)
        .map((n) => ({ title: n.title, path: n.conceptPath, inbound: n.inboundCount, outbound: n.outboundCount }));

    return { nodeCount, edgeCount, orphanCount, brokenEdgeCount, mostConnected: byConnections };
}
