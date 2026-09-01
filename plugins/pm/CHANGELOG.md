# pm

## 0.15.0 — 2026-09-01
- **The contract has a level.** `task.contract.level` says which ticket carries the done conditions and the QA checklist — the task, or the parent it hangs under. Put them where review happens: a condition and the step confirming it, split across two tickets, cannot be checked against each other and the coverage rule stops meaning anything. `level: none` files a summary and links only
- At `level: parent` the contract is its own run (`mode: contract`) rather than a rewrite triggered by every sibling task, and it is a body edit on an existing parent — the two sections are replaced and every other section of that parent is left byte for byte
- The referenced-version line is written directly beneath the design-match line, wherever that line goes. A line saying the build matches a design *at a version*, sitting on a different ticket from the version it names, points at nothing
- **A task's own done conditions are not the contract, and the two no longer collide.** The contract says the feature behaves correctly; a task's done conditions say this slice of work is finished — the artefacts for a task that produces the requirement, the built slice for one that works against it. `task.ticket.done_defaults` seeds the recurring artefacts so a draft starts from them
- The task summary is a scope boundary: what this slice covers, where it stops, which ticket has the rest. Where the title already settles it, nothing is written — a sentence repeating the title looks like content and is worse than an empty section
- **Where a design-match line is in play, the QA section must carry the comparison step, and that step enumerates every screen.** It is the one condition with no click path of its own, so it is the one read past; "confirm it matches the design" is confirmed by a glance, while a list is confirmed by going through it and a skipped screen shows. Added as a fifth required coverage kind
- `task.contract` now holds `level`, `sections`, `allow_tbd`, `incomplete_note`, `incomplete_label` and `design_match_line`; `task.ticket` keeps the task body's own slots. Where a tracker already gates on the sections existing, the guidance is to leave `incomplete_label` unset and let the gate do it
- A ticket now carries the two sections that decide when the work is finished — done conditions and a QA checklist — and they originate in the ticket rather than being copied from anywhere. The record answers why the work is happening; the ticket answers what counts as done, and the boxes are ticked where engineering works
- `/pm:task-publish` drafts both from the spec entry and the design before it asks anything. Behaviour, state, thresholds and copy are written as words; what is confirmed by comparing a value against the design is not written at all, and `ticket.design_match_line` covers it in one line against a pinned version. The rule is decided-by-looking versus decided-by-measuring, not appearance versus behaviour
- The design is read for structure — which state variants exist, what the screens are called, where the flow goes — never for how it looks, and copy comes from the spec first so placeholder text cannot freeze into the contract
- **Drafting is a coverage pass, not an impression.** Every row of the behaviour table, every state and case, every rule and exception, every state variant actually drawn, and the round trip after a write — each either produces a condition or is named in the preview as skipped with its reason. Happy path, states and cases, rules and exceptions and round trip all have to be present or explicitly not applicable, and the preview carries a coverage line so a thin draft is visible instead of silent
- Every QA step traces to a done condition, and a done condition no step reaches is the gap the section exists to close. A step writes its path out in full — "same as above" hides the step that differs — and its expected result is what gets looked at rather than a verdict
- **A ticket filed before its requirement exists says so.** Where the materials settle nothing, the preview forks — file it as a placeholder, or stop and write the requirement first. A placeholder carries `incomplete_note` under the done heading as a quote rather than a checkbox (a checkbox invites ticking, which is how "TBD" stopped meaning anything), names specifically what is missing, drops the QA heading the note already accounts for, takes `incomplete_label`, and is seated in the backlog whatever `status_map` says — a ticket nobody can start does not belong in a column somebody picks work up from. Filling it later is the ordinary second pass. New keys: `ticket.incomplete_note`, `ticket.incomplete_label`
- The update path reconciles instead of overwriting: a surviving line keeps its tick, a dropped line is named in the preview, a new line arrives unticked
- `ticket.sections` is a keyed map rather than a list, so a team can rename a section without the skill losing track of which slot it is. New keys: `sections.done`, `sections.qa`, `link_rows.version`, `allow_tbd_done`, `design_match_line`
- `/pm:task-sync` leaves the binding sections empty and reports the tickets it created as still needing `/pm:task-publish` — drafting a contract is not something a bulk reconciliation should do unwatched

## 0.14.0 — 2026-08-29
- Every sentence a person reads during a run is in plain words — the preflight verdicts and fix lines, what the scripts say when they stop ("is not supported yet", "is not set", "supported as the other side"), the README's troubleshooting as what-you-see · what-it-means · what-to-do, and a rule in every skill to say what a stop means rather than its code or path

## 0.13.0 — 2026-08-29
- Preflight reads the `connector:` line of a type's adapter, so a type a team writes (`gsheet`) requires the connector it actually runs on (Google Drive) rather than a name nobody prints. Found by running `/pm:setup` 3b for real against a Google Sheet
- Adapters declare `roles:` too, and `adapter.py --role` refuses a file for a side it does not serve with exit 4 — the schema allowed `record.type: github` and `mirror.type: notion`, and neither bundled file answered for that side
- The adapter templates and contract carry both lines, and 3b writes them
- `verify.py` now fails on a `${CLAUDE_PLUGIN_ROOT}` path that does not exist, a bundled adapter without `connector:` or `roles:`, an adapter naming a tool no skill may call, and a skill reference in the root README that does not exist. Every script under `_common` has a fixture or a syntax check in CI
- Preflight, draft-generator and importer fixtures under `tools/test`, run in CI

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
