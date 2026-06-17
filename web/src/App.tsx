import { useEffect, useMemo, useState } from 'react'
import { GitMerge } from 'lucide-react'
import TwinVoteViewer from './components/TwinVoteViewer'
import About from './components/About'
import Landing from './components/Landing'
import HeroTrend from './components/HeroTrend'
import AnimatedNumber from './components/AnimatedNumber'
import AdBanner from './components/AdBanner'
import { computeRoundStats } from './twinStats'
import { partyColor } from './partyColor'
import type { TwinData, TwinIndex, VotesCsvIndex } from './types'

const ELECTION_ORDER = ['지방선거', '총선', '대선']

export default function App() {
  const [index, setIndex] = useState<TwinIndex | null>(null)
  const [selectedElection, setSelectedElection] = useState<string>('지방선거')
  const [selectedRound, setSelectedRound] = useState<string | null>(null)
  const [data, setData] = useState<TwinData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [route, setRoute] = useState<string>(() => window.location.hash)
  const [votesCsvIndex, setVotesCsvIndex] = useState<VotesCsvIndex | null>(null)

  useEffect(() => {
    const onHashChange = () => setRoute(window.location.hash)
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

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
    fetch('/votes_csv_index.json')
      .then(response => (response.ok ? response.json() : null))
      .then(setVotesCsvIndex)
      .catch(() => setVotesCsvIndex(null))  // 매니페스트 없으면 버튼만 숨김
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
  const stats = useMemo(() => computeRoundStats(data), [data])
  const roundLabel = (selectedRound != null && currentElectionIndex?.roundLabels[selectedRound]) || selectedRound || ''

  // 선택 회차의 index 집계(즉시) — 회차 JSON 로드 전에도 카드 수치를 보여준다.
  const roundMeta = (selectedRound != null && currentElectionIndex?.rounds_meta?.[selectedRound]) || null
  // 카드 4개 소스: 회차 JSON 로드되면 stats, 아니면 roundMeta 폴백.
  const cardStats = data
    ? { pairCount: stats.pairCount, groupCount: stats.groupCount, totalLocations: stats.totalLocations, topPair: stats.topPair }
    : roundMeta

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text)' }}>
      <header
        className="sticky top-0 z-20"
        style={{ backgroundColor: 'var(--color-bg)', borderBottom: '1px solid var(--color-border)' }}
      >
        {/* 1줄: 로고 + 선거 종류 + nav */}
        <div className="max-w-3xl mx-auto px-6 pt-3 pb-2 flex items-center gap-3 flex-wrap">
          <a href="#" className="flex items-center gap-2 no-underline shrink-0" style={{ color: 'inherit' }}>
            <GitMerge size={16} style={{ color: 'var(--color-accent)' }} />
            <span className="text-sm font-semibold tracking-tight">표심</span>
          </a>
          {route === '#explore' && index && (
            <div className="flex items-center gap-1.5 flex-wrap">
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
          )}
          <nav className="ml-auto shrink-0 flex items-center gap-2">
            <a
              href="https://www.woomunhyundap.com/?utm_source=pyosim&utm_medium=header"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:inline text-xs"
              style={{ color: 'var(--color-text-tertiary)' }}
            >
              우문현답 ↗
            </a>
            <a
              href="#about"
              className="text-xs px-3 py-1.5 rounded-lg"
              style={{
                backgroundColor: route === '#about' ? 'var(--color-accent)' : 'var(--color-surface-2)',
                color: route === '#about' ? '#0C0F14' : 'var(--color-text-secondary)',
                border: '1px solid var(--color-border)',
              }}
            >
              출처·계산 방법
            </a>
          </nav>
        </div>

        {/* 2줄: 회차 탭 */}
        {route === '#explore' && currentElectionIndex && selectedRound !== null && (
          <div className="max-w-3xl mx-auto px-6 pb-2.5 flex items-center gap-1.5 flex-wrap">
            {currentElectionIndex.rounds.map(round => (
              <button
                key={round}
                onClick={() => setSelectedRound(round)}
                className="px-2.5 py-1 rounded-lg text-xs font-medium transition-colors"
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
      </header>

      {route === '#about' ? (
        <About onBack={() => { window.location.hash = '' }} />
      ) : route !== '#explore' ? (
        <Landing index={index} electionKeys={electionKeys} onPickElection={handleElectionChange} />
      ) : (
      <>
      <main className="max-w-3xl mx-auto px-6 py-6">
        {error && (
          <div
            className="rounded-lg p-4 text-sm"
            style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-error)', border: '1px solid var(--color-error)' }}
          >
            {error}
          </div>
        )}

        {/* (B) 회차 추세 막대 */}
        {currentElectionIndex && selectedRound !== null && (
          <div className="mb-6">
            <HeroTrend
              electionIndex={currentElectionIndex}
              selectedRound={selectedRound}
              onSelect={setSelectedRound}
            />
          </div>
        )}

        {/* (C) 선택 회차 핵심 수치 — index 집계로 즉시 표시(로드 전 폴백) */}
        {cardStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-6">
            <div className="rounded-xl px-4 py-3" style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
              <div className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>{roundLabel} 쌍둥이 후보쌍</div>
              <div className="flex items-baseline mt-0.5" style={{ color: 'var(--color-accent)' }}>
                <AnimatedNumber value={cardStats.pairCount} className="font-mono tabular-nums text-2xl font-bold" />
                <span className="text-sm font-normal" style={{ color: 'var(--color-text-tertiary)' }}> 쌍</span>
              </div>
            </div>
            <div className="rounded-xl px-4 py-3" style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
              <div className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>동일 득표 사례</div>
              <div className="flex items-baseline mt-0.5" style={{ color: 'var(--color-text)' }}>
                <AnimatedNumber value={cardStats.groupCount} className="font-mono tabular-nums text-2xl font-bold" />
                <span className="text-sm font-normal" style={{ color: 'var(--color-text-tertiary)' }}> 건</span>
              </div>
            </div>
            <div className="rounded-xl px-4 py-3" style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
              <div className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>일치한 투표소 총합</div>
              <div className="flex items-baseline mt-0.5" style={{ color: 'var(--color-text)' }}>
                <AnimatedNumber value={cardStats.totalLocations} className="font-mono tabular-nums text-2xl font-bold" />
                <span className="text-sm font-normal" style={{ color: 'var(--color-text-tertiary)' }}> 곳</span>
              </div>
            </div>
            <div className="rounded-xl px-4 py-3" style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
              <div className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>최다 반복 후보쌍</div>
              {cardStats.topPair ? (
                <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block rounded-sm shrink-0" style={{ width: 7, height: 7, backgroundColor: partyColor(cardStats.topPair.parties[0]) }} />
                    <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>{cardStats.topPair.names[0]}</span>
                  </span>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>·</span>
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block rounded-sm shrink-0" style={{ width: 7, height: 7, backgroundColor: partyColor(cardStats.topPair.parties[1]) }} />
                    <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>{cardStats.topPair.names[1]}</span>
                  </span>
                  <span className="font-mono tabular-nums text-base font-bold ml-0.5" style={{ color: 'var(--color-warning)' }}>
                    {cardStats.topPair.locations.toLocaleString()}곳
                  </span>
                </div>
              ) : (
                <div className="text-sm mt-1.5" style={{ color: 'var(--color-text-tertiary)' }}>—</div>
              )}
            </div>
          </div>
        )}

        {/* (D) 최다 반복 후보쌍 상위 N — 회차 JSON 로드 후 */}
        {data && stats.topPairs.length > 1 && (
          <div
            className="rounded-xl px-4 py-3 mb-6"
            style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
          >
            <div className="text-xs mb-2" style={{ color: 'var(--color-text-tertiary)' }}>
              {roundLabel} 최다 반복 후보쌍 상위 {stats.topPairs.length}
            </div>
            <ol className="flex flex-col gap-1.5">
              {stats.topPairs.map((pair, rank) => (
                <li key={`${pair.names[0]}=${pair.names[1]}-${rank}`} className="flex items-center gap-1.5 text-sm">
                  <span className="font-mono tabular-nums w-4 shrink-0" style={{ color: 'var(--color-text-tertiary)' }}>{rank + 1}</span>
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block rounded-sm shrink-0" style={{ width: 7, height: 7, backgroundColor: partyColor(pair.parties[0]) }} />
                    <span className="font-semibold" style={{ color: 'var(--color-text)' }}>{pair.names[0]}</span>
                  </span>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>·</span>
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block rounded-sm shrink-0" style={{ width: 7, height: 7, backgroundColor: partyColor(pair.parties[1]) }} />
                    <span className="font-semibold" style={{ color: 'var(--color-text)' }}>{pair.names[1]}</span>
                  </span>
                  <span className="font-mono tabular-nums ml-auto font-bold" style={{ color: 'var(--color-warning)' }}>
                    {pair.locations.toLocaleString()}곳
                  </span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {loading && (
          <div className="text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
            데이터 로딩 중...
          </div>
        )}

        {data && selectedRound !== null && (
          <TwinVoteViewer
            data={data}
            roundLabel={currentElectionIndex?.roundLabels[selectedRound] ?? selectedRound}
            electionType={selectedElection}
            round={selectedRound}
            csvMeta={votesCsvIndex?.[selectedElection]?.[selectedRound] ?? null}
          />
        )}
      </main>

      <footer
        className="mt-12 px-6 py-8"
        style={{ borderTop: '1px solid var(--color-border)', color: 'var(--color-text-tertiary)' }}
      >
        <div className="max-w-3xl mx-auto flex flex-col gap-3 text-xs leading-relaxed">
          <p>
            <strong style={{ color: 'var(--color-text-secondary)' }}>데이터 출처</strong> · 중앙선거관리위원회
            자료실 게시판과 선거통계시스템의 공식 개표결과를 가공한 자료입니다.{' '}
            <a href="#about" style={{ color: 'var(--color-accent)' }}>출처·계산 방법 →</a>
          </p>
          <p>
            <strong style={{ color: 'var(--color-text-secondary)' }}>쌍둥이 득표란</strong> · 같은 비교 단위 안에서
            서로 다른 두 읍면동이 같은 두 후보에게 같은 득표수를 준 경우입니다. 저득표 노이즈를 빼기 위해 각 후보
            10표 이상인 동률만 집계하며, 같은 투표 구분끼리 비교합니다.{' '}
            <a href="#about" style={{ color: 'var(--color-accent)' }}>정의·방법론 자세히 →</a>
          </p>
          <p style={{ color: 'var(--color-text-tertiary)' }}>
            이 자료는 <strong>특정 해석을 내놓지 않습니다.</strong> "과거 선거에서 이런
            일이 얼마나 자주 있었나"를 빈도로 보여주는 중립 자료이며, 확률 계산은 하지 않습니다.
          </p>
          <p style={{ borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem' }}>
            <strong style={{ color: 'var(--color-text-secondary)' }}>제가 만든 또 다른 서비스</strong> ·{' '}
            <a
              href="https://www.woomunhyundap.com/?utm_source=pyosim&utm_medium=footer"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--color-accent)' }}
            >
              우문현답
            </a>{' '}
            — AI 면접관과 1:1 모의면접으로 꼬리질문까지 대비하는 공채 면접 연습. 진짜 면접은 두 번째 질문부터입니다.
          </p>
        </div>
      </footer>
      </>
      )}
      <AdBanner />
    </div>
  )
}
