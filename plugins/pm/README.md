# pm

A bundle for product specs and the tasks that come out of them. Write the spec, draft the task, file it, and keep both sides reconciled.

```bash
claude plugin marketplace add byjunyoung/claude-product-skills
claude plugin install pm@byjunyoung
```

| Command | What it does |
|---|---|
| `/pm:setup` | Reads your tool schemas and drafts the config |
| `/pm:prd` | Writes a new requirements document, or extends one |
| `/pm:task-draft` | Turns a request source into a task's context table |
| `/pm:task-publish` | Files one task as a ticket in the engineering tracker |
| `/pm:task-sync` | Reconciles the planning list against that tracker |
| `/pm:log` | Writes a day's work log as a file from the same tracker |
| `/pm:log-review` | Turns a period of those logs into accomplishment statements |

## Where it writes

Where it is stored is decided by `prd.target` in `pm-conventions.yaml`. The skeleton is the same either way; only the publishing differs.

```
markdown   local files. The default — no other tool required
git        written as markdown, then a branch and a PR
notion     a Notion page. Requires the prd.notion section filled in
```

## Configuration

```
the plugin's bundled defaults        the floor
      ↓ covered by
~/.claude/pm-conventions.yaml        your own shared config
      ↓ covered by
./pm-conventions.yaml                per project (strongest)
```

Three layers merge, so **only the keys you need have to be written.** The full schema is in `_common/conventions.example.yaml`, and `/pm:setup` drafts it by reading your tools' schemas — including the board field and option ids that no interface shows you. It opens by checking this machine — `python3` with PyYAML, `node`, and which connectors actually answer — so anything missing is named up front.

## What this skill holds to

**It leaves no ambiguity.** The unit of judgement and aggregation, the target of filtering and sorting, the criteria for picking a 'representative', the definition of a state transition — a feature does not work with those four left blank, so they get filled with values. One slot left TBD that the material could have settled does not pass verification.

**It does not turn a product spec into an engineering doc.** Anything on the `forbidden_terms` list appearing in the body is rejected. Write as far as "what" (the requirement) and leave "how" (the implementation) to engineering or to a TBD.

**It stops before writing.** Verification is read-only, publishing happens only after preview → "go", and even then split into skeleton → user groups → feature entries.

## The other half

[`fig`](../fig/README.md) works the design file this spec is drawn into. The two never call each other, but they share two objects. If you install both, set `qa.baseline.prd` in `figma-conventions.yaml` to the spec this config writes, and `task_tracker.ref` to the task record it opens — otherwise `/fig:qa` has no baseline to judge against and `/fig:diff` has nowhere to write the comparison. The [repository README](https://github.com/byjunyoung/claude-product-skills#where-the-two-meet) draws the whole loop.
