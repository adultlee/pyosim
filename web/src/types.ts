export interface TwinGroup {
  category: string
  group: Record<string, string | number | null>
  locations: TwinLocation[]
  votes: Record<string, number>
  total_votes: number
  count: number
  rank_pair: [number, number]
  // 옵셔널 — 데이터에 있으면 표시(하위호환). 후보명 → 정당명.
  parties?: Record<string, string>
}

export interface TwinLocation {
  시도?: string
  구시군?: string
  읍면동?: string
  // 옵셔널 — 그 투표소의 규모·맥락. 있으면 카드에 표시.
  투표수?: number
  선거인수?: number
  '1위'?: string
  '1위득표'?: number
  [key: string]: string | number | undefined
}

export interface TwinData {
  twins: TwinGroup[]
}

export interface RoundMeta {
  pairCount: number
  totalLocations: number
  groupCount: number
  topPair: { names: [string, string]; parties: [string?, string?]; locations: number } | null
}

export interface ElectionIndex {
  rounds: string[]
  counts: Record<string, number>
  roundLabels: Record<string, string>
  // 옵셔널 — 구 index.json 하위호환. analyze_twin_votes.py 재생성 시 채워짐.
  rounds_meta?: Record<string, RoundMeta>
}

export interface TwinTotals {
  pairCount: number
  totalLocations: number
  groupCount: number
}

export interface TwinIndex {
  elections: Record<string, ElectionIndex>
  // 옵셔널 — 선거종류별 + "all" 전체 누적.
  totals?: Record<string, TwinTotals>
}

export interface VotesCsvMeta {
  file: string
  rows: number
  bytes: number
}

// {선거종류: {회차키: meta}} — split_votes_csv.py 가 생성.
export type VotesCsvIndex = Record<string, Record<string, VotesCsvMeta>>
