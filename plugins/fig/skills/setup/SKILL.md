---
name: setup
description: Reads an unfamiliar Figma file and works backwards to its conventions, drafting a figma-conventions.yaml. Page roles, naming patterns, state suffixes, spacing tokens, section style, and arrow style are observed from actual nodes and taken as the dominant value; anything with too few samples or a split vote is left null rather than guessed, then filled in by interview. It finishes by running /fig:lint and judging the draft by its false-positive rate. Run this first when opening these skills on a new company or a new file. Triggers - "/fig:setup", "work out this file's conventions", "draft the config", "이 파일 관례 뽑아줘", "설정 초안 만들어줘", "이 파일에 맞게 세팅해줘".
allowed-tools: AskUserQuestion, Bash, Read, Write, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot
---

# fig:setup — infer a file's conventions, draft the config

Every skill here reads `figma-conventions.yaml` as its source of rules. This skill **produces the first copy in an environment that has none.**

It does not ask for the conventions, it **observes them in the file.** Section style, spacing tokens, arrow style — those are already sitting on the canvas, and asking a person makes it worse, because they answer from memory and memory is wrong. What only a person knows — which page is canonical, which states are mandatory — is asked rather than observed.

**Prerequisites**: load `figma:figma-use` before calling `use_figma`. **Zero writes** — the Figma file is never touched. The only thing written is one local config file.

## How it runs — the ladder

Show this before the first call, and name each step as it begins:

```
① Check this machine                  read-only · seconds
② Read the page landscape             read-only
③ Probe three to five pages           read-only · says what it saw
④ Ask what observation can't settle   one at a time · a recommendation · "leave it blank" always offered
⑤ Write the file                      preview → go · one local file
⑥ First result                        /fig:lint on one page, judged by its false-positive rate
```

**Open with what this produces.** After this, a page can be tidied and its missing states
stubbed (`/fig:prep`), its flow arrows drawn and re-synced (`/fig:arrows`), and audited in one
pass (`/fig:lint`) — against the conventions this file already keeps, not a template's. Five
minutes on a tidy file. Nothing in Figma is touched; one local file is written, and shown first.

**Questions in the person's words, not the key's.** "Which pages does engineering build from?"
rather than `pages.strict`; "how far apart do you keep screens?" rather than `layout.frame_gap`.
The key lands in the file; the phrasing does not. Say what is being read before reading it —
a probe that takes seconds in silence reads as a hang.

## When to invoke

- Opening these skills on a new company or a new file for the first time
- When `resolve-config.py` falls through to the bundled defaults (the report says so)
- When the file's conventions have changed enough that the config should be re-derived

## When NOT to invoke

- The config exists and one value needs changing → edit the file directly
- Checking for rule violations → `/fig:lint`
- Tidying structure → `/fig:prep`

## Inputs

- `figma_url` (required): the target file URL. The fileKey is taken from it
- `out` (optional): where to write. Defaults to `~/.claude/figma-conventions.yaml`; use `./figma-conventions.yaml` for a project-specific config

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
- **unknown** on Claude in Chrome — it is a browser extension rather than an MCP server, so
  the shell cannot see it. It matters only for `/fig:proto`, `/fig:code` and `/fig:qa`
- **The seat is not visible from the shell either.** This skill only reads, so a View seat is
  fine here. The skills that write — `/fig:prep`, `/fig:arrows`, `/fig:diff`, `/fig:sync`,
  `/fig:tokens`, `/fig:deck` — check it themselves with `whoami` before their first write
- **Only `plugin:figma` can be required on a file with no config.** Once the config names a
  tracker in `task_tracker.type`, that connector is required on later runs and a run that
  cannot reach it stops on its name. Until then the other connectors read as optional, and
  the summary says so

### 1. Read the page landscape (read-only)

Read page names and **order** from `figma.root.children`. The file-level response from `get_metadata` returns an incomplete page list, so it is not used here.

```js
return figma.root.children.map((p, i) => `${i}\t${p.id}\t${p.name}`).join("\n");
```

What to take from this —

- **Are there divider pages** (empty pages named `---` or `## label ##`)? If so, the band beneath each one is a role group, and a candidate for `match: divider` on the three `pages` axes
- **Is there a naming prefix?** Bracket tags, symbols, a leading word — any group of pages sharing a prefix is probably a role split, and a candidate for `pages.strict` / `free` / `readonly`. Do not decide from the name alone what a prefix *means*; ask in step 4
- If no convention is visible, **do not invent one.** An empty list means the file simply has no such tier

### 2. Probe representative pages (in parallel)

Do not sweep every page. Pick **three to five pages that hold a lot of screens and are already tidy** — a thin sample hardens coincidence into convention, and an untidy page blurs it.

For each page, prepend `const PAGE_ID = "<id>";` to `${CLAUDE_PLUGIN_ROOT}/_common/scripts/probe-page.js` and run it through `use_figma`. **Split the calls per page and issue them in one message so they run in parallel** — each script sets `setCurrentPageAsync` exactly once.

The probe does not judge; it only reports observations. What counts as convention is decided in the next step, once they are summed.

### 3. Generate the draft

Save each probe result as JSON, then:

```
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/draft-conventions.py probe1.json probe2.json ... > draft.yaml
```

Where the sample is below `MIN_SUPPORT`, or the most common value is below `DOMINANCE`, the generator **writes no value and leaves `null`.** The `n/m` in the comment on each line is the evidence.

`null` is not a failure, it is **a record of not knowing.** Left alone, it means that check is skipped.

### 4. Interview for the nulls (one at a time)

Some things never come out of observation. Show the full list first so the scale is clear, then ask one at a time, most important first. Attach **the recommendation the observation suggests** to each question so a short answer finishes it.

| Item | Why observation can't settle it |
|---|---|
| `pages.strict` · `free` · `readonly` | Which page is canonical is not written on the canvas |
| `naming.required_states` | Requires first deciding the screen type (list, form, search) |
| `layout.section_padding` | Frame positions alone don't separate out a section's inner padding |
| the `arrows.trunk` family | Only shows up along elbow paths, so inference is unreliable |
| `component_audit.body_offset` | You have to open one screen and measure nav width and top bar height |
| `task_tracker` · `design_system` | Facts that live outside the file |

If it isn't known, leave `null`. **Do not invent a value to fill the blank.** Offer "leave it blank" on every question, out loud — a blank is a complete answer, written with the question beside it.

### 5. Preview → go → write

Show the full draft plus three groups — what observation filled, what the interview filled, and what stayed `null` — and get a go. If a config already exists, do not overwrite it; show **only the differences**.

### 6. First result — test the draft by its false-positive rate (required)

**Do not write the config and stop.** Run `/fig:lint` against one representative page and read the result.

- If **nearly everything is reported, the file is not a mess — the pattern is wrong.** Naming especially: a regex that can't accept how that team actually writes things
- Measured case: a pattern that restricted the suffix to `[A-Za-z]` flagged 38 of 61 frames (62%). The suffixes were Korean. Lifting the restriction dropped it to 2 (3%), and both were genuine
- When false positives are suspected, **open a sample of the reported violations and confirm by eye** that they really break the rule. If not, fix the pattern and run again

Skipping this step hardens a wrong config, and every lint run after it drowns in false positives.

This is the first result, so close on it: what the audit found on that page, in one line, and
the commands that follow, in the order they are used —

    /fig:lint <page>       audit any page against the file you just wrote
    /fig:prep <page>       tidy names, place sections, stub the missing states
    /fig:arrows <page>     draw the flow, re-sync it after frames move

## Constraints

- **Zero Figma writes.** This skill only reads. The one thing it writes is a local config file
- **Never present inference as settled.** Thin or split samples get `null`, with the evidence (n/m) left as a comment
- Before overwriting an existing config, **show the diff and get a go** — hand-entered values are hard to recover once erased
- Three to five representative pages. Probing every page costs tokens and does not make the conventions more accurate
- Do not report completion without step 6

## Notes

- The probe measures gaps between **adjacent pairs only.** Counting all pairs lets two- and three-step distances flood the list and collapse the mode — measured, `frame_gap` fell to 35% and became un-inferable
- Section style, arrow style, and label pills observe accurately. In practice, color, weight, font and padding all matched the hand-written config exactly
- Items with few samples, like `domain_row_gap`, do not come out well — staying `null` is the expected outcome
- Anything that differs per file (the three `pages` axes, typically) belongs under `files.<fileKey>`, not in the shared section
