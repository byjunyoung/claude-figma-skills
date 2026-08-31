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

**`devStatus` cannot be written through `use_figma`.** The tool's API allowlist rejects the getter and the setter alike — `"devStatus" is not a supported API` — on an Edit seat as much as a View one (checked on a live file, 2026-08-31). Figma's REST API reads the status but has no endpoint that sets it, so there is no way round it from here. `handoff.dev_status` therefore ships off, and the skill hands over links without touching Figma. Where someone turns it on and the write throws, report the error as it came and stop: it is not a permission problem, and no seat and no retry changes it.

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

`handoff.dev_status` — off by default, and the skill hands over links without touching Figma; read the note at the top before turning it on. `handoff.ready_note` — the note on the status. `task_tracker.type` and `task_tracker.ui_section_heading` — where the one line goes; `none` writes none.

## Procedure

### 0. Status route

With `handoff.dev_status` off — the default — steps 1 to 3 still run: the gate and the choice are the point, and the links are what actually gets handed over. The report then says the status was not set, and that it is set by hand in Dev Mode on the section. Nothing about the seat is worth checking here; what blocks the write belongs to the tool, not to the file.

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

Only where `handoff.dev_status` was turned on. Through `use_figma` this throws — see the note at
the top. The call is kept as written because it is correct against the Plugin API, and a runtime
that exposes it needs no other change:

```js
// on each chosen section — never on a frame: a node inside a section that has a status cannot carry one
section.devStatus = { type: "READY_FOR_DEV", description: "{note}" };
```

Then the task-doc line, where configured.

### 6. Read back

Re-read `devStatus` on every section written. The status is not visible in a screenshot, so the check is the property. A mismatch is reported, not retried.

*(Run on a live file with an Edit seat, 2026-08-31: the read and the write are both rejected by `use_figma` with `"devStatus" is not a supported API`. The property is there on the node — the allowlist is what stops it. Recorded so the next reader does not go looking for a permission problem.)*

## Report

```
[handed over]
· 01. Account - Login   Ready for dev · "handoff · 2026-08-29"   https://figma.com/design/…
· 02. Account - Signup  Ready for dev (refreshed)                 https://…

[not offered]
· 03. Account - Recovery   lint: 2 frames outside any section · Recovery-Error missing

[task doc]   {where the line went, or "no tracker configured"}
[status]     not set — mark these by hand in Dev Mode on each section (handoff.dev_status is off)
```

## Constraints

- Writes are the status and the one doc line. Frames, sections, names and positions are never touched
- A section that fails lint is never marked, whoever asks
- Status goes on sections only
- A section already `COMPLETED` is not touched without its own confirmation
- Where the status write is rejected, report the error as it came — do not retry it, and do not read it as a seat problem
