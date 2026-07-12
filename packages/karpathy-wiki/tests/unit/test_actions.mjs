// test_actions.mjs -- Seven-action + multi-instance isolation tests for the
// knowledge-graph canvas action layer (SDK-independent via actions.mjs).
//
// Run with: node packages/karpathy-wiki/tests/unit/test_actions.mjs
// Exit 0 = all assertions passed. Exit 1 = at least one failure.

import { makeActions, ActionError } from "../../.apm/extensions/knowledge-graph/actions.mjs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURE = resolve(__dirname, "../fixtures/archived-bundle");

let failures = 0;
function assert(cond, msg) {
    if (!cond) { console.error(`  FAIL: ${msg}`); failures++; }
    else { console.log(`  PASS: ${msg}`); }
}

// ---------------------------------------------------------------------------
// Action 1: open_graph
// ---------------------------------------------------------------------------
console.log("\n[A1] open_graph -- opens instance and returns stats");
{
    const { instances, dispatch } = makeActions();
    const result = await dispatch("open_graph", "inst-A", { wiki_path: FIXTURE });
    assert(result.ok === true, "open_graph returns ok:true");
    assert(typeof result.wikiRoot === "string", "open_graph returns wikiRoot");
    assert(typeof result.nodeCount === "number", "open_graph returns nodeCount");
    assert(typeof result.edgeCount === "number", "open_graph returns edgeCount");
    assert(instances.has("inst-A"), "open_graph stores instance in instances map");
    assert(instances.get("inst-A").graph !== null, "open_graph builds a non-null graph");
}

// ---------------------------------------------------------------------------
// Action 2: refresh_graph
// ---------------------------------------------------------------------------
console.log("\n[A2] refresh_graph -- rebuilds graph and returns updated stats");
{
    const { dispatch } = makeActions();
    await dispatch("open_graph", "inst-B", { wiki_path: FIXTURE });
    const result = await dispatch("refresh_graph", "inst-B", {});
    assert(result.ok === true, "refresh_graph returns ok:true");
    assert(typeof result.nodeCount === "number", "refresh_graph returns nodeCount");
}

// ---------------------------------------------------------------------------
// Action 3: get_statistics
// ---------------------------------------------------------------------------
console.log("\n[A3] get_statistics -- returns node/edge/orphan counts");
{
    const { dispatch } = makeActions();
    await dispatch("open_graph", "inst-C", { wiki_path: FIXTURE });
    const stats = await dispatch("get_statistics", "inst-C", {});
    assert(typeof stats.nodeCount === "number", "get_statistics returns nodeCount");
    assert(typeof stats.edgeCount === "number", "get_statistics returns edgeCount");
    assert(typeof stats.orphanCount === "number", "get_statistics returns orphanCount");
    assert(Array.isArray(stats.mostConnected), "get_statistics returns mostConnected array");
}

// ---------------------------------------------------------------------------
// Action 4: search_nodes
// ---------------------------------------------------------------------------
console.log("\n[A4] search_nodes -- returns matching nodes");
{
    const { dispatch } = makeActions();
    await dispatch("open_graph", "inst-D", { wiki_path: FIXTURE });
    const result = await dispatch("search_nodes", "inst-D", { query: "concept" });
    assert(typeof result.count === "number", "search_nodes returns count");
    assert(Array.isArray(result.nodes), "search_nodes returns nodes array");
    // Archived concept must not appear in default search
    const archivedInResults = result.nodes.some((n) => n.id === "archived-concept");
    assert(!archivedInResults, "search_nodes does not return archived concepts by default");
}

// ---------------------------------------------------------------------------
// Action 5: set_filter (including includeArchived rebuild)
// ---------------------------------------------------------------------------
console.log("\n[A5] set_filter -- narrows view and triggers rebuild on includeArchived change");
{
    const { instances, dispatch } = makeActions();
    await dispatch("open_graph", "inst-E", { wiki_path: FIXTURE });
    const defaultNodeCount = (await dispatch("get_statistics", "inst-E", {})).nodeCount;

    // Set type filter
    const filtered = await dispatch("set_filter", "inst-E", { type: "concept" });
    assert(filtered.ok === true, "set_filter returns ok:true");
    assert(typeof filtered.visibleNodes === "number", "set_filter returns visibleNodes");

    // Enable includeArchived -- must trigger rebuild
    const withArchived = await dispatch("set_filter", "inst-E", { includeArchived: true });
    assert(withArchived.includeArchived === true, "set_filter sets includeArchived:true on instance");
    const archivedNodeCount = (await dispatch("get_statistics", "inst-E", {})).nodeCount;
    assert(archivedNodeCount > defaultNodeCount, "includeArchived:true increases nodeCount (archived now in graph)");

    // Disable includeArchived -- must trigger rebuild back
    await dispatch("set_filter", "inst-E", { includeArchived: false });
    assert(!instances.get("inst-E").includeArchived, "set_filter resets includeArchived:false on instance");
    const backToDefault = (await dispatch("get_statistics", "inst-E", {})).nodeCount;
    assert(backToDefault === defaultNodeCount, "includeArchived:false restores original nodeCount");
}

// ---------------------------------------------------------------------------
// Action 6: clear_filters (resets all state including includeArchived)
// ---------------------------------------------------------------------------
console.log("\n[A6] clear_filters -- resets filters and includeArchived to defaults");
{
    const { instances, dispatch } = makeActions();
    await dispatch("open_graph", "inst-F", { wiki_path: FIXTURE });
    await dispatch("set_filter", "inst-F", { includeArchived: true, type: "concept" });
    assert(instances.get("inst-F").includeArchived === true, "set_filter applied includeArchived");

    const cleared = await dispatch("clear_filters", "inst-F", {});
    assert(cleared.ok === true, "clear_filters returns ok:true");
    assert(!instances.get("inst-F").includeArchived, "clear_filters resets includeArchived to false");
    assert(Object.keys(instances.get("inst-F").filters).length === 0, "clear_filters empties filters object");
}

// ---------------------------------------------------------------------------
// Action 7: focus_node + stale focus cleared on includeArchived change
// ---------------------------------------------------------------------------
console.log("\n[A7] focus_node -- returns neighbourhood; stale focus cleared on rebuild");
{
    const { instances, dispatch } = makeActions();
    await dispatch("open_graph", "inst-G", { wiki_path: FIXTURE });

    // Focus an active concept
    const focusResult = await dispatch("focus_node", "inst-G", { concept_path: "active" });
    assert(focusResult.found === true, "focus_node finds active-concept");
    assert(typeof focusResult.node.id === "string", "focus_node returns node.id");
    assert(Array.isArray(focusResult.inbound), "focus_node returns inbound array");
    assert(Array.isArray(focusResult.outbound), "focus_node returns outbound array");
    assert(instances.get("inst-G").filters._focusId !== undefined, "focus_node sets _focusId filter");

    // Enable includeArchived -- stale _focusId must be cleared on rebuild
    await dispatch("set_filter", "inst-G", { includeArchived: true });
    assert(instances.get("inst-G").filters._focusId === undefined, "includeArchived rebuild clears stale _focusId");

    // focus_node on archived concept -- only found when includeArchived:true
    const archivedFocus = await dispatch("focus_node", "inst-G", { concept_path: "archived" });
    assert(archivedFocus.found === true, "focus_node finds archived-concept when includeArchived:true");
}

// ---------------------------------------------------------------------------
// Multi-instance isolation: filter/focus/root do not bleed between instances
// ---------------------------------------------------------------------------
console.log("\n[A8] Multi-instance isolation -- two instances share no state");
{
    const { instances, dispatch } = makeActions();
    await dispatch("open_graph", "inst-X", { wiki_path: FIXTURE });
    await dispatch("open_graph", "inst-Y", { wiki_path: FIXTURE });

    // Apply includeArchived + type filter only on inst-X
    await dispatch("set_filter", "inst-X", { includeArchived: true, type: "concept" });
    assert(instances.get("inst-X").includeArchived === true, "inst-X has includeArchived:true");
    assert(!instances.get("inst-Y").includeArchived, "inst-Y is unaffected by inst-X includeArchived");
    assert(Object.keys(instances.get("inst-Y").filters).length === 0, "inst-Y filters empty after inst-X set_filter");

    // Focus a node on inst-X only
    await dispatch("focus_node", "inst-X", { concept_path: "active" });
    assert(instances.get("inst-X").filters._focusId !== undefined, "inst-X has _focusId set");
    assert(instances.get("inst-Y").filters._focusId === undefined, "inst-Y has no _focusId (isolation)");

    // clear_filters on inst-X must not affect inst-Y
    await dispatch("clear_filters", "inst-X", {});
    assert(Object.keys(instances.get("inst-X").filters).length === 0, "inst-X cleared");
    // (inst-Y was already empty, still is)
    assert(instances.get("inst-Y").graph !== null, "inst-Y graph survives inst-X clear_filters");
}

// ---------------------------------------------------------------------------
// Error: dispatch on unopened instance throws ActionError
// ---------------------------------------------------------------------------
console.log("\n[A9] Error handling -- dispatch on unopened instance throws ActionError");
{
    const { dispatch } = makeActions();
    let threw = false;
    try {
        await dispatch("get_statistics", "never-opened", {});
    } catch (e) {
        threw = true;
        assert(e.code === "not_open", "ActionError has code:not_open for unopened instance");
    }
    assert(threw, "dispatch on unopened instance throws ActionError");
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
console.log(`\n${failures === 0 ? "ALL TESTS PASSED" : `${failures} TEST(S) FAILED`}\n`);
process.exit(failures > 0 ? 1 : 0);
