# Google Calendar as the calendar

connector: Google Calendar
roles: calendar

For a `sources.calendar_type` of `google`. The calendar id comes from `log.sources.calendar` —
`primary` is the account's own. Run against a real calendar on 2026-08-29.

## A day's events

```
list_events   calendarId={log.sources.calendar}   startTime={date}T00:00:00{offset}   endTime={date}T23:59:59{offset}
              timeZone={IANA zone, e.g. Asia/Seoul}   orderBy=startTime   eventType=["DEFAULT"]   pageSize=50
```

Each event becomes time, title, and one or two key attendees. `nextPageToken` goes back in as
`pageToken` for the next page.

**`eventType` is the filter.** Left empty, the tool returns `DEFAULT`, `OUT_OF_OFFICE`,
`FOCUS_TIME` and `FROM_GMAIL` — working-location and birthday entries are already out, but
out-of-office and focus blocks are in, and they are not meetings. `["DEFAULT"]` is a day of
meetings.

An all-day event carries a date, not a time. Show it first, without a time.

## Things that bite

- **A day with no events returns only the calendar's header** — summary, time zone, reminders —
  and no `events` key at all. That is an empty day, not an error; a day with a meeting on it
  came back through the same bounds
- **Pass `timeZone`, or an offset on both bounds.** A bare timestamp is resolved in the
  calendar's zone, which is not always yours
- **A declined event still lists.** Your own entry in `attendees` carries `self: true` and a
  `responseStatus` — `accepted`, `needsAction`, `declined`. Drop `declined`
