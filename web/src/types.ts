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
  // 옵셔널 — 그 투표소의 규모. 있으면 카드에 표시.
  투표수?: number
  선거인수?: number
  [key: string]: string | number | undefined
}

export interface TwinData {
  twins: TwinGroup[]
}

export interface ElectionIndex {
  rounds: string[]
  counts: Record<string, number>
  roundLabels: Record<string, string>
}

export interface TwinIndex {
  elections: Record<string, ElectionIndex>
}
