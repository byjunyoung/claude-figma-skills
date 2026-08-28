# Slack as the chat source

For a `sources.chat_type` of `slack`. The channel and app ids the calls need come from
`log.sources` — `chat_channels`, `notes_channel`, `notes_exclude_apps`. These are the calls
`/pm:task-draft` and `/pm:log` were written against; the warnings are the ones they hit.

## A thread from a link

```
slack_read_thread   channel_id={from the permalink}  thread_ts={from the permalink}
```

A permalink to a *reply* carries the reply's timestamp. Resolve the thread root first —
`thread_ts` in the message — and read from there, or the shape of the discussion is lost and
only the tail comes back. Attached images and video arrive as filenames; they count as
context, never as evidence.

## A channel on a day

```
slack_read_channel   channel_id={id}   oldest={date 00:00 local, as epoch}   latest={date 23:59:59}
```

Page with the cursor until it is empty. A day in a busy channel is more than one page.

## Messages about me on a day

```
slack_search_public_and_private   query="from:@me on:{YYYY-MM-DD}"
slack_search_public_and_private   query="@me on:{YYYY-MM-DD}"
```

**Search caps its response size, and an over-large request fails outright and returns
nothing** — which reads as a quiet day. Ask for concise output without surrounding context,
and page rather than widening a single call.

## My notes channel

`log.sources.notes_channel` — a channel only you write in, usually your own direct message to
yourself. Read it as a channel on a day. **An app that posts there on your behalf is
attributed to the app** — its user id shows as the author — and `log.sources.notes_exclude_apps`
lists the ids to drop. Nothing you did not type belongs in your notes.

## Permalinks and names

```
slack_read_user_profile   user_id={id}     → display name, for a quote's sender
```

A message's permalink is `https://{workspace}.slack.com/archives/{channel}/p{ts without the dot}`.
Record a quote with the time, the body as written, and the permalink beside it.

## Things that bite

- **Retention expires.** A log that links a message nobody can open a year later has recorded
  nothing. Carry the text across; keep the permalink as a citation, not as the record
- **The search cap fails silently.** It does not return a partial page; it returns nothing
- **`on:` is the workspace's day, not yours.** Where the two differ, bound the query a day wider
  and drop what falls outside after the fetch
