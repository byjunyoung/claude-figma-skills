# _common — the fig plugin's shared layer

The **source of the rules** and the **executable code** that the plugin's thirteen skills share live here.
The skill documents (SKILL.md) carry the judgement; the values and the code gather in this one folder —
two copies means one of them gets fixed and they drift apart.

When a skill points at this folder it uses **`${CLAUDE_PLUGIN_ROOT}`, never an absolute path**.
A plugin installs to a different location in every environment, and hardcoding something under a home
directory breaks on someone else's machine.

```
conventions.example.yaml   the schema plus the bundled defaults. The comments are the guide
                           (the consistency checker moved to tools/verify.py in the repo)
scripts/
  audit-struct.js          membership · bounds · frame overlap · section overlap · naming
  audit-flow.js            arrow geometry · entry direction · pass-through · label z · [state] · coverage
  audit-component.js       component default residue (MODE=collect / compare)
  arrow-build.js           the arrow-creation preamble
  prep-ops.js              the page-tidying preamble
  probe-page.js            convention inference by observation (for /fig:setup)
  deck-base.js             shared helpers for Figma Slides builds (for /fig:deck, no values)
  lib/
    resolve-config.py      config lookup · deep merge · files overlay → JSON or `const CFG=`
    draft-conventions.py   aggregates observations → a conventions.yaml draft
    check.sh               the script syntax gate
```

## Configuration

The layers merge bundled defaults → `~/.claude/figma-conventions.yaml` → `./figma-conventions.yaml`.
If it ran on the bundled defaults alone, **say "ran on defaults" in the report**.

`null` means "unknown", and that check is skipped. **Never fill an inference in as though it were settled** —
not knowing a convention and breaking one are different things, and mixing them buries the report in false positives.

Anything that differs per file (the three `pages` axes, for instance) goes in `files.<fileKey>`, not in the shared section.

## Running the scripts

The Figma plugin sandbox has no filesystem. So the config is resolved on the host and the
result is pasted in ahead of the script.

```bash
python3 scripts/lib/resolve-config.py --js <fileKey>   # → const CFG = {...};
```

Concatenate `<that one line>` + `<the whole script>` + (where needed, one `setCurrentPageAsync` line at the top)
and hand it to `use_figma`. A page switch happens once per script, so multi-page work
splits into separate calls issued in parallel in one message.

## After editing

```bash
python3 tools/verify.py     # from the repository root
```

What it checks — both config files parse · every team config key exists in the schema · script syntax ·
the frontmatter `name` matches the directory · the config keys a SKILL.md references actually exist ·
the skills it points at actually exist · no team-specific values are left in.

The team-value check runs **one pattern at a time.** Joining several with `|` tangles the escaping and
silently returns zero — one case actually slipped through that way.

## Two pitfalls

**The syntax gate** — `use_figma` wraps a script in an async function to run it, so top-level
`await` and `return` are both legal. `node --check` rejects `await` when it reads the file as CommonJS
and `return` when it reads it as ESM. That is why `check.sh` wraps it the same way before checking.

**Excluded sections** — treated three different ways. Dropped from the audit, dropped from coverage, but
**kept as pass-through targets.** If a line actually crosses one, it is a broken line whether the section is excluded or not.

## Editing and releasing

Edit in your working copy and push to the repository.

```
1  edit in the working copy
2  python3 tools/verify.py          confirm zero violations
3  bump version in .claude-plugin/plugin.json   ← skip this and the installed copy never changes
4  push to the repository
5  claude plugin marketplace update <marketplace>
6  claude plugin uninstall fig@<marketplace> && claude plugin install fig@<marketplace>
```

**Step 3 is the one that matters.** An installed plugin is pinned by version at
`plugins/cache/<marketplace>/<plugin>/<version>/`, so with the version unchanged the installed copy keeps
running the old code however many times the marketplace is updated.

**Do not rely on the executable bit.** A file uploaded through the GitHub Contents API does not carry one.
Running `check.sh` directly gives `Permission denied` on an installed copy — call it as `bash <path>`.
