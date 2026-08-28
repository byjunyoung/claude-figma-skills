# Google Calendar as the calendar

For a `sources.calendar_type` of `google`. The calendar id comes from `log.sources.calendar` —
`primary` is the account's own.

## A day's events

```
list_events   calendarId={log.sources.calendar}   timeMin={date}T00:00:00{local offset}   timeMax={date}T23:59:59{local offset}
```

In local time, ordered by start. Each event becomes time, title, and one or two key attendees.

**Drop** working-location entries, birthdays, and out-of-office blocks — they are not meetings,
and a day's file that lists them reads as a day of meetings that did not happen.

An all-day event carries a date, not a time. Show it first, without a time.

## Things that bite

- **`timeMin`/`timeMax` without an offset are read as UTC.** A day queried that way shifts by
  the local offset and picks up the evening before or drops the evening after
- **A declined event still lists.** Check the user's own response status and drop `declined`
