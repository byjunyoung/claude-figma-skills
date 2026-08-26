# pm

A bundle for writing product specs against a format, and verifying them before they are written out.

| Command | What it does |
|---|---|
| `/pm:prd` | Writes a new requirements document, or extends one |

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

Three layers merge, so **only the keys you need have to be written.** The full schema is in `_common/conventions.example.yaml`.

## What this skill holds to

**It leaves no ambiguity.** The unit of judgement and aggregation, the target of filtering and sorting, the criteria for picking a 'representative', the definition of a state transition — a feature does not work with those four left blank, so they get filled with values. One slot left TBD that the material could have settled does not pass verification.

**It does not turn a product spec into an engineering doc.** Anything on the `forbidden_terms` list appearing in the body is rejected. Write as far as "what" (the requirement) and leave "how" (the implementation) to engineering or to a TBD.

**It stops before writing.** Verification is read-only, publishing happens only after preview → "go", and even then split into skeleton → user groups → feature entries.
