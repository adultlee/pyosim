import type { ElectionIndex } from '../types'

type Props = {
  electionIndex: ElectionIndex
  selectedRound: string
  onSelect: (round: string) => void
}

// 선택된 선거종류의 회차별 쌍둥이 그룹 수를 작은 막대로 (라이브러리 미사용).
// rounds_meta.groupCount 우선, 없으면 counts 폴백. 막대 클릭 → 회차 전환.
export default function HeroTrend({ electionIndex, selectedRound, onSelect }: Props) {
  const values = electionIndex.rounds.map(round => {
    const fromMeta = electionIndex.rounds_meta?.[round]?.groupCount
    return fromMeta ?? electionIndex.counts[round] ?? 0
  })
  const max = Math.max(1, ...values)

  return (
    <div
      className="rounded-xl px-4 py-3"
      style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
    >
      <div className="text-xs mb-2" style={{ color: 'var(--color-text-tertiary)' }}>
        회차별 동일 득표 사례 수
      </div>
      <div className="flex items-end gap-2" style={{ height: 72 }}>
        {electionIndex.rounds.map((round, index) => {
          const value = values[index]
          const isSelected = round === selectedRound
          const heightPct = Math.max(4, Math.round((value / max) * 100))
          return (
            <button
              key={round}
              onClick={() => onSelect(round)}
              title={`${electionIndex.roundLabels[round] ?? round}: ${value.toLocaleString()}건`}
              className="flex-1 flex flex-col items-center justify-end gap-1 group"
              style={{ height: '100%' }}
            >
              <span
                className="font-mono tabular-nums text-[10px]"
                style={{ color: isSelected ? 'var(--color-accent)' : 'var(--color-text-tertiary)' }}
              >
                {value.toLocaleString()}
              </span>
              <span
                className="w-full rounded-sm transition-colors"
                style={{
                  height: `${heightPct}%`,
                  backgroundColor: isSelected ? 'var(--color-accent)' : 'var(--color-surface-2)',
                  border: `1px solid ${isSelected ? 'transparent' : 'var(--color-border)'}`,
                }}
              />
              <span
                className="text-[10px] truncate w-full text-center"
                style={{ color: isSelected ? 'var(--color-text)' : 'var(--color-text-tertiary)' }}
              >
                {electionIndex.roundLabels[round] ?? round}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
