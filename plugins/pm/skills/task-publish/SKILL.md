---
name: task-publish
description: Files one task record as a ticket in the engineering tracker, or updates the ticket already there. The ticket carries a summary and links rather than a copy of the body, so the record stays the single place anything is edited. Missing fields are filled by one grouped interview, the parent is resolved before writing, and the link back into the record is what matching relies on afterwards. Reconciling many tasks at once belongs to /pm:task-sync. Triggers - "/pm:task-publish", "file this task as a ticket", "update the GitHub task", "깃헙에 일감 등록해줘", "이 일감 티켓 만들어줘", "티켓 갱신해줘".
allowed-tools: AskUserQuestion, Bash, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-update-page, mcp__plugin_github_github__issue_read, mcp__plugin_github_github__issue_write, mcp__plugin_github_github__add_issue_comment, mcp__plugin_github_github__sub_issue_write, mcp__plugin_github_github__list_issues, mcp__plugin_github_github__search_issues
---

# task-publish — one task record into one tracker ticket

Files a single task record as a ticket in the engineering tracker, or updates the one already there.

**The ticket carries a summary and links, not a copy of the body.** Detail — the spec, the design, the description of what changed — stays in the record, and the ticket points at it. Two copies means one gets edited and they drift; there is also no reliable way to carry embedded images across, so a copied body arrives broken.

## What decides where things go

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml --need task.record.ref,task.link_property
```

With `mirror.type` anything but `none`, `task.mirror.ref` belongs on that list too. A `null` named on stderr is a config gap, not a tracker problem — `/pm:setup` writes it. Stop on it rather than interviewing for the value here.

`task.record` is where the task lives, `task.mirror` is the tracker it is filed into. **With `mirror.type: none` this skill has nothing to do** — say so and stop, rather than inventing a destination.

**Matching runs on `task.link_property` alone** — the property on the record that holds the ticket's url. A back-link written in the ticket body is for a human to click, never for matching: it can point at a source that was already discarded, which is how duplicates and resurrected tickets happen.

## When NOT to invoke

- Filling the record's context table → `/pm:task-draft`
- Reconciling many tasks across both sides → `/pm:task-sync`
- Writing the requirements → `/pm:prd`

## Procedure

### 0. Take the record

Take the record's URL from the argument, or ask for it.

### 1. Read the record (zero writes)

Read its properties — title, project, group, priority, assignee, status, schedule, the link property, and any link to a published spec.

**Read the body too.** The change summary, the design links, and the spec links inside it are the defaults the interview starts from. Reading them first is what keeps the interview short.

Then branch:

- **The project has no entry in `task.label_map.project`** → stop. Say that this project is not mirrored. Do not guess a label
- **The link property is empty** → create
- **The link property is filled** → update

### 2. Interview, once (grouped)

Ask everything missing in one `AskUserQuestion` round. **Never ask for what the record already answers.**

| Item | Where it comes from |
|---|---|
| Summary | The record's title by default, with an option to type another |
| What changed | The body's change summary if it has one. Empty → ask, and write it back in step 8 |
| Spec link | The record's spec property if set. Empty → ask, and store it back so the next run has it |
| Design link | The design section of the body, else ask |
| Other links | Ask — dependencies, policies |
| Definition of done | `TBD` by default, with an option to type one |
| Version | Only where `task.hierarchy.milestone_on` is not `none`, and only for a project listed in `milestone_projects` |

Project, group, priority, assignee and dates come from the record and are not asked. Where the record has several assignees and the tracker takes one, ask which.

### 3. Resolve the parent

Only where `task.hierarchy.parent_kind` is set. With it `null`, tasks are a flat list — skip to step 4.

Search the mirror for open parents **of this task's project**, and read their titles to find
the one this task belongs under.

Do not filter the candidates by group. The group is a hint, not a key: a team that adopted a
`[{parent_kind}] [{group}] ...` title convention partway through has older parents without the
bracket, and those are exactly the long-running ones a new task most often belongs to. Filtering
on the group hides them, and the run then concludes there is no parent and offers to create a
duplicate of one that already exists.

- **One obvious match** → use it, and say which, so a wrong read is visible
- **None** → ask: create one / name an existing one / stop. Creating one is its own preview → go
- **Several plausible** → let the user pick. Do not break the tie yourself

A newly created parent is titled by `task.hierarchy.parent_title` and carries whatever `task.mirror_extras` specifies for its type and board placement. Where the project uses milestones, the milestone is set **on the parent** — see step 7.

### 4. Assemble the ticket body

Sections come from `task.ticket.sections`; the link rows from `task.ticket.link_rows`. A row whose value is missing is dropped rather than written as an empty bullet.

```
> Parent: #{parent}

### Project / version
- Project: {project label}
- Version: {milestone, or "Not set"}

### Summary
{from the interview — the record's title by default}

### Links
- Spec: {spec url, or "TBD"}
- Design: {design url}            ← dropped when absent
- Change summary: {record url}
{any other links from the interview}

### Definition of done
{from the interview, or "TBD"}

## Schedule
- Start: {date, or "Not set"}
- End: {date, or "Not set"}
```

The record link under Links is **for a person to click**. It is not what matching reads.

### 5. Preview → "go"

```
[ticket preview]
Repo / board : {mirror.ref}
Parent       : #{n} {title}
Title        : {task.ticket.title, filled in}
Labels       : {default_labels} + {project label} + {priority label}
Assignee     : {mapped username}

--- body ---
{step 4 in full}
--- end ---

{if the interview produced a new change summary:}
[to be written back into the record]
{the text}

shall I proceed? (go / changes)
```

**No external write happens before "go"** — not the ticket, not the write-back into the record. Both are in this one preview because both are writes.

**Title**: `task.ticket.title` as configured. Do not append your own qualifiers; add a short one only where the task's name alone leaves the kind of work unclear.

### 6. Create the ticket

Create it with the assembled title, body, labels and assignee.

**A milestone is not set on the task** where `task.hierarchy.milestone_on` is `parent` — that level owns it.

### 7. Attach it

- Link it under the parent, where the tracker has a parent-child relation
- Add it to the board named in `task.mirror_extras`, capturing the returned item id
- Set the board's custom fields from `task.mirror_extras` — project field, dates
- Dates go **on the task only**. A parent's schedule is managed separately and is never touched here
- **Seat it in the right column.** Where `task.status_map` has an entry for the record's current
  status, set the board's status field to it. Without an entry, leave the board's own default
  alone rather than guessing a column

Seating is not ownership. `task.field_owner.status` still says which side wins afterwards — with
it `mirror`, this is the only time this skill touches the status, and every later move belongs to
whoever runs the board. The reason to seat it at all is that a task whose spec is already written
lands in the backlog column otherwise, and the mirror's readers act on that.

Anything under `task.mirror_extras` is read verbatim. This skill does not interpret it, which is what lets a tracker it has never seen still work.

**The calls themselves live per tracker**, not in this document. Two copies of a command means one gets fixed. Read the mirror's adapter before this step and the record's before step 8:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind trackers --type {task.mirror.type} --role mirror
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind trackers --type {task.record.type} --role record
```

It prints the file to read — the bundled one, or yours from `adapters.dirs` where you drafted one. **Exit 3 means no adapter exists for that type.** Stop and say so; `/pm:setup` drafts one from the tools connected on this machine. Do not improvise the calls. **Exit 4 means the adapter exists but answers for the other side** — a mirror-only file asked for the record, say. Stop the same way; 3b drafts the side that is missing. Say what it means in the person's words — "this tool isn't supported yet; `/pm:setup` can add it from what's connected here" — never the exit code or the file path.

### 8. Write back into the record

- **The link property** — always. This is what every later run matches on
- **The spec link** — only where the interview produced a new one
- **The change summary** — only where the interview produced a new one. Where the record already had it, leave it alone. Append rather than replace, so the history survives: one dated line under what is already there

### 9. Report

```
[done]
Ticket        : {url}
Parent        : #{n}
Link property : written
{spec link stored, where applicable}
{change summary written, where applicable}
```

---

## The update path

Taken when the link property was already filled.

1. Read the current ticket body
2. Steps 2–4 as before. **Skip resolving the parent** — it is already attached. Ask whether to replace the whole body or only the summary and links sections. The change summary is the point of most updates: read it from the record, and ask only when it is new
3. Preview → go → edit the ticket, keeping the record link row intact
4. Write back into the record — the spec link only where newly given; the link property is already there. Append the new change summary under the existing one

---

## Constraints

- **Never invent a mapping.** A project, priority or assignee with no entry in the config stops the run with a message. A wrong label is harder to find later than a missing ticket
- **Read the tracker's current schema before writing** rather than trusting ids pinned in the config — options get renamed
- **Every external write waits for "go"**, including the write-back into the record
- **Never copy the body across.** The record stays the single source; the ticket links to it
- Verify after writing, and report what was actually written rather than what was intended
