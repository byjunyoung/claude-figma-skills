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
- `side` (optional): `record`, `mirror`, or `both` (the default). For when the two sides are reachable from different machines — the doc tool from one, the tracker from another. A run with a side writes only that side's keys into `out` and leaves the other side's byte for byte, so two runs on two machines finish one file

Anything omitted is asked for at the start, together, in one round.

## Procedure

### 0. Preflight — can this machine run it at all (required)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/preflight.py
```

**A missing connector does not announce itself.** A skill cannot call a tool it was never
given, and it does not fail loudly when one is absent — the run simply comes back thin, and
that reads as the skill having found nothing. This is the one step that says so out loud.

Report the table as it returns, then judge it:

- **FAIL** — stop and hand over the fix lines. Nothing below this works without them
- **absent** on an optional connector — fine as it is. Say so, because a config key pointed
  there in a later step will not reach it
- **Nothing beyond the host can fail yet.** Whether GitHub matters depends on an answer step 1
  has not asked for, so on a machine with no config every connector reads as optional and the
  summary says so. Step 1 runs the check again with the answers, and that pass is the verdict

### 1. Settle the two sides

Ask once, grouped: where tasks are planned, and where engineering tracks them.

**"They are the same place" is a real answer.** Then `mirror.type` is `none`, `/pm:task-sync` has nothing to reconcile, and half the config below does not apply. Do not talk anyone into a second tracker.

**Then run the preflight again with what was named**, so its verdict means something:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/preflight.py --require Notion,GitHub   # whichever step 1 named
```

Two rows decide a GitHub mirror: the `gh` CLI — the tracker adapter runs on it, not on the
connector — and the tracker itself, which the check tries to open as the account `gh` is logged
in to. **A `missing` here is a fact about this machine, not about the schema.** Either fix it
with the line the row carries, or finish the side that is reachable here and run `side: mirror`
on the machine that can reach the other. Do not interview around a side that cannot be read —
a value typed from memory in place of a schema read is exactly the config this skill exists to
prevent.

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

**Where the schema read itself fails** — a database the connected account cannot see, a tracker type with no adapter — stop this side: write its keys as `null` with the comment `# unreachable from this machine`, carry on with the other, and say in the report which machine or account can finish it.

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

Three things have to line up for them, and only the first shows in any error message: the account `gh` is logged in to can see the repo — a personal account against a company org gets a 404 that reads as if the repo did not exist; that account is a member of the org; and its token carries `read:project`, without which the repo answers and the board queries come back empty. The preflight row for `gh` names the account and the scopes. Read it before reading a 404 as a missing repo.

### 4. Pair the two sides

`label_map`, `assignee_map` and `status_map` join names across systems, and neither system knows about the other.

- **Propose pairs by name similarity, then confirm them.** A record project called `Store App` and a label called `project: Store` are almost certainly the same thing — almost. Show the proposed pairing and let it be corrected in one pass
- **A record value with no counterpart stays unmapped**, and unmapped means "not mirrored". That is a legitimate state, and it is what makes `/pm:task-publish` stop cleanly rather than invent a label
- **Never invent a label to complete a pair.** A missing ticket is easy to spot later; a ticket under a wrong label is not
- **`status_map` will not fall out of name similarity — ask it.** A record's statuses describe how far the planning side has got; a board's columns describe whose turn it is. `Not started` and `Backlog` may line up, but the two in the middle rarely do, and a wrong guess seats finished specs in the backlog column where the engineering side reads them as untouched. Show the two lists side by side and ask which column each status should file into, saying that a status left unpaired keeps the board's own default — and that no answer at all is also an answer: an empty `status_map` seats nothing, and the file carries the question for whoever runs the board

### 5. Interview what no schema answers

Grouped, with a recommendation on each, and recommendations grounded in what step 3 actually saw.

**Every question here has a "do not know" answer, and it is `null`.** Say so before asking. Someone new to a team cannot say which column a finished spec should sit in or which side owns the assignee field — that is knowledge about how the team works, not about the tools, and the person who has it runs the board. A `null` is written with the question beside it as a comment, so whoever can answer finds it in the file rather than in a chat history. Never fill it with the recommendation just because a recommendation was offered.

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
  status_map: {}                          # not settled — which column should a finished spec sit in? ask whoever runs the board
  mirror_extras:
    project_node_id: null                 # unreachable from this machine — run `side: mirror` where gh can see the org
```

**A `null` is not a gap to be filled later by guessing.** It says the schema did not settle it, so the check or the step is skipped until a person writes a value.

**With a `side`, read the existing file first** and rewrite only the keys that side owns. Record: `task.record`, `task.properties`, `task.context_rows`, `task.link_property`, `task.notion`. Mirror: `task.mirror`, `task.mirror_extras`, `task.ticket`, `task.hierarchy`. The maps that join the two — `task.label_map`, `task.assignee_map`, `task.status_map` — belong to whichever run can see both sides, and are left alone otherwise. Everything else in the file stays byte for byte, comments included.

### 7. Prove it before handing it over

**Do not stop at writing the file.** Resolve it and run one read-only pass:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml --where
```

Then take one existing task that is already filed on both sides and check that the config finds its pair — the link property resolves, the project maps to the label the ticket actually carries, the assignee maps to the username actually on it.

**A config that cannot re-derive a pair that already exists is wrong**, and this is the cheapest place to find that out. Report what was checked and what it matched.

With one side unreachable the pair cannot be checked. Say `not checked` in the report rather than checking the half that can be read and calling it a pass.

## Report

- Which keys came from a schema, and which were interviewed
- Which were left `null`, and what each one blocks
- Unmapped projects and users, listed by name — these are the ones that will be skipped
- Whether the step-7 pairing check passed, against which task — or `not checked`, and why
- Which side this run wrote, and what was left for another machine
- Where the mirror is GitHub, the account `gh` was on — so a later 404 can be read against it
