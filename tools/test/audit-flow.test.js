/* Regression fixtures for audit-flow.js — the geometry the report is built on.
 *
 *     node --test tools/test/
 *
 * The script runs inside the Figma sandbox against `CFG` and `figma` globals and returns
 * its findings, so a test supplies both and reads the return value. Only two lines touch
 * `figma` (the page and its children), which is what makes this possible without a sandbox.
 *
 * Every fixture is the same two screens 100px apart. What changes is the one arrow between
 * them — because the point of these checks is that arrows which look identical at working
 * zoom are not, and a distance-only check would pass most of them.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = readFileSync(
  join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "audit-flow.js"),
  "utf8"
);

const CFG = {
  naming: {
    arrow_delimiter: " --> ",
    state_chain_delimiter: " ~ ",
    label_prefix: "[label] ",
    state_chain_prefix: "[state] ",
  },
  arrows: { audit: { edge_tolerance: 2, gap_range: [9, 15], label_clear: 30 } },
  pages: {},
};

const frame = (name, x, y) => ({ type: "FRAME", name, x, y, width: 100, height: 100 });
const arrow = (name, ...pts) => ({
  type: "VECTOR", name, x: 0, y: 0,
  vectorNetwork: { vertices: pts.map(([x, y]) => ({ x, y })) },
});

// One section at the origin, so frame coordinates are already absolute.
const run = (children) =>
  new Function("CFG", "figma", SRC)(CFG, {
    currentPage: { name: "[UI] Fixture", children: [{ type: "SECTION", name: "S1", x: 0, y: 0, children }] },
  });

// A: x 0–100. B: x 200–300. Both y 0–100.
const A = frame("a_default", 0, 0);
const B = frame("b_default", 200, 0);

// Leaves A's right edge, ends 10px short of B's left edge, final segment perpendicular to it.
const GOOD = ["a_default --> b_default", [100, 50], [150, 50], [190, 50]];

test("a well-formed arrow reports nothing", () => {
  assert.strictEqual(run([A, B, arrow(...GOOD)]), "FLOW PASS");
});

test("target gap outside the configured range is reported", () => {
  // Stops 30px short — still visually near the frame, outside gap_range [9, 15].
  const out = run([A, B, arrow("a_default --> b_default", [100, 50], [150, 50], [170, 50])]);
  assert.ok(out.some((i) => /target gap 30px/.test(i)), out);
});

test("a start that is off the source edge is reported", () => {
  // Begins 20px inside A rather than on its edge.
  const out = run([A, B, arrow("a_default --> b_default", [80, 50], [150, 50], [190, 50])]);
  assert.ok(out.some((i) => /start off the edge by 20px/.test(i)), out);
});

test("an arrowhead 10px away still fails when its last segment runs parallel to the edge", () => {
  // This is the case distance alone cannot catch: the head sits inside gap_range, but the
  // final segment is vertical against a vertical edge, so it points at empty space beside B.
  const out = run([A, B, arrow("a_default --> b_default", [100, 50], [190, 20], [190, 50])]);
  assert.ok(out.some((i) => /arrowhead parallel to the target edge/.test(i)), out);
  assert.ok(!out.some((i) => /target gap/.test(i)), "the gap itself is within range");
});

test("a segment crossing an unrelated frame is reported", () => {
  // C sits between A and B, directly under the line.
  const C = frame("c_default", 130, 30);
  C.width = 40; C.height = 40;
  const out = run([A, B, C, arrow(...GOOD), arrow("c_default --> b_default", [170, 70], [200, 70], [190, 50])]);
  assert.ok(out.some((i) => /passes through c_default/.test(i)), out);
});

test("a frame on no flow at all is reported as a coverage orphan", () => {
  const out = run([A, B, frame("d_default", 0, 300), arrow(...GOOD)]);
  assert.ok(out.some((i) => /orphan frame .*d_default/.test(i)), out);
});

test("a [state] link must be a two-vertex vertical line", () => {
  const D = frame("a_empty", 0, 200);
  // Elbowed rather than straight — an elbow can curl over its own endpoints and slip
  // past the pass-through check, so shape is enforced before position.
  const out = run([A, B, D, arrow(...GOOD), arrow("[state] a_default ~ a_empty", [50, 100], [80, 150], [50, 200])]);
  assert.ok(out.some((i) => /not vertical \/ elbowed/.test(i)), out);
});

test("a straight [state] link between the same two frames reports nothing", () => {
  const D = frame("a_empty", 0, 200);
  assert.strictEqual(
    run([A, B, D, arrow(...GOOD), arrow("[state] a_default ~ a_empty", [50, 100], [50, 200])]),
    "FLOW PASS"
  );
});
