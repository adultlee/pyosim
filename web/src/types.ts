export interface TwinGroup {
  category: string
  group: Record<string, string | number | null>
  locations: Record<string, string | number>[]
  votes: Record<string, number>
  total_votes: number
  count: number
  rank_pair: [number, number]
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
