// test_graph_builder.mjs -- functional regression test for archived concept exclusion.
//
// Imports directly from graph.mjs (no SDK dependency) to test pure graph logic.
// Run with: node packages/karpathy-wiki/tests/unit/test_graph_builder.mjs
//
// Exit 0 = all assertions passed. Exit 1 = at least one failure.

import { buildGraph, computeStatistics, applyFilters } from "../../.apm/extensions/knowledge-graph/graph.mjs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { mkdtempSync, mkdirSync, writeFileSync, symlinkSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURE_BUNDLE = resolve(__dirname, "../fixtures/archived-bundle");

let failures = 0;

function assert(condition, message) {
    if (!condition) {
        console.error(`  FAIL: ${message}`);
        failures++;
    } else {
        console.log(`  PASS: ${message}`);
    }
}

// ---------------------------------------------------------------------------
// Test 1: Archived concept absent from default graph
// ---------------------------------------------------------------------------

console.log("\n[1] buildGraph (default: includeArchived=false)");
const defaultGraph = buildGraph(FIXTURE_BUNDLE);

assert(
    defaultGraph.nodes.some((n) => n.id === "active-concept"),
    "Active concept (stable) is present in default graph"
);
assert(
    defaultGraph.nodes.some((n) => n.id === "linked-concept"),
    "Linked concept (stable) is present in default graph"
);
assert(
    !defaultGraph.nodes.some((n) => n.id === "archived-concept"),
    "Archived concept is ABSENT from default graph"
);
assert(
    defaultGraph.nodes.length === 2,
    `Default graph has exactly 2 nodes (got ${defaultGraph.nodes.length})`
);

// ---------------------------------------------------------------------------
// Test 2: Archived concept absent from default graph statistics
// ---------------------------------------------------------------------------

console.log("\n[2] Statistics exclude archived concept");
const nodeCount = defaultGraph.nodes.length;
assert(
    nodeCount === 2,
    `nodeCount is 2 (active + linked), not including archived (got ${nodeCount})`
);
const archivedInOrphans = defaultGraph.nodes.filter((n) => n.isOrphan).some((n) => n.id === "archived-concept");
assert(
    !archivedInOrphans,
    "Archived concept does not appear in orphan list"
);

// ---------------------------------------------------------------------------
// Test 3: Edge from linked -> archived is SILENTLY OMITTED (not broken warning)
// ---------------------------------------------------------------------------

console.log("\n[3] Edge to archived concept is absent in default graph");
// Check by node ID (archived concept id from frontmatter)
const archiveEdgeById = defaultGraph.edges.find((e) => e.to === "archived-concept");
assert(
    archiveEdgeById === undefined,
    "No edge references the archived concept by node id in the default graph"
);
// Also check by path string -- previously broken edges used path strings as `to`.
// This confirms the edge is fully omitted, not just masked.
const archiveEdgeByPath = defaultGraph.edges.find(
    (e) => typeof e.to === "string" && e.to.includes("archived")
);
assert(
    archiveEdgeByPath === undefined,
    "No broken-link edge with archived-concept path exists in the default graph"
);
// Confirm zero broken edges exist at all in the default graph (no spurious warnings).
const anyBrokenEdge = defaultGraph.edges.find((e) => e.broken);
assert(
    anyBrokenEdge === undefined,
    "Default graph contains zero broken-link edges (archived links are omitted, not broken)"
);

// ---------------------------------------------------------------------------
// Test 4: Archived concept present when includeArchived=true
// ---------------------------------------------------------------------------

console.log("\n[4] buildGraph({ includeArchived: true })");
const fullGraph = buildGraph(FIXTURE_BUNDLE, { includeArchived: true });

assert(
    fullGraph.nodes.some((n) => n.id === "archived-concept"),
    "Archived concept IS present when includeArchived=true"
);
assert(
    fullGraph.nodes.length === 3,
    `Full graph has 3 nodes when includeArchived=true (got ${fullGraph.nodes.length})`
);

// ---------------------------------------------------------------------------
// Test 5: Edge from linked -> archived is valid in full graph
// ---------------------------------------------------------------------------

console.log("\n[5] Edge to archived concept is present (non-broken) in full graph");
const archiveEdgeFull = fullGraph.edges.find(
    (e) => e.to === "archived-concept" && !e.broken
);
assert(
    archiveEdgeFull !== undefined,
    "linked-concept -> archived-concept edge is present and non-broken in full graph"
);

// ---------------------------------------------------------------------------
// Test 6: Structural file links (index.md) still count as inbound credit
// ---------------------------------------------------------------------------

console.log("\n[6] Structural file link counts as inbound credit (no false orphan)");
// wiki/index.md links to concepts/active.md, so active-concept should not be orphaned
const activeConcept = defaultGraph.nodes.find((n) => n.id === "active-concept");
assert(
    activeConcept !== undefined,
    "active-concept node found"
);
// active-concept is linked from index.md AND links to linked-concept
// so it has outbound edges; it should not be an orphan
assert(
    activeConcept && !activeConcept.isOrphan,
    "active-concept is not an orphan (has inbound from index.md and outbound to linked)"
);

// ---------------------------------------------------------------------------
// Test 7a: computeStatistics excludes archived from counts
// ---------------------------------------------------------------------------

console.log("\n[7a] computeStatistics excludes archived from node/edge/orphan counts");
const defaultStats = computeStatistics(defaultGraph);
assert(
    defaultStats.nodeCount === 2,
    `computeStatistics.nodeCount is 2 (not 3) -- archived excluded (got ${defaultStats.nodeCount})`
);
assert(
    defaultStats.mostConnected.every((c) => c.path !== "archived"),
    "archived concept does not appear in mostConnected list"
);

// ---------------------------------------------------------------------------
// Test 7b: Search (simulated) does not surface archived concept
// ---------------------------------------------------------------------------

console.log("\n[7b] Simulated search does not surface archived concept");
const q = "archived";
const searchResults = defaultGraph.nodes.filter((n) =>
    n.title.toLowerCase().includes(q) ||
    (n.description && n.description.toLowerCase().includes(q)) ||
    n.conceptPath.toLowerCase().includes(q) ||
    n.tags.some((t) => t.toLowerCase().includes(q))
);
assert(
    searchResults.length === 0,
    `Search for "${q}" returns 0 results from default graph (got ${searchResults.length})`
);

// ---------------------------------------------------------------------------
// Test 7c: Focus lookup does not find archived concept by path
// ---------------------------------------------------------------------------

console.log("\n[7c] Focus lookup on archived concept path returns undefined from default graph");
const focusTarget = defaultGraph.nodes.find((n) => n.conceptPath === "archived");
assert(
    focusTarget === undefined,
    "focus_node('archived') finds nothing in default graph -- archived not a node"
);

// ---------------------------------------------------------------------------
// Test 7d: computeStatistics with includeArchived:true shows all 3 nodes
// ---------------------------------------------------------------------------

console.log("\n[7d] computeStatistics with includeArchived:true includes archived");
const fullStats = computeStatistics(fullGraph);
assert(
    fullStats.nodeCount === 3,
    `computeStatistics.nodeCount is 3 when includeArchived=true (got ${fullStats.nodeCount})`
);
assert(
    fullGraph.nodes.some((n) => n.conceptPath === "archived"),
    "archived concept is findable in full graph (includeArchived=true)"
);

// ---------------------------------------------------------------------------
// Test 8: Symlink escaping containment is blocked (regression)
// ---------------------------------------------------------------------------
// Skipped on platforms where symlink creation is genuinely unavailable.

console.log("\n[8] Symlink path traversal is blocked");
{
    let canSymlink = true;
    let tmpDir;
    try {
        tmpDir = mkdtempSync(join(tmpdir(), "kg-symlink-test-"));
        const wikiDir = join(tmpDir, "wiki");
        const conceptsDir = join(wikiDir, "concepts");
        mkdirSync(conceptsDir, { recursive: true });
        writeFileSync(join(tmpDir, "SCHEMA.md"), "# Schema");
        writeFileSync(join(wikiDir, "index.md"), "# Index");
        const sensitiveFile = join(tmpDir, "secret.txt");
        writeFileSync(sensitiveFile, "SENSITIVE");
        symlinkSync(sensitiveFile, join(conceptsDir, "escape.md"));
    } catch {
        canSymlink = false;
    }

    if (!canSymlink) {
        console.log("  SKIP: symlink creation not available on this platform");
    } else {
        const escapeBundleRoot = tmpDir;
        let graph;
        let threw = false;
        try {
            graph = buildGraph(escapeBundleRoot);
        } catch {
            threw = true;
        }
        if (!threw) {
            const hasSensitiveNode = graph.nodes.some(
                (n) => (n.path && n.path.includes("escape")) || n.id === "escape"
            );
            assert(!hasSensitiveNode, "Escaping symlink target is NOT surfaced as a graph node");
        } else {
            assert(threw, "buildGraph threw when bundle contained an escaping symlink");
        }
        try { rmSync(tmpDir, { recursive: true, force: true }); } catch {}
    }
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log(`\n${failures === 0 ? "ALL TESTS PASSED" : `${failures} TEST(S) FAILED`}\n`);
process.exit(failures > 0 ? 1 : 0);
