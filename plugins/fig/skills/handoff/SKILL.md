---
name: handoff
description: Hands finished sections to engineering. Runs /fig:lint as the gate, lets the person pick which passing sections go, marks them Ready for dev in Figma — the status engineering actually sees in Dev Mode — hands over the section links, and writes one line into the task doc where a tracker is configured. Nothing else is touched. Triggers - "/fig:handoff", "hand this off", "mark these ready for dev", "send this to engineering", "개발 넘겨줘", "핸드오프 해줘", "Ready for dev 표시해줘", "이 섹션 개발팀에 넘겨".
allowed-tools: AskUserQuestion, Bash, Read, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__whoami, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-update-page, mcp__plugin_github_github__issue_read, mcp__plugin_github_github__add_issue_comment
---

# fig:handoff — hand finished sections to engineering

The moment a feature's screens, states and arrows are drawn, somebody has to say "this is ready"
where engineering looks. In Figma that place is Dev Mode, and the signal is a section's *Ready
for dev* status. This skill puts it there — and only there, and only on sections that pass the
audit.

**The audit decides, the person chooses, the skill marks.** `/fig:lint` says which sections are
fit to hand over; the person says which of those go now; this skill sets the status, hands over
the links, and leaves one line in the task doc. It draws nothing, moves nothing, renames nothing.

**Prerequisites**: load `figma:figma-use` before calling `use_figma`. Every write goes through
preview → go.

**Seat check before the first write** — call `whoami` once. Where every plan it lists carries `seat: View`, the status cannot be set: hand over the links and say who with an Edit seat sets it. Where the seats are mixed, go ahead — and if the write comes back as a permission error, report the seat table and stop rather than retrying.

## When to invoke

- A feature's screens, states and arrows are drawn and it is time to hand them to engineering
- Something handed over was revised and needs handing over again
- "Which of these sections is actually ready?" — the gate answers that even when nothing is marked

## When NOT to invoke

- Laying the skeleton and stubbing missing states → `/fig:prep`
- Checking rules only → `/fig:lint`
- Marking what changed and writing it up → `/fig:diff`
- Filing the task as a ticket → `/pm:task-publish`
- After release, bringing canonical current and marking sections *Completed* → `/fig:sync`

## Inputs

- `page` (required): the page the sections are on
- `sections` (optional): names or numbers. Omitted, every section on the page that passes the gate is a candidate
- `note` (optional): the note carried on the status. Defaults to `handoff.ready_note`

## Where the rules come from

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --js <fileKey>
```

`handoff.dev_status` — off, and the skill hands over links without touching Figma. `handoff.ready_note` — the note on the status. `task_tracker.type` and `task_tracker.ui_section_heading` — where the one line goes; `none` writes none.

## Procedure

### 0. Seat

`whoami`, as above. On a View seat, steps 1 to 3 still run — the gate and the choice are worth having — and the report says the status was not set and by whom it can be.

### 1. The gate — `/fig:lint` on the page (zero writes)

Call `/fig:lint` (via the Skill tool) on the page. **No audit lives here**; the verdict is lint's alone, and it is the only thing that makes a section a candidate.

- A section that passes is a candidate
- A section that fails is out, with lint's reasons beside its name. It is not offered, and if the person names it anyway, say why it cannot go and leave it out — "hand it over now and fix it later" is what the status is meant to prevent

### 2. What is already there (read-only)

For each candidate read `section.devStatus`:

| Found | Means |
|---|---|
| `null` | never handed over |
| `READY_FOR_DEV` | handed over before — this run refreshes the note |
| `COMPLETED` | engineering shipped it. Handing it over again means it was reopened — ask before touching it, separately from the go |

### 3. Choose

Show the candidates as a table — name, what lint said, current status — and ask which go: all, or some. One question. Sections that failed the gate appear below the table with their reasons, so the person sees why they are not offered.

### 4. Preview → go

One preview with everything this run will do:

- the sections and the note each will carry — `handoff.ready_note` with `{date}` filled in, or the `note` given
- the section links: `https://figma.com/design/{fileKey}/?node-id={section id with : replaced by -}` — the same links `/fig:prep` hands over, because engineering opens sections, not frames
- where `task_tracker.type` is not `none`: the one line that goes into the task doc — the links and "handed over {date}, {n} sections" — under `task_tracker.ui_section_heading`, appended after what is already there, by the method `/fig:diff` uses for that tracker

Then the go.

### 5. Write

```js
// on each chosen section — never on a frame: a node inside a section that has a status cannot carry one
section.devStatus = { type: "READY_FOR_DEV", description: "{note}" };
```

Then the task-doc line, where configured.

### 6. Read back

Re-read `devStatus` on every section written. The status is not visible in a screenshot, so the check is the property. A mismatch is reported, not retried.

*(Setting `devStatus` has not yet been run on a live file — the seat where this skill was written could only view. The first run on an Edit seat verifies it, and removes this note.)*

## Report

```
[handed over]
· 01. Account - Login   Ready for dev · "handoff · 2026-08-29"   https://figma.com/design/…
· 02. Account - Signup  Ready for dev (refreshed)                 https://…

[not offered]
· 03. Account - Recovery   lint: 2 frames outside any section · Recovery-Error missing

[task doc]   {where the line went, or "no tracker configured"}
[status]     set · or: not set — View seat; someone with an Edit seat marks these
```

## Constraints

- Writes are the status and the one doc line. Frames, sections, names and positions are never touched
- A section that fails lint is never marked, whoever asks
- Status goes on sections only
- A section already `COMPLETED` is not touched without its own confirmation
- On a View seat, report — do not retry the write
