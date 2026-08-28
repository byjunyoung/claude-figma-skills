# Slack as the chat source

For a `sources.chat_type` of `slack`. The channel and app ids the calls need come from
`log.sources` — `chat_channels`, `notes_channel`, `notes_exclude_apps`. Your own user id is
printed in the search tool's own description ("Current logged in user's user_id is U…"). The
calls below were run against a real workspace on 2026-08-29; the warnings are what came back.

## A thread from a link

```
slack_read_thread   channel_id={C… from the permalink}   message_ts={the parent's ts, "1234567890.123456"}
```

A permalink is `…/archives/{channel}/p{16 digits}`, and the ts is those digits with a decimal
point before the last six. A permalink to a *reply* carries the reply's ts in the path and the
root's in its `?thread_ts=` query — read from the root, or only the tail comes back. Attached
images and files arrive as names.

## A channel on a day

```
slack_read_channel   channel_id={id}   oldest={epoch of 00:00 local}   latest={epoch of 23:59:59 local}   limit=100
```

Newest first. Page with `cursor` until it is empty — a day in a busy channel is more than one
page. A user id as `channel_id` reads that DM, which is how a notes channel is read where it is
a DM to yourself.

## Messages about me on a day

```
slack_search_public_and_private   query="from:<@{my id}> on:{YYYY-MM-DD}"   include_context=false   response_format=concise   sort=timestamp   limit=20
slack_search_public_and_private   query="<@{my id}> on:{YYYY-MM-DD}"        … the same parameters
```

The first is what I sent; the second is where I was mentioned — the literal `<@id>` in the
query matches the mention. Results carry a local-time stamp and a `cursor` for the next page.
`limit` tops out at 20, and the size cap is on the response rather than the page:
`include_context=false` and `response_format=concise` are what keep it under. `after` and
`before` take Unix timestamps as separate parameters, for a day bounded in your own zone.

## My notes channel

`log.sources.notes_channel` — read as a channel on a day. **An app that posts there on your
behalf is attributed to the app** — its user id is the author — and `log.sources.notes_exclude_apps`
lists the ids to drop. Nothing you did not type belongs in your notes.

## Permalinks and names

```
slack_read_user_profile   user_id={U…}   response_format=concise     → display name, for a quote's sender
```

A message's permalink is `https://{workspace}.slack.com/archives/{channel}/p{ts without the dot}`.
Record a quote with the time, the body as written, and the permalink beside it.

## Things that bite

- **The search cap fails silently.** An over-large request returns nothing, not a partial page —
  which reads as a quiet day. Concise, no context, and page
- **`include_bots` at its default still returned a post from a sender named as a report bot**, in
  a mention search — whether that sender was a bot user or an app was not checked. Drop app
  authors by id from `log.sources.notes_exclude_apps`, never by that flag
- **Retention expires.** Carry the text across; keep the permalink as a citation, not as the record
- **Which zone `on:` counts a day in is not documented.** The runs here matched the local day,
  but where the workspace and you sit in different zones, `after` and `before` with your own
  epoch bounds is the form that cannot be misread
