# fig

A bundle for tidying, auditing and syncing Figma files that are already drawn. Not the side that makes screens, but the side that manages a file several people share.

```bash
claude plugin marketplace add byjunyoung/claude-product-skills
claude plugin install fig@byjunyoung
```

| Command | What it does |
|---|---|
| `/fig:setup` | Observes a file's conventions and drafts a config |
| `/fig:read` | Collects the page and screen inventory |
| `/fig:prep` | Unifies names · places sections · stubs missing screens |
| `/fig:arrows` | Creates and re-syncs flow arrows |
| `/fig:lint` | The read-only audit gate (zero writes) |
| `/fig:tokens` | Audits colour bindings against design-system tokens |
| `/fig:sync` | Exhaustive audit against the canonical page → apply → migrate |
| `/fig:diff` | Annotates what changed · writes up the task doc |
| `/fig:proto` | A working single-file HTML prototype |
| `/fig:code` | Applies the design into a frontend repo |
| `/fig:qa` | Compares a shipped screen against the plan and files defects |
| `/fig:deck-setup` | Measures a team presentation template into deck assets |
| `/fig:deck` | Turns a source into a presentation deck (Figma Slides) |

A single `figma-conventions.yaml` decides the rules. The layers merge bundled defaults → `~/.claude/figma-conventions.yaml` → `./figma-conventions.yaml`, so **only the keys you need have to be written.**

On a file you are opening for the first time, run `/fig:setup` first and let it observe the conventions. The full explanation is in the [repository README](https://github.com/byjunyoung/claude-product-skills).

## The other half

[`pm`](../pm/README.md) writes the spec this file is drawn against and opens the task the changes belong to. The two never call each other, but they share two objects: point `qa.baseline.prd` at the spec `pm` writes and `task_tracker.ref` at the record it opens, and `/fig:qa` gains a baseline while `/fig:diff` gains somewhere to put the comparison table. Neither is required — left `null` and `none`, both skills still run. The [repository README](https://github.com/byjunyoung/claude-product-skills#where-the-two-meet) draws the whole loop.
