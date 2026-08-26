---
name: setup
description: Reads an unfamiliar Figma file and works backwards to its conventions, drafting a figma-conventions.yaml. Page roles, naming patterns, state suffixes, spacing tokens, section style, and arrow style are observed from actual nodes and taken as the dominant value; anything with too few samples or a split vote is left null rather than guessed, then filled in by interview. It finishes by running /fig:lint and judging the draft by its false-positive rate. Run this first when opening these skills on a new company or a new file. Triggers - "/fig:setup", "work out this file's conventions", "draft the config", "이 파일 관례 뽑아줘", "설정 초안 만들어줘", "이 파일에 맞게 세팅해줘".
allowed-tools: AskUserQuestion, Bash, Read, Write, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot
---

# fig:setup — infer a file's conventions, draft the config

Every skill here reads `figma-conventions.yaml` as its source of rules. This skill **produces the first copy in an environment that has none.**

It does not ask for the conventions, it **observes them in the file.** Section style, spacing tokens, arrow style — those are already sitting on the canvas, and asking a person makes it worse, because they answer from memory and memory is wrong. What only a person knows — which page is canonical, which states are mandatory — is asked rather than observed.

**Prerequisites**: load `figma:figma-use` before calling `use_figma`. **Zero writes** — the Figma file is never touched. The only thing written is one local config file.

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

If it isn't known, leave `null`. **Do not invent a value to fill the blank.**

### 5. Preview → go → write

Show the full draft plus three groups — what observation filled, what the interview filled, and what stayed `null` — and get a go. If a config already exists, do not overwrite it; show **only the differences**.

### 6. Verify — test the draft by its false-positive rate (required)

**Do not write the config and stop.** Run `/fig:lint` against one representative page and read the result.

- If **nearly everything is reported, the file is not a mess — the pattern is wrong.** Naming especially: a regex that can't accept how that team actually writes things
- Measured case: a pattern that restricted the suffix to `[A-Za-z]` flagged 38 of 61 frames (62%). The suffixes were Korean. Lifting the restriction dropped it to 2 (3%), and both were genuine
- When false positives are suspected, **open a sample of the reported violations and confirm by eye** that they really break the rule. If not, fix the pattern and run again

Skipping this step hardens a wrong config, and every lint run after it drowns in false positives.

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
