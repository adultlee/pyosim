import { useMemo, useState } from 'react'
import type { TwinGroup, TwinData } from '../types'

const PAGE_SIZE = 100

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

function GroupRows({ group }: { group: TwinGroup & { _level: string; _raceType: string; _electionType: string } }) {
  const candidates = Object.entries(group.votes)
    .sort((left, right) => right[1] - left[1])
    .map(([cand]) => cand)
  const isSajeon = group._level === '사전투표'
  const accentColor = isSajeon ? 'var(--color-warning)' : 'var(--color-text-tertiary)'

  // group 헤더 텍스트 구성
  const groupParts: string[] = []
  const sido = group.group['시도'] as string | undefined
  const gu = group.group['구시군'] as string | undefined | null
  const districtName = group.group['선거구명'] as string | undefined
  if (sido) groupParts.push(sido)
  if (gu) groupParts.push(gu)
  if (districtName) groupParts.push(districtName)

  // 위치 컬럼: 대선/총선은 시도+구시군+읍면동, 지방선거는 구시군+읍면동
  const showSido = group._electionType === '대선' || group._electionType === '총선'

  return (
    <>
      <tr style={{ backgroundColor: 'var(--color-surface-2)' }}>
        <td
          colSpan={showSido ? 3 : 2}
          className="px-3 py-2 text-xs"
          style={{ borderTop: `2px solid ${isSajeon ? 'var(--color-warning)' : 'var(--color-border)'}` }}
        >
          {groupParts.length > 0 && (
            <span style={{ color: 'var(--color-text-secondary)' }} className="mr-2">{groupParts.join(' ')}</span>
          )}
          {group._raceType && group._electionType !== '대선' && (
            <span style={{ color: 'var(--color-text-tertiary)' }}>{group._raceType}</span>
          )}
          <span className="ml-2 px-1.5 py-0.5 rounded font-mono" style={{ color: accentColor }}>
            {LEVEL_LABEL[group._level] ?? group._level}
          </span>
        </td>
        {candidates.map((cand, idx) => (
          <th
            key={cand}
            className="px-3 py-2 text-xs font-medium text-right"
            style={{
              color: idx === 0 ? 'var(--color-accent)' : 'var(--color-text-secondary)',
              borderTop: `2px solid ${isSajeon ? 'var(--color-warning)' : 'var(--color-border)'}`,
            }}
          >
            {cand}
          </th>
        ))}
      </tr>

      {group.locations.map((loc, locIdx) => (
        <tr key={locIdx}>
          {showSido && (
            <td className="px-3 py-1.5 text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
              {loc['시도']}
            </td>
          )}
          <td className="px-3 py-1.5 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            {loc['구시군']}
          </td>
          <td className="px-3 py-1.5 text-sm">{loc['읍면동']}</td>
          {candidates.map((cand, idx) => (
            <td
              key={cand}
              className="px-3 py-1.5 text-sm font-mono tabular-nums text-right"
              style={{ color: idx === 0 ? 'var(--color-accent)' : 'var(--color-text)' }}
            >
              {group.votes[cand].toLocaleString()}
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

export default function TwinVoteViewer({
  data,
  electionType,
  roundLabel,
}: {
  data: TwinData
  electionType: string
  roundLabel: string
}) {
  const enriched = useMemo(() =>
    data.twins.map(group => {
      const { electionType: et, raceType, level } = parseCategory(group.category)
      return { ...group, _electionType: et, _raceType: raceType, _level: level }
    }), [data.twins])

  const levels = useMemo(() => Array.from(new Set(enriched.map(g => g._level))), [enriched])
  const raceTypes = useMemo(() => Array.from(new Set(enriched.map(g => g._raceType).filter(Boolean))), [enriched])
  const rankPairs = useMemo(() => {
    const pairs = Array.from(new Set(enriched.map(g => g.rank_pair[0]))).sort((a, b) => a - b)
    return pairs
  }, [enriched])

  const [selectedLevel, setSelectedLevel] = useState('all')
  const [selectedRace, setSelectedRace] = useState('all')
  const [selectedRank, setSelectedRank] = useState<number | 'all'>('all')
  const [page, setPage] = useState(1)

  const filtered = useMemo(() => {
    setPage(1)
    return enriched
      .filter(g => selectedLevel === 'all' || g._level === selectedLevel)
      .filter(g => selectedRace === 'all' || g._raceType === selectedRace)
      .filter(g => selectedRank === 'all' || g.rank_pair[0] === selectedRank)
      .sort((a, b) => b.total_votes - a.total_votes)
  }, [enriched, selectedLevel, selectedRace, selectedRank])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const showSido = electionType === '대선' || electionType === '총선'

  return (
    <div className="flex flex-col gap-5">
      {/* 필터 바 */}
      <div className="flex flex-col gap-2.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs w-16 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>투표 구분</span>
          {['all', ...levels].map(lv => (
            <button key={lv} onClick={() => setSelectedLevel(lv)}
              className="px-3 py-1 rounded-lg text-xs font-medium transition-colors"
              style={{
                backgroundColor: selectedLevel === lv ? 'var(--color-accent)' : 'var(--color-surface-2)',
                color: selectedLevel === lv ? '#0C0F14' : 'var(--color-text-secondary)',
                border: `1px solid ${selectedLevel === lv ? 'transparent' : 'var(--color-border)'}`,
              }}>
              {lv === 'all' ? '전체' : (LEVEL_LABEL[lv] ?? lv)}
            </button>
          ))}
        </div>

        {raceTypes.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs w-16 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>선거 종류</span>
            {['all', ...raceTypes].map(rt => (
              <button key={rt} onClick={() => setSelectedRace(rt)}
                className="px-3 py-1 rounded-lg text-xs font-medium transition-colors"
                style={{
                  backgroundColor: selectedRace === rt ? 'var(--color-accent)' : 'var(--color-surface-2)',
                  color: selectedRace === rt ? '#0C0F14' : 'var(--color-text-secondary)',
                  border: `1px solid ${selectedRace === rt ? 'transparent' : 'var(--color-border)'}`,
                }}>
                {rt === 'all' ? '전체' : rt}
              </button>
            ))}
          </div>
        )}

        {rankPairs.length > 1 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs w-16 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>순위 쌍</span>
            {(['all', ...rankPairs] as Array<'all' | number>).map(rk => (
              <button key={String(rk)} onClick={() => setSelectedRank(rk)}
                className="px-3 py-1 rounded-lg text-xs font-medium transition-colors"
                style={{
                  backgroundColor: selectedRank === rk ? 'var(--color-accent)' : 'var(--color-surface-2)',
                  color: selectedRank === rk ? '#0C0F14' : 'var(--color-text-secondary)',
                  border: `1px solid ${selectedRank === rk ? 'transparent' : 'var(--color-border)'}`,
                }}>
                {rk === 'all' ? '전체' : `${rk}·${(rk as number) + 1}위`}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {roundLabel} · {filtered.length.toLocaleString()}개 그룹 · 두 후보 합 득표 기준 정렬
        </span>
        {totalPages > 1 && (
          <span className="text-xs font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            {page} / {totalPages} 페이지
          </span>
        )}
      </div>

      {pageItems.length > 0 && (
        <div
          className="rounded-xl overflow-x-auto"
          style={{ border: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface)' }}
        >
          <table className="w-full border-collapse">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                {showSido && (
                  <th className="px-3 py-2 text-xs font-medium text-left" style={{ color: 'var(--color-text-tertiary)' }}>시·도</th>
                )}
                <th className="px-3 py-2 text-xs font-medium text-left" style={{ color: 'var(--color-text-tertiary)' }}>구·시·군</th>
                <th className="px-3 py-2 text-xs font-medium text-left" style={{ color: 'var(--color-text-tertiary)' }}>읍·면·동</th>
                <th className="px-3 py-2 text-xs font-medium text-right" style={{ color: 'var(--color-text-tertiary)' }}>후보자별 득표수 →</th>
              </tr>
            </thead>
            <tbody>
              {pageItems.map((group, idx) => (
                <GroupRows key={idx} group={group} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pageItems.length === 0 && (
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
            style={{
              backgroundColor: 'var(--color-surface-2)',
              color: page === 1 ? 'var(--color-text-tertiary)' : 'var(--color-text-secondary)',
              border: '1px solid var(--color-border)',
              opacity: page === 1 ? 0.4 : 1,
            }}
          >
            이전
          </button>
          {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
            let pageNum: number
            if (totalPages <= 7) {
              pageNum = i + 1
            } else if (page <= 4) {
              pageNum = i + 1
            } else if (page >= totalPages - 3) {
              pageNum = totalPages - 6 + i
            } else {
              pageNum = page - 3 + i
            }
            return (
              <button
                key={pageNum}
                onClick={() => setPage(pageNum)}
                className="px-3 py-1 rounded-lg text-xs font-mono transition-colors"
                style={{
                  backgroundColor: page === pageNum ? 'var(--color-accent)' : 'var(--color-surface-2)',
                  color: page === pageNum ? '#0C0F14' : 'var(--color-text-secondary)',
                  border: `1px solid ${page === pageNum ? 'transparent' : 'var(--color-border)'}`,
                }}
              >
                {pageNum}
              </button>
            )
          })}
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 rounded-lg text-xs font-medium transition-colors"
            style={{
              backgroundColor: 'var(--color-surface-2)',
              color: page === totalPages ? 'var(--color-text-tertiary)' : 'var(--color-text-secondary)',
              border: '1px solid var(--color-border)',
              opacity: page === totalPages ? 0.4 : 1,
            }}
          >
            다음
          </button>
        </div>
      )}
    </div>
  )
}
