/* =============================================================================
 * audit-struct.js — structural audit (read-only, zero writes)
 *
 * Checks: frame membership · out of bounds · frame overlap · section overlap · naming
 *
 * Usage
 *   1) python3 scripts/lib/resolve-config.py --js <fileKey>   → `const CFG = {...};`
 *   2) prepend that one line to this file and hand it to use_figma
 *   3) for another page, one setCurrentPageAsync line at the top (once per script)
 *
 * Returns: an array of violation strings, or "STRUCT PASS"
 *
 * A null pattern skips that check — it keeps a file with no convention from reporting everything.
 * Coordinate and parent checks always run regardless of config (geometry holds with or without a rule).
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const N = C.naming || {}, P = C.pages || {};

const reOrNull = s => (s ? new RegExp(s) : null);
const anyOf = a => (a && a.length ? new RegExp(a.join("|")) : null);

const NAME_RE = reOrNull(N.frame_pattern);
const SEC_RE = reOrNull(N.section_pattern);
const SEC_EXCLUDE = anyOf(P.exclude_sections);
const LABEL = N.label_prefix || "[label] ";

const skipSection = s => !!(SEC_EXCLUDE && SEC_EXCLUDE.test(s.name));
const isScreen = n => n.type === "FRAME" && !n.name.startsWith(LABEL);
const r = v => Math.round(v);

const issues = [];
const secs = figma.currentPage.children.filter(c => c.type === "SECTION");

// A screen frame sitting directly on the page = the absorb step was missed.
// clone() and createFrame default their parent to currentPage, so anything not absorbed leaks out here.
for (const f of figma.currentPage.children)
  if (isScreen(f))
    issues.push(`[membership] directly on page (not absorbed into a section): ${f.name} @abs ${r(f.x)},${r(f.y)}`);

for (const s of secs) {
  if (skipSection(s)) continue;
  const frames = s.children.filter(isScreen);

  for (const f of frames) {
    // Out of bounds — a section child's x/y is relative to the section.
    // Write an absolute coordinate there and the frame shoots outside the section.
    if (f.x < 0 || f.y < 0 || f.x + f.width > s.width || f.y + f.height > s.height)
      issues.push(`[bounds] ${s.name} / ${f.name} outside (rel ${r(f.x)},${r(f.y)} ${r(f.width)}x${r(f.height)} vs section ${r(s.width)}x${r(s.height)})`);
    if (NAME_RE && !NAME_RE.test(f.name))
      issues.push(`[naming] ${s.name} / ${f.name} (pattern mismatch)`);
  }

  for (let i = 0; i < frames.length; i++)
    for (let j = i + 1; j < frames.length; j++) {
      const a = frames[i], b = frames[j];
      if (a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y)
        issues.push(`[frame overlap] ${s.name}: ${a.name} ∩ ${b.name}`);
    }

  if (SEC_RE && !SEC_RE.test(s.name))
    issues.push(`[naming] section ${s.name} (pattern mismatch)`);
}

// Section overlap — an excluded section on either side is dropped from the check
for (let i = 0; i < secs.length; i++)
  for (let j = i + 1; j < secs.length; j++) {
    const a = secs[i], b = secs[j];
    if (skipSection(a) || skipSection(b)) continue;
    if (a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y)
      issues.push(`[section overlap] ${a.name} ∩ ${b.name}`);
  }

// ── Ordering mismatch — does the NN. number agree with the canvas order (row-major) ──
// Protected number ranges are never reassigned, so they are not checked either.
const BUCKET = (C.layout || {}).row_bucket || 1000;
const PROT = P.protected_numbers || [];
const numbered = secs
  .filter(s => !skipSection(s) && /^\d+\./.test(s.name) && !PROT.some(p => s.name.startsWith(p)))
  .sort((a, b) => (Math.round(a.y / BUCKET) - Math.round(b.y / BUCKET)) || (a.x - b.x));
numbered.forEach((s, i) => {
  const want = String(i + 1).padStart(2, "0");
  const have = s.name.match(/^(\d+)\./)[1];
  if (have !== want) issues.push(`[order] ${s.name} → ${want}. (${i + 1} on canvas)`);
});

// ── Split state variants — are one screen's variants broken apart within a column ──
// A transition result (a modal, a dialog) wedged between the parent screen and its variant
// gets crossed by the [state] dashed line, which is straight. Catching it at the placement
// stage is what keeps the arrow stage clean.
const screenOf = n => n.replace(/-[^-]+$/, "");     // [screen name] with the trailing suffix removed
for (const s of secs) {
  if (skipSection(s)) continue;
  const frames = s.children.filter(isScreen)
    .map(f => ({ name: f.name, screen: screenOf(f.name), x: f.x, y: f.y, b: f.y + f.height }));
  const byScreen = {};
  for (const f of frames) (byScreen[f.screen] = byScreen[f.screen] || []).push(f);
  for (const [screen, group] of Object.entries(byScreen)) {
    if (group.length < 2) continue;
    // Only compare within one column (close in x) — a different column is not a [state] target at all
    const cols = {};
    for (const f of group) { const k = Math.round(f.x / 8); (cols[k] = cols[k] || []).push(f); }
    for (const col of Object.values(cols)) {
      if (col.length < 2) continue;
      col.sort((a, b) => a.y - b.y);
      for (let i = 1; i < col.length; i++) {
        const top = col[i - 1].b, bot = col[i].y;
        const intruder = frames.find(o =>
          o.screen !== screen && Math.abs(o.x - col[i].x) < 8 && o.y >= top && o.y < bot);
        if (intruder)
          issues.push(`[split state] ${s.name}: ${intruder.name} is wedged between ${col[i - 1].name} and ${col[i].name}`);
      }
    }
  }
}

return issues.length ? issues : "STRUCT PASS";
