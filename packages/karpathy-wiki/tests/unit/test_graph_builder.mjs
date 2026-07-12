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
// Test 8: Symlink to sibling-dir file (outside bundle) is blocked
// ---------------------------------------------------------------------------
// The symlink target lives in a SEPARATE temp directory entirely outside the
// bundle root. The target contains valid OKF frontmatter so that omission
// from graph.nodes proves containment rejection, not parse failure.
// containmentCheck is called against conceptsDir (not bundle root) so that
// even a symlink to raw/ (bundle-root sibling of wiki/) is rejected.

console.log("\n[8] Symlink to file outside bundle is blocked");
{
    let canSymlink = true;
    let bundleDir, siblingDir;
    try {
        // Two completely separate temp directories.
        bundleDir = mkdtempSync(join(tmpdir(), "kg-bundle-"));
        siblingDir = mkdtempSync(join(tmpdir(), "kg-sibling-"));

        const wikiDir = join(bundleDir, "wiki");
        const conceptsDir = join(wikiDir, "concepts");
        mkdirSync(conceptsDir, { recursive: true });
        writeFileSync(join(bundleDir, "SCHEMA.md"), "# Schema");
        writeFileSync(join(wikiDir, "index.md"), "# Index");

        // Valid OKF concept file in the sibling dir (OUTSIDE bundle root).
        const validConceptContent = [
            "---",
            "id: escaped-concept",
            "title: Escaped Concept",
            "type: concept",
            "created: 2026-01-01",
            "modified: 2026-01-01",
            "---",
            "",
            "This file is outside the bundle root.",
        ].join("\n");
        const externalFile = join(siblingDir, "escaped-concept.md");
        writeFileSync(externalFile, validConceptContent);

        // Symlink from inside wiki/concepts/ to the external valid file.
        symlinkSync(externalFile, join(conceptsDir, "escape.md"));
    } catch {
        canSymlink = false;
    }

    if (!canSymlink) {
        console.log("  SKIP: symlink creation not available on this platform");
    } else {
        let graph;
        let threw = false;
        try {
            graph = buildGraph(bundleDir);
        } catch {
            threw = true;
        }
        if (threw) {
            assert(true, "buildGraph threw on external symlink (escape rejected)");
        } else {
            // The external concept has valid frontmatter id="escaped-concept".
            // If containment works correctly it must NOT appear as a graph node.
            const hasEscapedNode = graph.nodes.some(
                (n) => n.id === "escaped-concept"
                     || (n.path && n.path.includes("escape"))
            );
            assert(!hasEscapedNode,
                "Symlink to valid external concept is NOT surfaced as a graph node " +
                "(containment checked against conceptsDir, not bundle root)"
            );
        }
        try { rmSync(bundleDir, { recursive: true, force: true }); } catch {}
        try { rmSync(siblingDir, { recursive: true, force: true }); } catch {}
    }
}

// ---------------------------------------------------------------------------
// Test 8b: Symlink to raw/ (bundle-root sibling of wiki/) is also blocked
// ---------------------------------------------------------------------------
// Even though raw/ is inside the bundle root, concept candidates must be
// contained within conceptsDir. A symlink pointing to raw/ must be rejected.

console.log("\n[8b] Symlink to raw/ sibling of wiki/ is also blocked");
{
    let canSymlink = true;
    let bundleDir;
    try {
        bundleDir = mkdtempSync(join(tmpdir(), "kg-raw-symlink-"));
        const wikiDir = join(bundleDir, "wiki");
        const conceptsDir = join(wikiDir, "concepts");
        const rawDir = join(bundleDir, "raw");
        mkdirSync(conceptsDir, { recursive: true });
        mkdirSync(rawDir, { recursive: true });
        writeFileSync(join(bundleDir, "SCHEMA.md"), "# Schema");
        writeFileSync(join(wikiDir, "index.md"), "# Index");

        // Valid concept file in raw/ (inside bundle but outside wiki/concepts/).
        const validConcept = [
            "---", "id: raw-concept", "title: Raw Concept", "type: concept",
            "created: 2026-01-01", "modified: 2026-01-01", "---", "",
        ].join("\n");
        writeFileSync(join(rawDir, "raw-concept.md"), validConcept);
        // Symlink from concepts/ into raw/.
        symlinkSync(join(rawDir, "raw-concept.md"), join(conceptsDir, "via-raw.md"));
    } catch {
        canSymlink = false;
    }

    if (!canSymlink) {
        console.log("  SKIP: symlink creation not available on this platform");
    } else {
        let graph;
        let threw = false;
        try { graph = buildGraph(bundleDir); } catch { threw = true; }
        if (threw) {
            assert(true, "buildGraph threw on raw/ symlink (escape rejected)");
        } else {
            const hasRawNode = graph.nodes.some((n) => n.id === "raw-concept");
            assert(!hasRawNode,
                "Symlink from concepts/ to raw/ is NOT surfaced as a graph node " +
                "(conceptsDir containment prevents raw/ sibling escapes)"
            );
        }
        try { rmSync(bundleDir, { recursive: true, force: true }); } catch {}
    }
}

// ---------------------------------------------------------------------------
// Test 9: Dangling symlink is NOT surfaced (no realpathSync fallback)
// ---------------------------------------------------------------------------
// Old code: realpathSync failure fell back to the symlink path itself.
// The symlink path IS inside wiki/, so containmentCheck passed (false pass).
// New code: realpathSync failure immediately throws GraphError -- dangling
// symlink is explicitly rejected by containmentCheck, not just by readFileSync.
//
// Either way, the dangling file must not appear as a graph node.

console.log("\n[9] Dangling symlink is NOT surfaced in graph");
{
    let canSymlink = true;
    let tmpDir;
    try {
        tmpDir = mkdtempSync(join(tmpdir(), "kg-dangling-test-"));
        const wikiDir = join(tmpDir, "wiki");
        const conceptsDir = join(wikiDir, "concepts");
        mkdirSync(conceptsDir, { recursive: true });
        writeFileSync(join(tmpDir, "SCHEMA.md"), "# Schema");
        writeFileSync(join(wikiDir, "index.md"), "# Index");
        // Dangling symlink: points to a non-existent file outside the bundle.
        symlinkSync("/non-existent-path/secret.txt", join(conceptsDir, "dangling.md"));
    } catch {
        canSymlink = false;
    }

    if (!canSymlink) {
        console.log("  SKIP: symlink creation not available on this platform");
    } else {
        let graph;
        let threw = false;
        try {
            graph = buildGraph(tmpDir);
        } catch {
            threw = true;
        }
        if (threw) {
            assert(true, "buildGraph threw on dangling symlink (explicitly rejected)");
        } else {
            const hasDanglingNode = graph.nodes.some(
                (n) => (n.path && n.path.includes("dangling")) || n.id === "dangling"
            );
            assert(!hasDanglingNode, "Dangling symlink is NOT surfaced as a graph node");
        }
        try { rmSync(tmpDir, { recursive: true, force: true }); } catch {}
    }
}

// ---------------------------------------------------------------------------
// Test 10: All 7 graph functions execute without throwing on valid fixture
// ---------------------------------------------------------------------------

console.log("\n[10] All 7 graph functions execute on the fixture bundle");
{
    const graph = buildGraph(FIXTURE_BUNDLE);
    let ok = true;

    // 1. buildGraph (already called above) -- tested implicitly
    // 2. computeStatistics
    try {
        const stats = computeStatistics(graph);
        assert(typeof stats.nodeCount === "number", "computeStatistics returns nodeCount");
    } catch (e) { assert(false, `computeStatistics threw: ${e.message}`); }

    // 3. applyFilters -- no filter (identity)
    try {
        const filtered = applyFilters(graph, {});
        assert(Array.isArray(filtered.nodes), "applyFilters returns nodes array");
    } catch (e) { assert(false, `applyFilters({}) threw: ${e.message}`); }

    // 4. applyFilters -- type filter
    try {
        const filtered = applyFilters(graph, { type: "concept" });
        assert(Array.isArray(filtered.nodes), "applyFilters with type filter returns nodes");
    } catch (e) { assert(false, `applyFilters({type}) threw: ${e.message}`); }

    // 5. applyFilters -- text search
    try {
        const filtered = applyFilters(graph, { text: "example" });
        assert(Array.isArray(filtered.nodes), "applyFilters with text filter returns nodes");
    } catch (e) { assert(false, `applyFilters({text}) threw: ${e.message}`); }

    // 6. applyFilters -- orphan filter
    try {
        const filtered = applyFilters(graph, { onlyOrphans: true });
        assert(Array.isArray(filtered.nodes), "applyFilters with onlyOrphans returns nodes");
    } catch (e) { assert(false, `applyFilters({onlyOrphans}) threw: ${e.message}`); }

    // 7. buildGraph -- includeArchived opt-in
    try {
        const fullGraph = buildGraph(FIXTURE_BUNDLE, { includeArchived: true });
        assert(typeof fullGraph.nodes === "object", "buildGraph(includeArchived:true) returns nodes");
    } catch (e) { assert(false, `buildGraph(includeArchived:true) threw: ${e.message}`); }
}

// ---------------------------------------------------------------------------
// Test 11: Multi-instance isolation -- two separate buildGraph calls are independent
// ---------------------------------------------------------------------------

console.log("\n[11] Multi-instance isolation -- separate graph state per call");
{
    const graphA = buildGraph(FIXTURE_BUNDLE);
    const graphB = buildGraph(FIXTURE_BUNDLE);

    // Mutating a filter on graphA's result must not affect graphB
    const filteredA = applyFilters(graphA, { onlyOrphans: true });
    const filteredB = applyFilters(graphB, {});

    assert(
        filteredA.nodes.length <= filteredB.nodes.length,
        "Instance A filter (onlyOrphans) does not bleed into instance B (no filter)"
    );

    // Modifying graphA directly does not affect graphB
    const originalNodeCount = graphB.nodes.length;
    graphA.nodes = [];
    assert(
        graphB.nodes.length === originalNodeCount,
        "Clearing instance A nodes does not affect instance B node count"
    );
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log(`\n${failures === 0 ? "ALL TESTS PASSED" : `${failures} TEST(S) FAILED`}\n`);
process.exit(failures > 0 ? 1 : 0);
