# Markdown as the record side

connector: none
roles: record

For a `task.record.type` of `markdown`. `{dir}` is `task.record.ref` — a directory. One file
per task, and the properties live in the file's front matter under the names the config uses.
No other tool is involved, which is what makes this the tracker a team can start on today and
the one a skill can read exhaustively.

## The shape of a record

```markdown
---
title: Notification settings — push
project: Store App           # a value from task.properties.projects
group: Notifications         # what task.hierarchy.parent_kind groups by
status: Not started          # task.properties.status_initial on a new record
priority: medium             # a value from task.properties.priority
assignee: jane               # whatever string your team uses. task.assignee_map's left side is this string
start: 2026-08-01
end: 2026-08-14
ticket:                      # ← the key task.link_property names. empty until /pm:task-publish files it
---

## Context

| Request source | … |
| Initial request | … |
…                            # one row per task.context_rows, in that order

## Change summary
```

The front matter **is** the schema. `/pm:setup` reads the keys the files already carry; a
directory with no files yet has no schema, and the interview supplies the names.

## Reading the list

A directory can be listed in full, so the coverage line is `exhaustive` — there is no
relevance ranking here to miss a row.

```bash
# every record, as one JSON line each — path, then the front matter
python3 - <<'PY'
import json, sys, yaml, pathlib
for p in sorted(pathlib.Path("{dir}").rglob("*.md")):
    s = p.read_text(encoding="utf-8")
    if not s.startswith("---\n") or "\n---\n" not in s[4:]:
        print(json.dumps({"path": str(p), "error": "no front matter"})); continue
    fm = yaml.safe_load(s[4:s.index("\n---\n", 4)]) or {}
    print(json.dumps({"path": str(p), **fm}, ensure_ascii=False, default=str))
PY
```

**The path is the id.** Match a record to its ticket by `{task.link_property}`, and a record
to itself by path — never by title, which gets rewritten.

**What moved on a day** (`/pm:log`) — where `{dir}` sits in a git repository, ask git; a
file's modification time survives neither a clone nor a checkout.

```bash
git -C {dir} log --since="{date} 00:00" --until="{date} 23:59" --name-only --format= -- . | sort -u
```

Without git, fall back to `find {dir} -name "*.md" -newermt "{date}" ! -newermt "{date + 1}"`,
and say in the log that the day was read from modification times.

`log.me.tracker_user_id` is the assignee string, since there is no user id.

## Writing back

```bash
# the link property, after a ticket is filed — edit the one line, never append a second key
python3 - <<'PY'
import pathlib, re
p = pathlib.Path("{path}"); s = p.read_text(encoding="utf-8")
head, _, body = s[4:].partition("\n---\n")
key = "{task.link_property}"
if re.search(rf"^{key}:", head, re.M):
    head = re.sub(rf"^{key}:.*$", f"{key}: {ticket url}", head, count=1, flags=re.M)
else:
    head += f"\n{key}: {ticket url}"
p.write_text("---\n" + head + "\n---\n" + body, encoding="utf-8")
PY
```

**A change summary is appended under its heading, never replaced.** One dated line after
whatever is already there — the section exists to keep the history.

**A new record** is the skeleton above, written whole. `task.notion.body_template` does not
apply here; `task.context_rows` decides the table rows and `task.properties.status_initial`
the status.

## Things that bite

- **Front matter must be the first thing in the file** — `---` on the first line, `---` on
  its own line to close. A file that opens with a heading is not a record; report it rather
  than guessing which heading was meant as the title.
- **Keys are the config's words.** The skills look the link up by the name `task.link_property`
  holds. A file that spells it differently is a file without a link, and it will be filed twice.
- **Two files with the same title are two records.** The path is the identity.
- **Dates are `YYYY-MM-DD`.** A relative date in front matter is a string nobody can sort.
- **Use the config's own status words** in `status:` — `task.status_map`'s left-hand side is
  matched on the string as written.
- **Edit with the file's own line endings and encoding.** A write that re-encodes the file
  shows up in git as a whole-file change, and the history the change summary keeps is gone.
