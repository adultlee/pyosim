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
  ['dem', ['더불어민주', '열린우리', '민주통합', '새정치민주', '통합민주', '새천년민주']],
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

// 정당 계열 서열 — 낮을수록 주요 정당(목록 정렬·우선순위용).
const LINEAGE_RANK: Record<PartyLineage, number> = {
  dem: 0,
  ppp: 1,
  reform: 2,
  peoples: 3,
  justice: 4,
  progress: 5,
  etc: 6,
}

export function partyRank(party: string | undefined | null): number {
  return LINEAGE_RANK[partyLineage(party)]
}

// ── 회차별 주요 정당 서열 ──────────────────────────────────────────
// 정당명은 시대마다 바뀌고(민주당 계열·보수 계열), 같은 이름이 다른 시대에
// 군소정당으로 재등장한다("한나라당"이 2020년대에도 보임). 그래서 정당의
// 주요도(major rank)는 회차(연도)를 함께 봐야 정확하다.
//
// 각 시대의 양대 정당을 명시한다. dem=0, ppp=1(양당), 그 외는 LINEAGE_RANK로.
// 키: `${electionType}|${round}` (round는 JSON group.선거_회차 값).

type MajorParties = { dem: string[]; ppp: string[] }

// 회차별 양대 정당의 그 시기 공식 명칭(부분일치 키워드).
const MAJOR_BY_ROUND: Record<string, MajorParties> = {
  // 대선 (round = 14~21)
  '대선|14': { dem: ['새정치국민회의', '국민회의'], ppp: ['한나라'] },
  '대선|15': { dem: ['새천년민주'], ppp: ['한나라'] },
  '대선|16': { dem: ['열린우리', '새천년민주'], ppp: ['한나라'] },
  '대선|17': { dem: ['대통합민주신당', '통합민주'], ppp: ['한나라'] },
  '대선|18': { dem: ['민주통합'], ppp: ['새누리'] },
  '대선|19': { dem: ['더불어민주'], ppp: ['자유한국', '새누리'] },
  '대선|20': { dem: ['더불어민주'], ppp: ['국민의힘'] },
  '대선|21': { dem: ['더불어민주'], ppp: ['국민의힘'] },
  // 지방선거 (round = 3~9)
  '지방선거|3': { dem: ['새천년민주'], ppp: ['한나라'] },
  '지방선거|4': { dem: ['열린우리'], ppp: ['한나라'] },
  '지방선거|5': { dem: ['민주당'], ppp: ['한나라'] },
  '지방선거|6': { dem: ['새정치민주연합'], ppp: ['새누리'] },
  '지방선거|7': { dem: ['더불어민주'], ppp: ['자유한국'] },
  '지방선거|8': { dem: ['더불어민주'], ppp: ['국민의힘'] },
  '지방선거|9': { dem: ['더불어민주'], ppp: ['국민의힘'] },
  // 총선 (round = 제16대~제22대)
  '총선|제16대': { dem: ['새천년민주'], ppp: ['한나라'] },
  '총선|제17대': { dem: ['열린우리', '새천년민주'], ppp: ['한나라'] },
  '총선|제18대': { dem: ['통합민주'], ppp: ['한나라'] },
  '총선|제19대': { dem: ['민주통합'], ppp: ['새누리'] },
  '총선|제20대': { dem: ['더불어민주'], ppp: ['새누리'] },
  '총선|제21대': { dem: ['더불어민주'], ppp: ['미래통합'] },
  '총선|제22대': { dem: ['더불어민주'], ppp: ['국민의힘'] },
}

// 회차별 주요도 서열. 그 시대의 양당이면 0(민주)/1(보수), 아니면 계열 서열.
export function partyRankForRound(
  party: string | undefined | null,
  electionType: string,
  round: string | number,
): number {
  if (!party) return LINEAGE_RANK.etc
  const major = MAJOR_BY_ROUND[`${electionType}|${round}`]
  if (major) {
    if (major.dem.some(keyword => party.includes(keyword))) return 0
    if (major.ppp.some(keyword => party.includes(keyword))) return 1
    // 그 시대 양당이 아니면, 군소로 본다(계열 서열은 색상용이라 정렬엔 안 씀).
    return LINEAGE_RANK.etc
  }
  // 회차 정의가 없으면 계열 서열로 폴백.
  return LINEAGE_RANK[partyLineage(party)]
}
