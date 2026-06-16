// 정당명 → 계열색 매핑. twin-vote-spec.md §3 기준.
// 역사적 정당은 당시 공식색이 아니라 계열색으로 통일한다.

export type PartyLineage =
  | 'dem'
  | 'ppp'
  | 'reform'
  | 'justice'
  | 'progress'
  | 'peoples'
  | 'etc'

// 부분일치 키워드 → 계열. 위에서부터 먼저 매칭되는 계열을 쓴다.
const LINEAGE_KEYWORDS: [PartyLineage, string[]][] = [
  ['dem', ['더불어민주', '열린우리', '민주통합', '새정치민주', '통합민주', '새천년민주', '민주당']],
  ['ppp', ['국민의힘', '새누리', '한나라', '자유한국', '미래통합']],
  ['reform', ['개혁신당']],
  ['progress', ['진보당', '통합진보', '민주노동']],
  ['justice', ['정의당', '녹색정의', '노동당', '진보신당', '녹색당']],
  ['peoples', ['국민의당', '국민의미래']],
]

const LINEAGE_COLOR: Record<PartyLineage, string> = {
  dem: 'var(--color-party-dem)',
  ppp: 'var(--color-party-ppp)',
  reform: 'var(--color-party-reform)',
  justice: 'var(--color-party-justice)',
  progress: 'var(--color-party-progress)',
  peoples: 'var(--color-party-peoples)',
  etc: 'var(--color-party-etc)',
}

export function partyLineage(party: string | undefined | null): PartyLineage {
  if (!party) return 'etc'
  for (const [lineage, keywords] of LINEAGE_KEYWORDS) {
    if (keywords.some(keyword => party.includes(keyword))) return lineage
  }
  return 'etc'
}

export function partyColor(party: string | undefined | null): string {
  return LINEAGE_COLOR[partyLineage(party)]
}
