# {Tool} as the record side / as the mirror

<!-- Keep the sections whose questions this tool answers. Delete the rest — a heading with
     nothing under it reads as an answer. Every call below should be one you ran; mark one
     you have not with (unverified) and remove the mark when it has run. -->

For a `task.record.type` / `task.mirror.type` of `{type}`. `{ref}` is `task.record.ref` /
`task.mirror.ref` — {what the ref is: a database url, an owner/repo, a project key}.

## The schema

```
{call that returns property names, types, select options, and users}
```

{Which property is url-typed and could hold the mirror's link. Whether the user list is a
separate call.}

## Reading the list

```
{call that lists every record with title, project, group, priority, status, assignee, link}
```

**Is it exhaustive?** {yes — a listing with paging | no — a relevance-ranked search. Say what
a search misses and what the coverage line should report.}

**What moved on a day** — {how to filter on last-edited for a date. Whether the filter is
applied in the query or after the fetch.}

## Reading one record

```
{call that returns one record's properties and body}
```

{Where the context table sits in the body.}

## Writing back

```
{call that creates a record with properties and a body}
{call that sets the link property — and how to read it back}
{call that appends one line under the change-summary heading without replacing the section}
```

{Whether a template is applied on create. If not, the body skeleton has to be written explicitly.}

## As the mirror

```
{exhaustive listing of tickets with open/closed state — and where it truncates}
{create a ticket · create a parent · attach a child · set labels, assignee}
{board: the project field, the status column, the dates — which id each takes}
{milestones: list open, create, set on the parent}
{the id queries /pm:setup runs for task.mirror_extras}
```

## Things that bite

- {one line per thing, each because it happened}
