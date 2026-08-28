import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, existsSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { stripNotionHash, parseDate, parseTitleDate, readEntry, importExport } from './import-notion-export.mjs'

test('파일명에서 32자리 해시를 떼어낸다', () => {
  const r = stripNotionHash('@어제 3c931847b3e581a6ba35feddaeab08a3.md')
  assert.equal(r.title, '@어제')
  assert.equal(r.pageId, '3c931847b3e581a6ba35feddaeab08a3')
})

test('해시가 없으면 pageId 는 null', () => {
  assert.equal(stripNotionHash('제목만.md').pageId, null)
})

test('한글 날짜와 ISO 날짜를 모두 읽는다', () => {
  assert.equal(parseDate('기록일: 2025년 8월 6일'), '2025-08-06')
  assert.equal(parseDate('기록일: 2026년 12월 25일'), '2026-12-25')
  assert.equal(parseDate('기록일: 2026-08-27'), '2026-08-27')
  assert.equal(parseDate('기록일:'), null)
})

function fixture () {
  const dir = mkdtempSync(join(tmpdir(), 'nx-'))
  const w = (n, s) => writeFileSync(join(dir, n), s)
  w('@어제 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.md',
    '# @어제\n\n기록일: 2026년 8월 27일\n\n### 오늘 한 일\n\n- 정상 건\n')
  w('제목 없음 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.md',
    '# 제목 없음\n')
  w('@2026년 8월 27일 cccccccccccccccccccccccccccccccc.md',
    '# @2026년 8월 27일\n\n기록일: 2026년 8월 27일\n\n- 짧음\n')
  w('25 08 06 dddddddddddddddddddddddddddddddd.md',
    '# 25/08/06\n\n기록일: 2025년 8월 6일\n\n### 주요 업무\n\n- 옛 형식\n')
  mkdirSync(join(dir, '@어제'))
  writeFileSync(join(dir, '@어제', '회의록 eeee.md'), '# 회의록\n')
  mkdirSync(join(dir, '주인 없는 폴더'))
  writeFileSync(join(dir, '주인 없는 폴더', 'x.md'), '# x\n')
  return dir
}

test('날짜가 읽히면 날짜 경로로, 아니면 미확정으로 간다', () => {
  const exportDir = fixture()
  const outDir = mkdtempSync(join(tmpdir(), 'out-'))
  const r = importExport({ exportDir, outDir })

  assert.equal(r.written, 2)
  assert.ok(existsSync(join(outDir, 'logs/2026/08/2026-08-27.md')))
  assert.ok(existsSync(join(outDir, 'logs/2025/08/2025-08-06.md')))

  const body = readFileSync(join(outDir, 'logs/2026/08/2026-08-27.md'), 'utf8')
  assert.match(body, /^---\ndate: 2026-08-27\nsource: notion-import\n---\n/)
  assert.match(body, /### 오늘 한 일/)
  assert.match(body, /정상 건/, '같은 날짜면 본문이 긴 쪽이 채택된다')
  assert.doesNotMatch(body, /기록일:/, '속성 줄은 본문에 남지 않는다')
  assert.doesNotMatch(body, /^# /m, '제목 줄은 본문에 남지 않는다')

  const reasons = r.unresolved.map(u => u.reason).join(' | ')
  assert.match(reasons, /기록일 없음/)
  assert.match(reasons, /날짜 중복 2026-08-27 — 본문/)
  assert.ok(existsSync(join(outDir, 'logs/_unresolved')))
})

test('하위 폴더는 날짜 폴더로 따라가고, 주인 없는 폴더는 보고된다', () => {
  const exportDir = fixture()
  const outDir = mkdtempSync(join(tmpdir(), 'out-'))
  const r = importExport({ exportDir, outDir })

  assert.equal(r.attached, 1)
  assert.ok(existsSync(join(outDir, 'logs/2026/08/2026-08-27/회의록 eeee.md')))
  assert.deepEqual(r.orphanDirs, ['주인 없는 폴더'])
  assert.ok(existsSync(join(outDir, 'logs/_unresolved/_orphan-dirs/주인 없는 폴더/x.md')))
})

test('제목의 절대 날짜만 읽고 상대 표기는 무시한다', () => {
  assert.equal(parseTitleDate('@2026년 7월 1일'), '2026-07-01')
  assert.equal(parseTitleDate('@어제'), null)
  assert.equal(parseTitleDate('@지난주 화요일'), null)
  assert.equal(parseTitleDate('제목 없음'), null)
})

test('제목과 속성이 어긋나면 제목을 따르고 그 사실을 보고한다', () => {
  // 실제로 겪은 모양 그대로. 내용이 있는 페이지는 제목이 제 날짜인데 속성이 다른 날을
  // 가리키고, 그 날 자리는 속성만 맞는 빈 템플릿이 차지하고 있었다.
  const dir = mkdtempSync(join(tmpdir(), 'nx2-'))
  writeFileSync(join(dir, '@2026년 7월 1일 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.md'),
    '# @2026년 7월 1일\n\n기록일: 2026년 7월 3일\n\n### 오늘 한 일\n\n- 실제 내용이 길게 들어 있는 하루\n')
  writeFileSync(join(dir, '@오늘 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.md'),
    '# @오늘\n\n기록일: 2026년 7월 1일\n\n- [ ]  빈 템플릿\n')
  const out = mkdtempSync(join(tmpdir(), 'out2-'))
  const r = importExport({ exportDir: dir, outDir: out })

  assert.equal(r.written, 1)
  assert.match(readFileSync(join(out, 'logs/2026/07/2026-07-01.md'), 'utf8'), /실제 내용/,
    '제목이 7월 1일인 실제 내용이 7월 1일 자리를 차지한다')
  assert.equal(r.unresolved.length, 1)
  assert.match(r.unresolved[0].reason, /날짜 중복 2026-07-01/)
  assert.equal(r.conflicts.length, 1)
  assert.match(r.conflicts[0].note, /제목 2026-07-01/)
})
