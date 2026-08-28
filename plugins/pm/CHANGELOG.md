# pm

## 0.12.0 — 2026-08-29
- `/pm:setup` runs as an onboarding: it opens with what it produces and how long it takes, shows an eight-step ladder and names each step, asks in the person's words rather than the file's keys, offers "leave it blank" on every question, and ends on a first result — a context table drafted from one pasted message, nothing written — with the commands that follow
- Preflight leads with a verdict in words and the lines to fix; the table is detail underneath. A 400 on the GitHub connector says what usually causes it

## 0.11.0 — 2026-08-29
- Adapters are open. The calls for a tool live in `trackers/<type>.md` or `sources/<type>.md`, the type in the config picks the file, and `adapter.py` finds it — bundled, or yours in `adapters.dirs` outside the plugin. A type with no file stops the skill on exit 3
- What an adapter has to answer is written down — `trackers/README.md`, `sources/README.md` — with a template for each
- `/pm:setup` drafts an adapter for a tool it has never seen from the tools connected on the machine, marking the answers it could not verify. It also takes "nothing yet" and lays out one markdown repository that needs no other tool
- Chat and calendar are adapters too — `sources.chat_type`, `sources.calendar_type`; Slack and Google Calendar ship, every call checked against the live tool's schema and run once
- Preflight requires whatever tool the config names, not only the three it knew — a value somebody wrote, never a default alone

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
