// Converts a Notion "Markdown & CSV" export of a daily-log database into
// one file per day under <outDir>/logs/YYYY/MM/YYYY-MM-DD.md
//
// The date comes from the `기록일`-style property Notion writes into the body,
// not from the file name — exported titles can be rendered relative to the
// export moment ("@yesterday", "@Monday") and are unusable as a key.
import { readdirSync, readFileSync, writeFileSync, mkdirSync, cpSync, statSync } from 'node:fs'
import { join, dirname, basename } from 'node:path'

const HASH = /^(.*?)[ _]([0-9a-f]{32})$/
const KO_DATE = /(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일/
const ISO_DATE = /(\d{4})-(\d{2})-(\d{2})/

export function stripNotionHash (filename) {
  const base = filename.replace(/\.md$/, '')
  const m = base.match(HASH)
  if (!m) return { title: base, pageId: null }
  return { title: m[1].trim(), pageId: m[2] }
}

// Only an absolute date counts. Notion renders a date mention relative to the
// moment of export ("@yesterday", "@Monday"), so a title that does not carry a
// full date tells you nothing about which day the page is.
export function parseTitleDate (title) {
  const ko = title.match(KO_DATE)
  if (!ko) return null
  const [, y, m, d] = ko
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

export function parseDate (text) {
  const ko = text.match(KO_DATE)
  if (ko) {
    const [, y, m, d] = ko
    return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
  }
  const iso = text.match(ISO_DATE)
  return iso ? iso[0] : null
}

// The property block sits between the title line and the first blank line that
// follows it. Only that block is searched, so a date mentioned in the prose
// cannot be mistaken for the record date.
export function readEntry (path, dateProperty) {
  const raw = readFileSync(path, 'utf8')
  const lines = raw.split('\n')
  let i = 0
  if (lines[i]?.startsWith('# ')) i++
  while (i < lines.length && lines[i].trim() === '') i++

  let date = null
  const propStart = i
  while (i < lines.length && lines[i].trim() !== '') {
    const line = lines[i]
    if (line.startsWith(dateProperty + ':')) date = parseDate(line)
    i++
  }
  const consumed = date !== null
  const body = lines.slice(consumed ? i : propStart).join('\n').replace(/^\n+/, '')
  return { date, body }
}

function frontMatter (date) {
  return `---\ndate: ${date}\nsource: notion-import\n---\n\n`
}

export function importExport ({ exportDir, outDir, dateProperty = '기록일' }) {
  const entries = readdirSync(exportDir, { withFileTypes: true })
  const files = entries.filter(e => e.isFile() && e.name.endsWith('.md')).map(e => e.name).sort()
  const dirs = new Set(entries.filter(e => e.isDirectory()).map(e => e.name))

  // Read everything first. Which of two pages claiming the same day wins must be
  // decided on content, not on whatever order the file names happened to sort in.
  // Two independent claims on the date: the title and the property. Where they
  // disagree the title wins — the title is what a person edits and reads every
  // day, while the property is written by automation that can set the same value
  // across several pages at once. Every disagreement is reported either way.
  const read = files.map(file => {
    const { title } = stripNotionHash(file)
    const { date: propDate, body } = readEntry(join(exportDir, file), dateProperty)
    const titleDate = parseTitleDate(title)
    const conflict = titleDate && propDate && titleDate !== propDate
      ? `제목 ${titleDate} · ${dateProperty} ${propDate} — 제목을 따름`
      : null
    return { file, title, date: titleDate ?? propDate, body, conflict }
  })

  const unresolved = []
  const conflicts = read.filter(e => e.conflict).map(e => ({ file: e.file, note: e.conflict }))
  const byDate = new Map()
  for (const e of read) {
    if (!e.date) { unresolved.push({ file: e.file, title: e.title, reason: `${dateProperty} 없음` }); continue }
    if (!byDate.has(e.date)) byDate.set(e.date, [])
    byDate.get(e.date).push(e)
  }

  let written = 0
  let attached = 0

  for (const [date, group] of byDate) {
    group.sort((a, b) => b.body.trim().length - a.body.trim().length)
    const [winner, ...rest] = group
    for (const loser of rest) {
      unresolved.push({
        file: loser.file,
        title: loser.title,
        reason: `날짜 중복 ${date} — 본문 ${loser.body.trim().length}자, 채택된 쪽 ${winner.body.trim().length}자 (${winner.file})`
      })
    }

    const [y, m] = date.split('-')
    const dest = join(outDir, 'logs', y, m, `${date}.md`)
    mkdirSync(dirname(dest), { recursive: true })
    writeFileSync(dest, frontMatter(date) + winner.body.trimEnd() + '\n')
    written++

    // A page with children exports as a sibling directory named after its title.
    if (dirs.has(winner.title)) {
      cpSync(join(exportDir, winner.title), join(outDir, 'logs', y, m, date), { recursive: true })
      dirs.delete(winner.title)
      attached++
    }
  }

  for (const u of unresolved) {
    const dest = join(outDir, 'logs', '_unresolved', u.file)
    mkdirSync(dirname(dest), { recursive: true })
    cpSync(join(exportDir, u.file), dest)
    if (dirs.has(u.title)) {
      cpSync(join(exportDir, u.title), join(outDir, 'logs', '_unresolved', u.title), { recursive: true })
      dirs.delete(u.title)
    }
  }

  // Directories nothing claimed. Never dropped silently.
  const orphanDirs = [...dirs]
  for (const d of orphanDirs) {
    cpSync(join(exportDir, d), join(outDir, 'logs', '_unresolved', '_orphan-dirs', d), { recursive: true })
  }

  return { written, attached, unresolved, conflicts, orphanDirs }
}
