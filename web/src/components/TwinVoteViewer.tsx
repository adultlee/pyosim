import { useMemo, useState } from 'react'
import type { TwinGroup, TwinData } from '../types'
import { partyColor, partyRankForRound } from '../partyColor'

const PAGE_SIZE = 50
const GRID_PREVIEW = 6 // 투표소 많을 때 우선 보여줄 칸 수
const CASE_PREVIEW = 3 // 후보쌍 카드에서 우선 보여줄 사례(득표값) 수

function parseCategory(cat: string) {
  const parts = cat.split('_')
  // 지방선거_시도지사_당일투표 / 총선_지역구_사전투표 / 대선_당일투표
  return { electionType: parts[0] ?? '', raceType: parts[1] ?? '', level: parts[2] ?? parts[1] ?? '' }
}

const LEVEL_LABEL: Record<string, string> = {
  당일투표: '당일투표',
  사전투표: '관내사전투표',
  관외사전투표: '관외사전투표',
  거소선상: '거소·선상투표',
  재외투표: '재외투표',
}

type EnrichedGroup = TwinGroup & { _level: string; _raceType: string; _electionType: string }

// 같은 후보쌍(이름)을 한 비교단위 안에서 묶은 묶음.
type PairGroup = {
  key: string
  candidates: [string, string]
  parties: Record<string, string>
  _level: string
  _raceType: string
  _electionType: string
  rank_pair: [number, number]
  group: Record<string, string | number | null>
  cases: EnrichedGroup[]
  totalLocations: number
  maxTotalVotes: number
  partyRankSum: number  // 두 후보 정당 서열의 합 (작을수록 양쪽 다 주요 정당)
}

// 반복 횟수 → 배지 강조 정도. 많을수록 진한 민트.
function countBadgeStyle(count: number): React.CSSProperties {
  if (count >= 10) {
    return { backgroundColor: 'var(--color-accent)', color: '#06251f', fontWeight: 700 }
  }
  if (count >= 4) {
    return { backgroundColor: 'rgba(61,189,167,0.22)', color: 'var(--color-accent-hover)', fontWeight: 600 }
  }
  return { backgroundColor: 'var(--color-surface-2)', color: 'var(--color-text-secondary)', fontWeight: 500 }
}

function PartyName({ party, name }: { party?: string; name: string }) {
  // 비례대표는 후보명=정당명이라 중복 표기를 피한다.
  const showParty = party && party !== name
  return (
    <span className="inline-flex items-center gap-1.5">
      {party && (
        <span
          className="inline-block rounded-sm shrink-0"
          style={{ width: 8, height: 8, backgroundColor: partyColor(party) }}
        />
      )}
      <span className="text-sm">
        {showParty && <span style={{ color: partyColor(party) }}>{party} </span>}
        <span className="font-semibold" style={{ color: showParty ? 'var(--color-text)' : partyColor(party) }}>{name}</span>
      </span>
    </span>
  )
}

// 한 사례(고정 득표값) = 동률 헤더 + 일치 동 그리드. (원래 GroupCard 디자인)
function CaseRow({ group, first, second, showSido }: {
  group: EnrichedGroup
  first: string
  second: string | undefined
  showSido: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const visibleLocations = expanded ? group.locations : group.locations.slice(0, GRID_PREVIEW)
  const hiddenCount = group.locations.length - visibleLocations.length

  return (
    <div style={{ borderTop: '1px solid var(--color-border)' }}>
      {/* 사례 헤더: 득표값 = 득표값 · 반복 횟수 배지 */}
      <div className="px-4 py-2.5 flex items-center gap-2.5 flex-wrap">
        <span className="font-mono tabular-nums font-semibold text-base" style={{ color: 'var(--color-text)' }}>
          {group.votes[first]?.toLocaleString()}
        </span>
        <span style={{ color: 'var(--color-text-tertiary)' }}>=</span>
        <span className="font-mono tabular-nums font-semibold text-base" style={{ color: 'var(--color-text)' }}>
          {second != null ? group.votes[second]?.toLocaleString() : ''}
        </span>
        <span className="px-2 py-0.5 rounded-md font-mono text-xs" style={countBadgeStyle(group.count)}>
          🔁 {group.count.toLocaleString()}곳
        </span>
      </div>

      {/* 일치 동 3컬럼 그리드 */}
      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
        style={{ borderTop: '1px solid var(--color-border)', gap: '1px', backgroundColor: 'var(--color-border)' }}
      >
        {visibleLocations.map((loc, locIdx) => (
          <div key={locIdx} className="px-4 py-2.5" style={{ backgroundColor: 'var(--color-surface)' }}>
            <div className="text-sm flex items-baseline gap-1.5">
              <span style={{ color: 'var(--color-text)' }}>{loc['읍면동']}</span>
              {showSido && loc['시도'] && (
                <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>{loc['시도']}</span>
              )}
              {!showSido && loc['구시군'] && (
                <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>{loc['구시군']}</span>
              )}
            </div>
            <div className="text-xs font-mono tabular-nums mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              {group.votes[first]?.toLocaleString()} = {second != null ? group.votes[second]?.toLocaleString() : ''}
              {typeof loc['투표수'] === 'number' && (
                <span style={{ color: 'var(--color-text-tertiary)' }}> · 투표 {loc['투표수'].toLocaleString()}중</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {hiddenCount > 0 && (
        <button
          onClick={() => setExpanded(true)}
          className="w-full py-2 text-xs transition-colors"
          style={{ borderTop: '1px solid var(--color-border)', color: 'var(--color-accent)' }}
        >
          나머지 {hiddenCount.toLocaleString()}곳 더보기 ▾
        </button>
      )}
      {expanded && group.locations.length > GRID_PREVIEW && (
        <button
          onClick={() => setExpanded(false)}
          className="w-full py-2 text-xs transition-colors"
          style={{ borderTop: '1px solid var(--color-border)', color: 'var(--color-text-tertiary)' }}
        >
          접기 ▴
        </button>
      )}
    </div>
  )
}

function PairCard({ pair }: { pair: PairGroup }) {
  const [casesExpanded, setCasesExpanded] = useState(false)

  const [first, second] = pair.candidates
  const parties = pair.parties

  const showSido = pair._electionType === '대선' || pair._electionType === '총선'

  // 그룹 헤더 지역 텍스트
  const metaParts: string[] = []
  const sido = pair.group['시도'] as string | undefined
  const gu = pair.group['구시군'] as string | undefined | null
  const districtName = pair.group['선거구명'] as string | undefined
  if (sido) metaParts.push(sido)
  if (gu) metaParts.push(gu)
  if (districtName) metaParts.push(districtName)

  const levelLabel = LEVEL_LABEL[pair._level] ?? pair._level
  const isSajeon = pair._level === '사전투표'

  const visibleCases = casesExpanded ? pair.cases : pair.cases.slice(0, CASE_PREVIEW)
  const hiddenCases = pair.cases.length - visibleCases.length

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ border: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface)' }}
    >
      {/* 후보쌍 헤더 */}
      <div className="px-4 pt-3 pb-2 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <PartyName party={parties[first]} name={first} />
          <span style={{ color: 'var(--color-text-tertiary)' }}>·</span>
          {second != null && <PartyName party={parties[second]} name={second} />}
        </div>
        <span className="px-2 py-0.5 rounded-md font-mono text-xs" style={countBadgeStyle(pair.totalLocations)}>
          🔁 총 {pair.totalLocations.toLocaleString()}곳 · {pair.cases.length.toLocaleString()}사례
        </span>
      </div>

      {/* 메타 한 줄 */}
      <div className="px-4 pb-2.5 flex items-center gap-2 flex-wrap text-xs">
        <span style={{ color: isSajeon ? 'var(--color-warning)' : 'var(--color-text-tertiary)' }}>{levelLabel}</span>
        <span style={{ color: 'var(--color-text-tertiary)' }}>·</span>
        <span style={{ color: 'var(--color-text-tertiary)' }}>{pair.rank_pair[0]}·{pair.rank_pair[1]}위</span>
        {metaParts.length > 0 && (
          <>
            <span style={{ color: 'var(--color-text-tertiary)' }}>·</span>
            <span style={{ color: 'var(--color-text-secondary)' }}>{metaParts.join(' ')}</span>
          </>
        )}
        {pair._raceType && pair._electionType !== '대선' && (
          <>
            <span style={{ color: 'var(--color-text-tertiary)' }}>·</span>
            <span style={{ color: 'var(--color-text-tertiary)' }}>{pair._raceType}</span>
          </>
        )}
      </div>

      {/* 득표값별 사례 */}
      {visibleCases.map((caseGroup, caseIdx) => (
        <CaseRow key={caseIdx} group={caseGroup} first={first} second={second} showSido={showSido} />
      ))}

      {hiddenCases > 0 && (
        <button
          onClick={() => setCasesExpanded(true)}
          className="w-full py-2 text-xs transition-colors"
          style={{ borderTop: '1px solid var(--color-border)', color: 'var(--color-accent)' }}
        >
          나머지 {hiddenCases.toLocaleString()}개 사례 더보기 ▾
        </button>
      )}
      {casesExpanded && pair.cases.length > CASE_PREVIEW && (
        <button
          onClick={() => setCasesExpanded(false)}
          className="w-full py-2 text-xs transition-colors"
          style={{ borderTop: '1px solid var(--color-border)', color: 'var(--color-text-tertiary)' }}
        >
          사례 접기 ▴
        </button>
      )}
    </div>
  )
}

export default function TwinVoteViewer({
  data,
  roundLabel,
}: {
  data: TwinData
  roundLabel: string
}) {
  const enriched = useMemo<EnrichedGroup[]>(() =>
    data.twins.map(group => {
      const { electionType: et, raceType, level } = parseCategory(group.category)
      return { ...group, _electionType: et, _raceType: raceType, _level: level }
    }), [data.twins])

  // 후보쌍(이름) 기준으로 묶음 — 득표값만 키에서 제외, 비교단위는 유지.
  const pairs = useMemo<PairGroup[]>(() => {
    const byKey = new Map<string, PairGroup>()
    for (const group of enriched) {
      const names = Object.entries(group.votes)
        .sort((left, right) => right[1] - left[1])
        .map(([cand]) => cand)
      const [first, second] = names
      if (second == null) continue
      const sortedPair = [first, second].sort()
      const groupId = JSON.stringify(group.group)
      const key = `${group.category}|${groupId}|${group.rank_pair.join('-')}|${sortedPair.join('=')}`

      const totalVotes = group.votes[first] + group.votes[second]
      let entry = byKey.get(key)
      if (!entry) {
        entry = {
          key,
          candidates: [first, second],
          parties: group.parties ?? {},
          _level: group._level,
          _raceType: group._raceType,
          _electionType: group._electionType,
          rank_pair: group.rank_pair,
          group: group.group,
          cases: [],
          totalLocations: 0,
          maxTotalVotes: 0,
          partyRankSum:
            partyRankForRound((group.parties ?? {})[first], group._electionType, group.group['선거_회차'] ?? '') +
            partyRankForRound((group.parties ?? {})[second], group._electionType, group.group['선거_회차'] ?? ''),
        }
        byKey.set(key, entry)
      }
      entry.cases.push(group)
      entry.totalLocations += group.count
      if (totalVotes > entry.maxTotalVotes) entry.maxTotalVotes = totalVotes
    }
    // 각 묶음 안 사례를 반복 많은 순으로 정렬
    for (const entry of byKey.values()) {
      entry.cases.sort((a, b) => b.count - a.count)
    }
    return Array.from(byKey.values())
  }, [enriched])

  const levels = useMemo(() => Array.from(new Set(pairs.map(p => p._level))), [pairs])
  const raceTypes = useMemo(() => Array.from(new Set(pairs.map(p => p._raceType).filter(Boolean))), [pairs])
  const rankPairs = useMemo(
    () => Array.from(new Set(pairs.map(p => p.rank_pair[0]))).sort((a, b) => a - b),
    [pairs],
  )

  const [selectedLevel, setSelectedLevel] = useState('all')
  const [selectedRace, setSelectedRace] = useState('all')
  const [selectedRank, setSelectedRank] = useState<number | 'all'>('all')
  const [sortBy, setSortBy] = useState<'count' | 'major' | 'cases' | 'votes'>('count')
  const [page, setPage] = useState(1)

  const filtered = useMemo(() => {
    setPage(1)
    const comparators: Record<typeof sortBy, (a: PairGroup, b: PairGroup) => number> = {
      count: (a, b) => b.totalLocations - a.totalLocations,
      votes: (a, b) => b.maxTotalVotes - a.maxTotalVotes,
      cases: (a, b) => b.cases.length - a.cases.length || b.totalLocations - a.totalLocations,
      major: (a, b) => a.partyRankSum - b.partyRankSum || b.totalLocations - a.totalLocations,
    }
    return pairs
      .filter(p => selectedLevel === 'all' || p._level === selectedLevel)
      .filter(p => selectedRace === 'all' || p._raceType === selectedRace)
      .filter(p => selectedRank === 'all' || p.rank_pair[0] === selectedRank)
      .sort(comparators[sortBy])
  }, [pairs, selectedLevel, selectedRace, selectedRank, sortBy])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const chipStyle = (active: boolean): React.CSSProperties => ({
    backgroundColor: active ? 'var(--color-accent)' : 'var(--color-surface-2)',
    color: active ? '#0C0F14' : 'var(--color-text-secondary)',
    border: `1px solid ${active ? 'transparent' : 'var(--color-border)'}`,
  })

  return (
    <div className="flex flex-col gap-5">
      {/* 필터 바 */}
      <div className="flex flex-col gap-2.5">
        {/* 정렬 한 줄 */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs w-16 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>정렬</span>
          <button onClick={() => setSortBy('count')} className="px-3 py-1 rounded-lg text-xs font-medium transition-colors" style={chipStyle(sortBy === 'count')}>
            반복 횟수 순
          </button>
          <button onClick={() => setSortBy('major')} className="px-3 py-1 rounded-lg text-xs font-medium transition-colors" style={chipStyle(sortBy === 'major')}>
            주요 정당 순
          </button>
          <button onClick={() => setSortBy('cases')} className="px-3 py-1 rounded-lg text-xs font-medium transition-colors" style={chipStyle(sortBy === 'cases')}>
            사례 수 순
          </button>
          <button onClick={() => setSortBy('votes')} className="px-3 py-1 rounded-lg text-xs font-medium transition-colors" style={chipStyle(sortBy === 'votes')}>
            득표 큰 순
          </button>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs w-16 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>투표 구분</span>
          {['all', ...levels].map(lv => (
            <button key={lv} onClick={() => setSelectedLevel(lv)} className="px-3 py-1 rounded-lg text-xs font-medium transition-colors" style={chipStyle(selectedLevel === lv)}>
              {lv === 'all' ? '전체' : (LEVEL_LABEL[lv] ?? lv)}
            </button>
          ))}

          {raceTypes.length > 0 && (
            <>
              <span className="text-xs ml-2 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>선거</span>
              <select
                value={selectedRace}
                onChange={ev => setSelectedRace(ev.target.value)}
                className="px-2.5 py-1 rounded-lg text-xs"
                style={{ backgroundColor: 'var(--color-surface-2)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}
              >
                <option value="all">전체</option>
                {raceTypes.map(rt => <option key={rt} value={rt}>{rt}</option>)}
              </select>
            </>
          )}

          {rankPairs.length > 1 && (
            <>
              <span className="text-xs ml-2 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>순위</span>
              <select
                value={String(selectedRank)}
                onChange={ev => setSelectedRank(ev.target.value === 'all' ? 'all' : Number(ev.target.value))}
                className="px-2.5 py-1 rounded-lg text-xs"
                style={{ backgroundColor: 'var(--color-surface-2)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}
              >
                <option value="all">전체</option>
                {rankPairs.map(rk => <option key={rk} value={rk}>{rk}·{rk + 1}위</option>)}
              </select>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {roundLabel} · 후보쌍 {filtered.length.toLocaleString()}개 · {({ count: '반복 횟수', major: '주요 정당', cases: '사례 수', votes: '득표 큰' } as const)[sortBy]} 순
        </span>
        {totalPages > 1 && (
          <span className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            {page} / {totalPages} 페이지
          </span>
        )}
      </div>

      {pageItems.length > 0 ? (
        <div className="flex flex-col gap-3">
          {pageItems.map(pair => (
            <PairCard key={pair.key} pair={pair} />
          ))}
        </div>
      ) : (
        <div className="text-center py-20 text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
          해당 조건의 데이터가 없습니다.
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded-lg text-xs font-medium transition-colors"
            style={{ backgroundColor: 'var(--color-surface-2)', color: page === 1 ? 'var(--color-text-tertiary)' : 'var(--color-text-secondary)', border: '1px solid var(--color-border)', opacity: page === 1 ? 0.4 : 1 }}
          >
            이전
          </button>
          {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
            let pageNum: number
            if (totalPages <= 7) pageNum = i + 1
            else if (page <= 4) pageNum = i + 1
            else if (page >= totalPages - 3) pageNum = totalPages - 6 + i
            else pageNum = page - 3 + i
            return (
              <button
                key={pageNum}
                onClick={() => setPage(pageNum)}
                className="px-3 py-1 rounded-lg text-xs font-mono transition-colors"
                style={chipStyle(page === pageNum)}
              >
                {pageNum}
              </button>
            )
          })}
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 rounded-lg text-xs font-medium transition-colors"
            style={{ backgroundColor: 'var(--color-surface-2)', color: page === totalPages ? 'var(--color-text-tertiary)' : 'var(--color-text-secondary)', border: '1px solid var(--color-border)', opacity: page === totalPages ? 0.4 : 1 }}
          >
            다음
          </button>
        </div>
      )}
    </div>
  )
}
