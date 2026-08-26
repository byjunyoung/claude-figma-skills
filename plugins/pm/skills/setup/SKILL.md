---
name: setup
description: Reads the schemas of your document tool and your issue tracker and drafts pm-conventions.yaml from them. Property names, select options, labels, board field ids and user mappings are read from the live schema rather than guessed, and the ids nobody can find by hand — board node id, custom field ids, single-select option ids, issue-type ids — are queried for you. Anything the schema does not settle is left null and asked about rather than filled in. Run this first when opening these skills on a new workspace. Triggers - "/pm:setup", "set up the pm config", "read my tracker schema", "pm 설정 만들어줘", "트래커 스키마 읽어줘", "일감 설정 초안".
allowed-tools: AskUserQuestion, Read, Write, Bash, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-search, mcp__claude_ai_Notion__notion-get-users, mcp__plugin_github_github__list_issues, mcp__plugin_github_github__search_issues, mcp__plugin_github_github__issue_read, mcp__plugin_github_github__get_me, mcp__plugin_github_github__list_repository_collaborators
---

# pm:setup — read the schemas, draft the config

The `pm` skills read every value from `pm-conventions.yaml`. This is where that file comes from.

**It reads schemas rather than inferring from samples.** A design file has no schema, so `/fig:setup` has to count occurrences and take the dominant value. A document database and an issue tracker both publish theirs — property names, select options, labels, field ids. So this skill queries, and only interviews for what a schema genuinely cannot answer.

**What it never does is guess.** A value the schema does not settle is written as `null`, and `null` means that check or that step is skipped. Filling a blank with a plausible value is how a config ends up describing a workspace nobody has.

## When to invoke

- Opening these skills on a new workspace, a new company, or a new tracker
- The tracker was restructured — fields renamed, a board rebuilt, options changed
- `/pm:task-publish` stopped with "this project is not mapped"
- You need the board ids for `mirror_extras` and do not want to write GraphQL by hand

## When NOT to invoke

- Drafting a task's context table → `/pm:task-draft`
- Design file conventions → `/fig:setup`. Separate file, separate config

## Inputs

- `record` (optional): the planning-side list — a database url, a repo, or a directory
- `mirror` (optional): the engineering tracker — usually `owner/repo`
- `out` (optional): where to write. Defaults to `~/.claude/pm-conventions.yaml`; pass `./pm-conventions.yaml` for a project-local one

Anything omitted is asked for at the start, together, in one round.

## Procedure

### 1. Settle the two sides

Ask once, grouped: where tasks are planned, and where engineering tracks them.

**"They are the same place" is a real answer.** Then `mirror.type` is `none`, `/pm:task-sync` has nothing to reconcile, and half the config below does not apply. Do not talk anyone into a second tracker.

### 2. Read the record side's schema

Read the tracker's own schema documentation first: `${CLAUDE_PLUGIN_ROOT}/_common/trackers/<record.type>.md`.

| Read | Fills |
|---|---|
| Property names and types | `task.context_rows` candidates, and which property could hold the ticket url |
| Select options on the status property | `task.properties.status_initial`, `task.status_map` keys |
| Select options on priority | `task.properties.priority` |
| Select options on project | `task.properties.projects` |
| The user list | `task.assignee_map` left-hand side |

**`link_property` is the one that matters most and the one a schema cannot decide.** List every url-typed property as candidates and ask. Where none exists, say so plainly: this property has to be created before `/pm:task-publish` can work, because it is the only thing matching runs on.

### 3. Read the mirror's schema

Read `${CLAUDE_PLUGIN_ROOT}/_common/trackers/<mirror.type>.md`, then run the id queries at the end of it.

| Read | Fills |
|---|---|
| Label list | `task.label_map.project` and `.priority` candidates |
| Board fields and their single-select options | `task.mirror_extras` — field ids, option ids |
| Board node id | `task.mirror_extras` |
| Issue types available | `task.mirror_extras`, where the tracker has typed issues |
| Collaborators | `task.assignee_map` right-hand side |
| A handful of existing tickets | `task.ticket.title` pattern, `task.hierarchy.parent_kind` and `parent_title` |
| Milestones | `task.hierarchy.milestone_format`, `milestone_projects` |

**These queries are the reason this skill exists.** Board field ids and single-select option ids are not visible in any user interface, and a person configuring by hand simply cannot find them.

### 4. Pair the two sides

`label_map` and `assignee_map` join names across systems, and neither system knows about the other.

- **Propose pairs by name similarity, then confirm them.** A record project called `Store App` and a label called `project: Store` are almost certainly the same thing — almost. Show the proposed pairing and let it be corrected in one pass
- **A record value with no counterpart stays unmapped**, and unmapped means "not mirrored". That is a legitimate state, and it is what makes `/pm:task-publish` stop cleanly rather than invent a label
- **Never invent a label to complete a pair.** A missing ticket is easy to spot later; a ticket under a wrong label is not

### 5. Interview what no schema answers

Grouped, with a recommendation on each, and recommendations grounded in what step 3 actually saw.

- `hierarchy.parent_kind` — do tasks hang under something, and what is it called. Existing ticket titles usually give this away
- `hierarchy.milestone_on` — which level carries a version, if any
- `hierarchy.milestone_projects` — which projects use them. Often only one does
- `field_owner` — which side wins per field. **The default is deliberately small**; a field nobody claims is reported as a difference and left alone, which is safer than an arbitrary winner
- `context_rows` — the defaults, or what this team actually asks

### 6. Write the draft

Write to `out`, every inferred value carrying its evidence as a line comment, in the same form `/fig:setup` uses.

```yaml
task:
  properties:
    projects: [Store App, Kiosk, Admin]   # 3 select options read from the schema
  label_map:
    project:
      Store App: "project: Store"         # paired by name, confirmed
      Kiosk:     "project: Kiosk"         # paired by name, confirmed
      Admin:     null                     # no matching label — not mirrored
  hierarchy:
    parent_kind: Epic                     # 12 of 14 open tickets titled [EPIC]
    milestone_on: parent                  # no task carries a milestone; 8 parents do
```

**A `null` is not a gap to be filled later by guessing.** It says the schema did not settle it, so the check or the step is skipped until a person writes a value.

### 7. Prove it before handing it over

**Do not stop at writing the file.** Resolve it and run one read-only pass:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml --where
```

Then take one existing task that is already filed on both sides and check that the config finds its pair — the link property resolves, the project maps to the label the ticket actually carries, the assignee maps to the username actually on it.

**A config that cannot re-derive a pair that already exists is wrong**, and this is the cheapest place to find that out. Report what was checked and what it matched.

## Report

- Which keys came from a schema, and which were interviewed
- Which were left `null`, and what each one blocks
- Unmapped projects and users, listed by name — these are the ones that will be skipped
- Whether the step-7 pairing check passed, against which task
