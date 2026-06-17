import type { TwinData } from './types'

export type RoundStats = {
  pairCount: number       // 서로 다른 후보쌍 수
  totalLocations: number  // 모든 사례의 일치 투표소 합
  groupCount: number      // 득표값까지 같은 사례(쌍둥이 그룹) 수
  topPair: { names: [string, string]; parties: [string?, string?]; locations: number } | null
}

// 로드된 회차 JSON을 후보쌍 기준으로 집계해 hero용 수치를 낸다.
// (TwinVoteViewer의 묶음 키와 동일 규칙: category + group + rank_pair + 후보쌍이름)
export function computeRoundStats(data: TwinData | null): RoundStats {
  const empty: RoundStats = { pairCount: 0, totalLocations: 0, groupCount: 0, topPair: null }
  if (!data) return empty

  const byKey = new Map<string, { names: [string, string]; parties: [string?, string?]; locations: number }>()
  let totalLocations = 0

  for (const group of data.twins) {
    const names = Object.entries(group.votes)
      .sort((left, right) => right[1] - left[1])
      .map(([cand]) => cand)
    const [first, second] = names
    if (second == null) continue

    totalLocations += group.count
    const sortedPair = [first, second].sort()
    const key = `${group.category}|${JSON.stringify(group.group)}|${group.rank_pair.join('-')}|${sortedPair.join('=')}`
    const entry = byKey.get(key)
    if (entry) {
      entry.locations += group.count
    } else {
      const parties = group.parties ?? {}
      byKey.set(key, { names: [first, second], parties: [parties[first], parties[second]], locations: group.count })
    }
  }

  let topPair: RoundStats['topPair'] = null
  for (const entry of byKey.values()) {
    if (topPair == null || entry.locations > topPair.locations) topPair = entry
  }

  return {
    pairCount: byKey.size,
    totalLocations,
    groupCount: data.twins.length,
    topPair,
  }
}
