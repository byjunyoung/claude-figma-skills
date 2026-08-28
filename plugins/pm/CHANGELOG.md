# pm

## 0.10.0 — 2026-08-29
- Preflight reads the config: a connector the config names is required, and a machine with no config yet is told nothing beyond the host can fail
- Preflight checks the `gh` CLI the GitHub adapter runs on — which account it is logged in to, whether the token carries `read:project`, and whether that account can open the tracker at all. A connector that is configured but not answering is reported apart from one that is absent
- `resolve-config.py --need` stops a skill on a `null` it cannot run without, naming the key, instead of running on nothing. `/pm:task-draft`, `/pm:task-publish` and `/pm:task-sync` ask for theirs
- `/pm:setup` takes `side` for a doc tool and a tracker reachable from different machines, re-runs the preflight with what step 1 named, and writes `null` with the question beside it for anything a person cannot answer
- A markdown tracker adapter, so `task.record.type: markdown` reads and writes a directory of files as the README already said it would
- Config-resolution fixtures under `tools/test`, run in CI

## 0.9.0 — 2026-08-28
- `/pm:log` reads the tracker through its adapter like every other skill here, instead of assuming one
- `/pm:log-review` asks an item's three questions in one round, and stops at `log.review.max_items`
- The log side is documented — why it is split in two, how to schedule it, and how to import an existing Notion log

## 0.8.1 — 2026-08-28
- `/pm:log-review` stitches by title where a period's files carry no urls, instead of returning every day as its own item

## 0.8.0 — 2026-08-28
- `/pm:log` reads the channel you type notes to yourself in, and carries the text across rather than a link that expires

## 0.7.0 — 2026-08-28
- `/pm:log` writes a day's work log as a file, and fills the days an earlier run missed
- `/pm:log-review` turns a period of those logs into accomplishment statements, asking for the role, the measure and the learning it cannot derive

## 0.6.0 — 2026-08-28
- `/pm:setup` opens with the same preflight
- Getting started reaches `/pm:setup` without going through the fig path first

## 0.5.3 — 2026-08-28
- `/pm:prd` declares the Notion tools it writes with

## 0.5.2 — 2026-08-27
- An empty search is no longer treated as evidence of absence

## 0.5.1 — 2026-08-27
- Issue listing no longer truncates where the diagnosis lives

## 0.5.0 — 2026-08-27
- A filed task is seated in the right board column

## 0.4.1 — 2026-08-27
- Corrected three claims the first real run disproved

## 0.4.0 — 2026-08-26
- `/pm:setup` and per-tracker recipe docs

## 0.3.0 — 2026-08-26
- `/pm:task-draft`, `/pm:task-publish`, `/pm:task-sync`

## 0.2.0 — 2026-08-26
- English release
