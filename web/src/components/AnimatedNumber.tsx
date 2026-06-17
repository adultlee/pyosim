import { useEffect, useState } from 'react'
import NumberFlow from '@number-flow/react'

type Props = {
  value: number
  className?: string
  style?: React.CSSProperties
  /** 마운트 시 0에서 값까지 굴러오게 한다 (기본 true). false면 값 변경 시에만 애니메이션. */
  animateOnMount?: boolean
  /** 켜면 loopIntervalMs 마다 0 → value 라이징을 계속 반복한다. */
  loop?: boolean
  /** 롤링 반복 주기(ms). 기본 9000. */
  loopIntervalMs?: number
  /** 0 → value 까지 차오르는 시간(ms). 기본 1600. */
  riseDurationMs?: number
}

// number-flow 래퍼. 0에서 value 까지 여러 단계를 거쳐(100 → 1,000 → 20,000 …)
// 자릿수가 점점 불어나며 차오른다. loop=true 면 주기적으로 0부터 다시 차오른다.
export default function AnimatedNumber({
  value,
  className,
  style,
  animateOnMount = true,
  loop = false,
  loopIntervalMs = 9000,
  riseDurationMs = 1600,
}: Props) {
  const [cycle, setCycle] = useState(0)
  const [display, setDisplay] = useState(animateOnMount ? 0 : value)

  // 0 → value 를 easeOutCubic 로 여러 키프레임을 거쳐 차오르게 한다.
  // 단계 사이 간격을 둬서 number-flow 가 자릿수를 굴릴 시간을 준다.
  useEffect(() => {
    if (value <= 0) {
      setDisplay(value)
      return
    }
    const STEPS = 14
    const stepGap = riseDurationMs / STEPS
    setDisplay(0)
    const timers: ReturnType<typeof setTimeout>[] = []
    for (let step = 1; step <= STEPS; step++) {
      const progress = step / STEPS
      const eased = 1 - Math.pow(1 - progress, 3) // easeOutCubic
      const target = step === STEPS ? value : Math.round(value * eased)
      timers.push(setTimeout(() => setDisplay(target), step * stepGap))
    }
    return () => timers.forEach(clearTimeout)
  }, [value, cycle, riseDurationMs])

  // 주기마다 사이클을 증가 → 위 effect가 0부터 다시 차오름.
  useEffect(() => {
    if (!loop || value <= 0) return
    const interval = setInterval(() => setCycle(prev => prev + 1), loopIntervalMs)
    return () => clearInterval(interval)
  }, [loop, loopIntervalMs, value])

  return (
    <NumberFlow
      value={display}
      className={className}
      style={style}
      format={{ useGrouping: true }}
      locales="ko-KR"
    />
  )
}
