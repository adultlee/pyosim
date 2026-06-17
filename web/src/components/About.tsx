const SOURCES = [
  {
    label: '선관위 자료실 게시판',
    desc: '과거 회차 개표결과 원본(XLS·XLSX)을 내려받았습니다. 지방선거 3~8회, 총선 16~22대, 대선 14~21대.',
    href: 'https://nec.go.kr/site/nec/ex/bbs/List.do?cbIdx=1129',
  },
  {
    label: '중앙선거관리위원회 선거통계시스템',
    desc: '최근 회차 개표결과(HTML)를 가져왔습니다. 9회 지방선거(2026) 등.',
    href: 'https://info.nec.go.kr',
  },
]

const STEPS = [
  {
    title: '1. 파싱',
    body: '선관위 원본(XLS·XLSX·HTML)을 회차별 파서로 읽어 tidy CSV로 정규화합니다. 각 행은 (회차·선거종류·시도·구시군·읍면동·투표구분·후보·득표수) 단위입니다.',
  },
  {
    title: '2. 검증',
    body: '파싱 결과를 선관위 공식 득표 총합과 대조하는 검증 게이트를 통과해야만 CSV를 씁니다. 총합이 어긋나면 산출물을 만들지 않습니다.',
  },
  {
    title: '3. 단위 통일 (읍면동 × 투표구분)',
    body: '회차마다 원본 단위가 다릅니다(3회 지선은 투표구 「가리봉제1동제3투」까지, 9회·총선·대선은 읍면동까지). 작은 단위일수록 득표가 작아 동률이 과도하게 잡히므로, 같은 읍면동의 여러 투표구를 한 투표소로 합산해 모든 회차를 읍면동 단위로 통일합니다. 시·구로는 올리지 않습니다.',
  },
  {
    title: '4. 쌍둥이 집계',
    body: '같은 비교 단위 안에서, 서로 다른 두 읍면동이 같은 두 후보에게 같은 득표수를 준 경우를 셉니다. 한 투표소 내 인접 순위 쌍이면 되고(1·2위, 2·3위…), 각 후보 10표 이상인 동률만 인정합니다. 합계(「계」) 행과 같은 투표 구분이 아닌 비교는 제외합니다.',
  },
]

const UNITS = [
  ['대선', '(회차, 투표구분) — 전국'],
  ['총선 지역구', '(회차, 선거구명, 투표구분)'],
  ['총선 비례', '(회차, 투표구분) — 전국'],
  ['지선 시도지사·교육감·광역비례', '(회차, 선거종류, 시도그룹, 투표구분)'],
  ['지선 나머지', '(회차, 선거종류, 시도, 구시군, 투표구분)'],
]

function Code({ children }: { children: string }) {
  return (
    <pre
      className="rounded-lg px-4 py-3 text-xs leading-relaxed overflow-x-auto"
      style={{ backgroundColor: 'var(--color-surface-2)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}
    >
      <code>{children}</code>
    </pre>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-base font-semibold" style={{ color: 'var(--color-text)' }}>
        {title}
      </h2>
      {children}
    </section>
  )
}

export default function About({ onBack }: { onBack: () => void }) {
  return (
    <main className="max-w-3xl mx-auto px-6 py-6 flex flex-col gap-8">
      <button
        onClick={onBack}
        className="self-start text-xs px-3 py-1 rounded-lg"
        style={{ backgroundColor: 'var(--color-surface-2)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}
      >
        ← 돌아가기
      </button>

      <div>
        <h1 className="text-lg font-semibold mb-1">데이터 출처와 계산 방법</h1>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          이 도구는 중앙선거관리위원회의 공식 개표결과만을 가공한 중립 자료입니다.
          특정 해석을 내놓지 않으며, 확률 계산은 하지 않습니다.
        </p>
      </div>

      <Section title="원본 데이터 출처">
        <div className="flex flex-col gap-2.5">
          {SOURCES.map(source => (
            <div
              key={source.href}
              className="rounded-lg px-4 py-3 text-sm leading-relaxed"
              style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
            >
              <a
                href={source.href}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium"
                style={{ color: 'var(--color-accent)' }}
              >
                {source.label} ↗
              </a>
              <p className="mt-1" style={{ color: 'var(--color-text-secondary)' }}>{source.desc}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="계산 방법">
        <div className="flex flex-col gap-2.5">
          {STEPS.map(step => (
            <div
              key={step.title}
              className="rounded-lg px-4 py-3 text-sm leading-relaxed"
              style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
            >
              <p className="font-medium mb-1" style={{ color: 'var(--color-text)' }}>{step.title}</p>
              <p style={{ color: 'var(--color-text-secondary)' }}>{step.body}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="비교 단위">
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          쌍둥이는 아래 비교 단위 <strong>안에서만</strong> 찾습니다. 단위가 다르면 비교하지 않습니다.
        </p>
        <div className="rounded-lg overflow-hidden text-sm" style={{ border: '1px solid var(--color-border)' }}>
          {UNITS.map(([elec, unit], index) => (
            <div
              key={elec}
              className="flex flex-col sm:flex-row sm:gap-4 px-4 py-2.5"
              style={{
                borderTop: index === 0 ? undefined : '1px solid var(--color-border)',
                backgroundColor: 'var(--color-surface)',
              }}
            >
              <span className="sm:w-56 shrink-0 font-medium" style={{ color: 'var(--color-text)' }}>{elec}</span>
              <span className="font-mono text-xs" style={{ color: 'var(--color-text-secondary)' }}>{unit}</span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="코드로 보는 집계 로직">
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          실제 집계 코드의 핵심입니다. ① 같은 읍면동의 투표구를 합산하고, ② 득표순으로
          줄 세워 인접한 두 후보를 한 쌍으로 묶은 뒤, ③ 서로 다른 투표소에서 같은 쌍이
          반복되고 두 후보 모두 10표 이상이면 쌍둥이로 셉니다.
        </p>

        <p className="text-sm font-medium mt-1" style={{ color: 'var(--color-text)' }}>① 읍면동 단위로 투표구 득표 합산</p>
        <Code>{`# 같은 읍면동 안 투표구(예: 북부동제1투 ~ 제6투)를
# 후보별로 더해 한 투표소로 합친다
vote_by_id = {}
for 후보, 득표 in 한_읍면동_행들:
    vote_by_id[후보] = vote_by_id.get(후보, 0) + 득표
# → {"이회창": 9714, "노무현": 7057, "권영길": 602, ...}`}</Code>

        <p className="text-sm font-medium mt-1" style={{ color: 'var(--color-text)' }}>② 득표순 인접 쌍으로 버킷에 담기</p>
        <Code>{`# 득표 내림차순으로 정렬해 인접한 두 후보를 한 쌍으로
ranked = sorted(후보_득표, key=lambda x: -x[1])
for rank in range(len(ranked) - 1):
    쌍 = (ranked[rank], ranked[rank + 1])   # (1·2위), (2·3위) …
    버킷[(비교단위, rank+1, 쌍)].append(이_투표소)`}</Code>

        <p className="text-sm font-medium mt-1" style={{ color: 'var(--color-text)' }}>③ 두 투표소 이상 반복 + 10표 임계값</p>
        <Code>{`for 버킷키, 투표소목록 in 버킷.items():
    if len(투표소목록) < 2:        # 한 곳뿐이면 '반복' 아님
        continue
    (후보1, 표1), (후보2, 표2) = 버킷키의 두 후보
    if 표1 < 10 or 표2 < 10:       # 저득표 노이즈 제외
        continue
    쌍둥이로 집계  # 예: 박찬대 583 = 유정복 583 이 A·B동에서 반복`}</Code>

        <p className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
          ※ 같은 투표 구분(관내사전·당일 등)끼리만 비교하며, 합계(「계」) 행은 입력에서 제외합니다.
          이름과 득표수가 모두 같아야 하고, 표만 같고 후보가 다르면 쌍둥이가 아닙니다.
        </p>
      </Section>
    </main>
  )
}
