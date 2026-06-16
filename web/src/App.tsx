import { useEffect, useState } from 'react'
import { GitMerge } from 'lucide-react'
import TwinVoteViewer from './components/TwinVoteViewer'
import type { TwinData, TwinIndex } from './types'

const ELECTION_ORDER = ['지방선거', '총선', '대선']

export default function App() {
  const [index, setIndex] = useState<TwinIndex | null>(null)
  const [selectedElection, setSelectedElection] = useState<string>('지방선거')
  const [selectedRound, setSelectedRound] = useState<string | null>(null)
  const [data, setData] = useState<TwinData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/twin_votes_index.json')
      .then(res => res.json())
      .then((idx: TwinIndex) => {
        setIndex(idx)
        const electionKeys = ELECTION_ORDER.filter(k => k in idx.elections)
        const firstElection = electionKeys[0] ?? Object.keys(idx.elections)[0]
        setSelectedElection(firstElection)
        const rounds = idx.elections[firstElection]?.rounds ?? []
        setSelectedRound(rounds[rounds.length - 1] ?? null)
      })
      .catch(() => setError('인덱스를 불러오지 못했습니다.'))
  }, [])

  useEffect(() => {
    if (selectedRound === null || !selectedElection) return
    setLoading(true)
    setData(null)
    const safe = selectedRound.replace(/ /g, '_')
    fetch(`/twin_votes_${selectedElection}_${safe}.json`)
      .then(res => res.json())
      .then((d: TwinData) => { setData(d); setLoading(false) })
      .catch(() => { setError('데이터를 불러오지 못했습니다.'); setLoading(false) })
  }, [selectedElection, selectedRound])

  function handleElectionChange(election: string) {
    if (!index) return
    setSelectedElection(election)
    const rounds = index.elections[election]?.rounds ?? []
    setSelectedRound(rounds[rounds.length - 1] ?? null)
    setData(null)
  }

  const currentElectionIndex = index?.elections[selectedElection]
  const electionKeys = index ? ELECTION_ORDER.filter(k => k in index.elections) : []

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text)' }}>
      <header
        className="sticky top-0 z-10 px-6 py-3 flex items-center gap-3"
        style={{ backgroundColor: 'var(--color-bg)', borderBottom: '1px solid var(--color-border)' }}
      >
        <GitMerge size={16} style={{ color: 'var(--color-accent)' }} />
        <span className="text-sm font-semibold tracking-tight">표심</span>
        <span
          className="text-xs px-2 py-0.5 rounded font-mono"
          style={{ backgroundColor: 'var(--color-surface-2)', color: 'var(--color-text-tertiary)' }}
        >
          쌍둥이 득표 분석
        </span>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        <div className="mb-6 flex flex-col gap-3">
          <div>
            <h1 className="text-lg font-semibold mb-1">쌍둥이 득표</h1>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              서로 다른 두 읍면동에서 <strong>같은 두 후보가 같은 득표수</strong>를 받은 사례.
              저득표 노이즈를 빼기 위해 각 후보 10표 이상인 동률만 보며, 같은 투표 구분(사전·당일 등)끼리 비교합니다.
            </p>
          </div>
          <div
            className="rounded-lg px-4 py-3 text-sm leading-relaxed"
            style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}
          >
            <p className="mb-1" style={{ color: 'var(--color-text)' }}>왜 보는가 — 9회 지방선거(2026) 사전투표 동일 득표 논란</p>
            인천 송도1·2동 관내사전투표에서 인천시장 박찬대 3,030표·유정복 1,440표가 두 동에서 똑같이 나오고,
            전남 신안 하의면과 여수 삼일동에서도 민형배 506표·이정현 42표가 일치하면서
            "서로 다른 투표소가 어떻게 1의 자리까지 같으냐"는 의혹이 제기됐습니다.
            이 표는 <strong>과거 선거(지방선거 3~9회, 총선 16~22대, 대선 14~21대)에서 같은 일이 얼마나 있었는지</strong>를
            선관위 공식 개표 데이터 그대로 보여주는 맥락 자료입니다. 부정선거 주장도, 반박도 아닙니다.
          </div>
        </div>

        {error && (
          <div
            className="rounded-lg p-4 text-sm"
            style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-error)', border: '1px solid var(--color-error)' }}
          >
            {error}
          </div>
        )}

        {index && (
          <div className="flex flex-col gap-3 mb-6">
            {/* 선거 종류 탭 */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs w-16 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>선거 종류</span>
              {electionKeys.map(election => (
                <button
                  key={election}
                  onClick={() => handleElectionChange(election)}
                  className="px-3 py-1 rounded-lg text-xs font-medium transition-colors"
                  style={{
                    backgroundColor: selectedElection === election ? 'var(--color-accent)' : 'var(--color-surface-2)',
                    color: selectedElection === election ? '#0C0F14' : 'var(--color-text-secondary)',
                    border: `1px solid ${selectedElection === election ? 'transparent' : 'var(--color-border)'}`,
                  }}
                >
                  {election}
                </button>
              ))}
            </div>

            {/* 회차 탭 */}
            {currentElectionIndex && selectedRound !== null && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs w-16 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>선거 회차</span>
                {currentElectionIndex.rounds.map(round => (
                  <button
                    key={round}
                    onClick={() => setSelectedRound(round)}
                    className="px-3 py-1 rounded-lg text-xs font-medium transition-colors"
                    style={{
                      backgroundColor: selectedRound === round ? 'var(--color-accent)' : 'var(--color-surface-2)',
                      color: selectedRound === round ? '#0C0F14' : 'var(--color-text-secondary)',
                      border: `1px solid ${selectedRound === round ? 'transparent' : 'var(--color-border)'}`,
                    }}
                  >
                    {currentElectionIndex.roundLabels[round] ?? round}{' '}
                    <span className="font-mono opacity-60">({(currentElectionIndex.counts[round] ?? 0).toLocaleString()})</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {loading && (
          <div className="text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
            데이터 로딩 중...
          </div>
        )}

        {data && selectedRound !== null && (
          <TwinVoteViewer data={data} roundLabel={currentElectionIndex?.roundLabels[selectedRound] ?? selectedRound} />
        )}
      </main>

      <footer
        className="mt-12 px-6 py-8"
        style={{ borderTop: '1px solid var(--color-border)', color: 'var(--color-text-tertiary)' }}
      >
        <div className="max-w-7xl mx-auto flex flex-col gap-3 text-xs leading-relaxed">
          <p>
            <strong style={{ color: 'var(--color-text-secondary)' }}>데이터 출처</strong> · 중앙선거관리위원회
            선거통계시스템(info.nec.go.kr)의 공식 개표결과를 가공한 자료입니다.
          </p>
          <p>
            <strong style={{ color: 'var(--color-text-secondary)' }}>쌍둥이 득표란</strong> · 같은 비교 단위 안에서
            서로 다른 두 읍면동이 같은 두 후보에게 같은 득표수를 준 경우입니다. 저득표 노이즈를 빼기 위해 각 후보
            10표 이상인 동률만 집계하며, 같은 투표 구분끼리 비교합니다.{' '}
            <a
              href="https://github.com/adultlee/pyosim/blob/main/docs/twin-vote-spec.md"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--color-accent)' }}
            >
              정의·방법론 자세히 →
            </a>
          </p>
          <p style={{ color: 'var(--color-text-tertiary)' }}>
            이 자료는 통계적 이상이나 부정선거를 <strong>주장하지도, 반박하지도 않습니다.</strong> "과거 선거에서 이런
            일이 얼마나 자주 있었나"를 빈도로 보여주는 중립적 맥락 자료이며, 확률 계산은 하지 않습니다.
          </p>
        </div>
      </footer>
    </div>
  )
}
