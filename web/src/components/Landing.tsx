import type { TwinIndex } from '../types'
import AnimatedNumber from './AnimatedNumber'
import { partyColor } from '../partyColor'

// 같은 두 후보가 여러 동에서 동률로 반복된 대표 쌍 (9회 지선)
const SAMPLES = [
  {
    race: '전남지사 · 사전투표',
    p1: '민형배', party1: '더불어민주당', p2: '이정현', party2: '국민의힘',
    locCount: 8,
    cases: ['1,401 = 120', '606 = 57', '506 = 42', '356 = 42'],
  },
  {
    race: '인천시장 · 사전투표',
    p1: '박찬대', party1: '더불어민주당', p2: '유정복', party2: '국민의힘',
    locCount: 2,
    cases: ['3,030 = 1,440'],
  },
]

type Props = {
  index: TwinIndex | null
  electionKeys: string[]
  onPickElection: (election: string) => void
}

export default function Landing({ index, electionKeys, onPickElection }: Props) {
  const totals = index?.totals?.all ?? null

  const serif = { fontFamily: 'Georgia, "Nanum Myeongjo", "Apple SD Gothic Neo", serif' }

  return (
    <>
    <main className="max-w-3xl mx-auto px-6 pt-8 pb-12">
      {/* 상단 괘선 + 발행 정보 */}
      <div className="flex items-center justify-between text-xs pb-2" style={{ color: 'var(--color-text-tertiary)' }}>
        <span className="uppercase tracking-widest">선거 데이터 리포트</span>
        <span>2026 · 선관위 공식 개표결과</span>
      </div>
      <div style={{ borderTop: '3px solid var(--color-text)', borderBottom: '1px solid var(--color-text)', height: 4 }} />

      {/* 헤드라인 */}
      <h1
        className="mt-6 text-3xl sm:text-5xl font-bold leading-tight text-center"
        style={{ ...serif, color: 'var(--color-text)' }}
      >
        우연일까? 부정일까?<br />
        <span style={{ color: 'var(--color-accent)' }}>과거엔 어땠을까.</span>
      </h1>
      <p className="mt-3 text-center text-sm" style={{ color: 'var(--color-text-secondary)' }}>
        이런 일이 과거 선거엔 얼마나 있었는지 — 숫자로만 보여준다.
      </p>

      <div className="mt-6" style={{ borderTop: '1px solid var(--color-border)' }} />

      {/* 본문 2단: 좌 사건 / 우 질문+규모 */}
      <div className="mt-6 grid sm:grid-cols-2 gap-x-8 gap-y-6">
        {/* 좌: 사건 기사 + 사례 */}
        <div className="flex flex-col gap-3">
          <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
            <span className="float-left text-4xl leading-none mr-2 font-bold" style={{ ...serif, color: 'var(--color-text)' }}>2</span>
            026년 9회 지방선거 관내사전투표에서, 서로 다른 두 동의 득표가 한 표도
            틀리지 않고 일치한 사례가 잇따라 발견됐다. 더 놀라운 건 — 같은 두 후보의
            득표가 <strong style={{ color: 'var(--color-text)' }}>한두 곳이 아니라 여러 동에서 거듭</strong> 똑같이 나왔다는 점이다.
          </p>
          <div className="flex flex-col gap-2">
            {SAMPLES.map(sample => (
              <div
                key={sample.race}
                className="rounded-lg px-3 py-3"
                style={{ border: '1px solid var(--color-border)' }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>{sample.race}</span>
                  <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ backgroundColor: 'var(--color-warning)', color: '#0C0F14' }}>
                    {sample.locCount}곳에서 반복
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-sm mb-1.5">
                  <span className="inline-block rounded-sm shrink-0" style={{ width: 8, height: 8, backgroundColor: partyColor(sample.party1) }} />
                  <span className="font-medium" style={{ color: 'var(--color-text)' }}>{sample.p1}</span>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>·</span>
                  <span className="inline-block rounded-sm shrink-0" style={{ width: 8, height: 8, backgroundColor: partyColor(sample.party2) }} />
                  <span className="font-medium" style={{ color: 'var(--color-text)' }}>{sample.p2}</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {sample.cases.map(caseText => (
                    <span
                      key={caseText}
                      className="font-mono tabular-nums text-xs px-2 py-0.5 rounded"
                      style={{ backgroundColor: 'var(--color-surface-2)', color: 'var(--color-text-secondary)' }}
                    >
                      {caseText}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* 어떻게 읽나 — 정의 시각화 */}
          <div className="pt-3" style={{ borderTop: '1px solid var(--color-text)' }}>
            <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--color-text-tertiary)' }}>어떻게 읽나</div>
            <div className="flex flex-col gap-1 text-sm font-mono tabular-nums">
              <div className="flex items-center gap-2">
                <span className="text-xs px-1.5 py-0.5 rounded shrink-0" style={{ backgroundColor: 'var(--color-surface-2)', color: 'var(--color-text-tertiary)' }}>A동</span>
                <span style={{ color: 'var(--color-text)' }}>박찬대 3,030 = 유정복 1,440</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-1.5 py-0.5 rounded shrink-0" style={{ backgroundColor: 'var(--color-surface-2)', color: 'var(--color-text-tertiary)' }}>B동</span>
                <span style={{ color: 'var(--color-text)' }}>박찬대 3,030 = 유정복 1,440</span>
              </div>
            </div>
            <p className="text-xs mt-2 leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
              두 후보의 득표가 서로 같다는 뜻이 아니라, <strong style={{ color: 'var(--color-text)' }}>서로 다른 두 투표소의 결과가 똑같이 반복</strong>된다는 뜻이다.
              이름과 득표수가 모두 일치해야 하고, 각 후보 10표 이상인 경우만 센다.
            </p>
          </div>

          {/* 관련 영상 */}
          <div className="pt-3" style={{ borderTop: '1px solid var(--color-border)' }}>
            <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--color-text-tertiary)' }}>관련 영상</div>
            <div className="relative w-full rounded overflow-hidden" style={{ paddingBottom: '56.25%' }}>
              <iframe
                className="absolute inset-0 w-full h-full"
                src="https://www.youtube.com/embed/UPBWEdob7pY"
                title="동일 득표 관련 영상"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                style={{ border: '1px solid var(--color-border)' }}
              />
            </div>
          </div>
        </div>

        {/* 우: 질문 → 규모 공개 */}
        <div className="flex flex-col gap-4">
          <blockquote
            className="text-lg leading-snug pl-3"
            style={{ ...serif, borderLeft: '3px solid var(--color-text)', color: 'var(--color-text)' }}
          >
            "드문 일일까, 흔한 일일까?<br />— 직접 헤아려보자."
          </blockquote>
          <div
            className="rounded-lg px-4 py-5 text-center"
            style={{ border: '2px solid var(--color-text)' }}
          >
            <div className="text-xs uppercase tracking-widest mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
              지난 30년 · 22개 선거
            </div>
            <AnimatedNumber
              value={totals?.groupCount ?? 0}
              loop
              className="font-mono tabular-nums text-5xl font-bold"
              style={{ color: 'var(--color-accent)' }}
            />
            <div className="text-sm mt-1" style={{ color: 'var(--color-text)' }}>건의 동일 득표가 있었다</div>
            {totals && (
              <div className="flex justify-center gap-6 mt-4 pt-4" style={{ borderTop: '1px solid var(--color-border)' }}>
                <div>
                  <AnimatedNumber
                    value={totals.pairCount}
                    loop
                    className="font-mono tabular-nums text-lg font-bold"
                    style={{ color: 'var(--color-text)' }}
                  />
                  <div className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>후보쌍</div>
                </div>
                <div>
                  <AnimatedNumber
                    value={totals.totalLocations}
                    loop
                    className="font-mono tabular-nums text-lg font-bold"
                    style={{ color: 'var(--color-text)' }}
                  />
                  <div className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>일치 투표소</div>
                </div>
              </div>
            )}
          </div>
          <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-tertiary)' }}>
            이 자료는 옳고 그름을 판단하지 않는다. "과거에 같은 일이 얼마나 있었나"를
            선관위 공식 데이터로 보여주는 빈도 자료다.
          </p>
          <figure className="flex flex-col gap-1 mt-1">
            <img
              src="/about-background.png"
              alt="장동혁 국민의힘 대표가 동일 득표를 두고 발언하는 모습"
              className="w-full rounded"
              style={{ border: '1px solid var(--color-border)', filter: 'grayscale(1)' }}
            />
            <figcaption className="text-xs leading-snug" style={{ color: 'var(--color-text-tertiary)' }}>
              장동혁 국민의힘 대표가 2026년 6월 동일 득표를 두고 조작 가능성을 제기했다.{' '}
              <a
                href="https://www.tjb.co.kr/news05/bodo/view/id/99311/version/1"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--color-accent)' }}
              >
                TJB, 2026-06-09 ↗
              </a>
            </figcaption>
          </figure>
        </div>
      </div>

      {/* 종류별 집계 — 굵은 괘선으로 구분 */}
      <div className="mt-8" style={{ borderTop: '1px solid var(--color-text)' }} />
      <div className="text-xs uppercase tracking-widest mt-3 mb-2" style={{ color: 'var(--color-text-tertiary)' }}>
        선거 종류별 집계
      </div>
      {index?.totals && (
        <div className="grid grid-cols-3 gap-px" style={{ backgroundColor: 'var(--color-border)' }}>
          {electionKeys.map(election => {
            const summary = index.totals?.[election]
            const range = index.elections[election]
            const rangeLabel = range
              ? `${range.roundLabels[range.rounds[0]]}~${range.roundLabels[range.rounds[range.rounds.length - 1]]}`
              : ''
            return (
              <a
                key={election}
                href="#explore"
                onClick={() => onPickElection(election)}
                className="px-4 py-4 no-underline transition-colors"
                style={{ backgroundColor: 'var(--color-bg)', color: 'inherit' }}
              >
                <div className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>{election}</div>
                <div className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>{rangeLabel}</div>
                <div className="mt-1 flex items-baseline" style={{ color: 'var(--color-accent)' }}>
                  <AnimatedNumber
                    value={summary?.groupCount ?? 0}
                    className="font-mono tabular-nums text-2xl font-bold"
                  />
                  <span className="text-xs font-normal ml-0.5" style={{ color: 'var(--color-text-tertiary)' }}>건</span>
                </div>
              </a>
            )
          })}
        </div>
      )}

      </main>

      {/* 하단 고정 CTA — 스크롤 내내 진입 버튼 노출 */}
      <div
        className="sticky bottom-0 z-10 px-6 py-3"
        style={{
          backgroundColor: 'var(--color-bg)',
          borderTop: '1px solid var(--color-border)',
        }}
      >
        <a
          href="#explore"
          className="block max-w-3xl mx-auto px-6 py-3 rounded-lg text-base font-semibold text-center"
          style={{ backgroundColor: 'var(--color-accent)', color: '#0C0F14' }}
        >
          어느 선거였는지 직접 보기 →
        </a>
      </div>
    </>
  )
}
