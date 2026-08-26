# GitHub as the mirror

The calls behind the abstract steps in `/pm:task-publish` and `/pm:task-sync`, for a mirror
whose `task.mirror.type` is `github`. Every placeholder in braces comes from the config —
`{repo}` is `task.mirror.ref`, and everything under `{extras.*}` is `task.mirror_extras`.

**These are recovered from a working setup, gotchas included.** Where a line carries a warning,
the warning is there because it was hit.

## Reading

```bash
# every task and parent on the board, with title, status, milestone and url
gh project item-list {extras.project_number} --owner {extras.project_owner} --format json

# open / closed is a property of the issue, not the board column — read it separately
gh issue view {n} --repo {repo} --json state,body --jq '{state, body}'

# candidate parents for a project
gh issue list --repo {repo} --label "{project label}" --state open \
  --json number,title,url \
  --jq '.[] | select(.title | test("\\[{parent_kind}\\]"; "i"))'
```

## Creating a task

```bash
gh issue create --repo {repo} \
  --title "{task.ticket.title, filled in}" \
  --body  "{assembled body}" \
  --label "{default_labels},{priority label},{project label}" \
  --assignee "{mapped username}"
```

**Never pass `--milestone` on a task** where `task.hierarchy.milestone_on` is `parent`.
The parent owns the milestone; a task carrying one is the policy violation `/pm:task-sync`
reports as `Policy`.

## Creating a parent

```bash
gh issue create --repo {repo} \
  --title "{task.hierarchy.parent_title, filled in}" \
  --body  "## Definition of done"$'\n'"- every child task done" \
  --label "{default_labels},{priority label},{project label}" \
  --assignee "{mapped usernames}"
```

The issue **type** is not a CLI flag — it is a GraphQL mutation, and it must be set or the
item shows up untyped on the board:

```bash
gh api graphql -f query='
  mutation { updateIssue(input: {
    id: "{parent node id}", issueTypeId: "{extras.epic_issue_type}"
  }) { issue { id } } }'
```

## Attaching a task to its parent

```bash
gh api graphql -f query='
  mutation { addSubIssue(input: {
    issueId: "{parent node id}", subIssueId: "{task node id}"
  }) { issue { id } } }'
```

## Putting it on the board

```bash
# add — takes the project NUMBER
gh project item-add {extras.project_number} --owner {extras.project_owner} \
  --url {issue url} --format json --jq '.id'
```

**Capture that id.** Every field write below addresses the *item*, not the issue, and there is
no second way to look it up cheaply.

```bash
# the single-select project field
gh api graphql -f query='
  mutation { updateProjectV2ItemFieldValue(input: {
    projectId: "{extras.project_node_id}",
    itemId:    "{item id}",
    fieldId:   "{extras.project_field_id}",
    value: { singleSelectOptionId: "{extras.project_field_options[label]}" }
  }) { projectV2Item { id } } }'

# the date fields — task only. A parent's schedule is managed elsewhere
gh project item-edit --project-id {extras.project_node_id} --id {item id} \
  --field-id {extras.start_date_field} --date {YYYY-MM-DD}
gh project item-edit --project-id {extras.project_node_id} --id {item id} \
  --field-id {extras.end_date_field}   --date {YYYY-MM-DD}
```

**`item-add` takes the project number; `item-edit` takes the project node id.** They are not
interchangeable and the error message does not say which one it wanted.

## Milestones

Only where the project appears in `task.hierarchy.milestone_projects`.

```bash
# what already exists, open only, so the interview offers real options
gh api repos/{repo}/milestones --paginate \
  -q '.[] | select(.title | startswith("{prefix}")) | select(.state=="open") | .title'

# create one, after a preview
gh api -X POST repos/{repo}/milestones -f title="{task.hierarchy.milestone_format, filled in}"

# set it on the parent
gh issue edit {parent number} --repo {repo} --milestone "{title}"
```

## Updating an existing ticket

```bash
gh issue view {n} --repo {repo} --json body --jq .body     # read before you overwrite
gh issue edit {n} --repo {repo} --body "{new body}"
```

Keep the row that links back to the record. It is what a person clicks to find the detail —
it is never what matching reads.

## Finding the ids for `mirror_extras`

`/pm:setup` runs these for you. They are here so the values can be checked by hand.

```bash
# project node id
gh api graphql -f query='{ organization(login: "{owner}") {
  projectV2(number: {n}) { id } } }' --jq '.data.organization.projectV2.id'

# fields, and the option ids of every single-select
gh api graphql -f query='{ organization(login: "{owner}") { projectV2(number: {n}) {
  fields(first: 50) { nodes {
    ... on ProjectV2Field { id name }
    ... on ProjectV2SingleSelectField { id name options { id name } }
  } } } } }'

# issue types available to the org
gh api graphql -f query='{ organization(login: "{owner}") {
  issueTypes(first: 20) { nodes { id name } } } }'
```

For a personal account rather than an org, swap `organization(login:)` for `user(login:)`.
