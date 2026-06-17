import { useState } from 'react'

/**
 * 만든 사람의 다른 서비스(우문현답) 떠있는 사이드 배너.
 * 데스크톱(lg 이상)에서만 화면 우측 하단에 고정 노출, 모바일에선 숨김(본문 보호).
 * 닫기 버튼으로 끌 수 있고, 한 번 닫으면 localStorage에 기억해 일정 기간 다시 뜨지 않는다.
 */
const DISMISS_KEY = 'woomunhyundap-ad-dismissed-until'
const DISMISS_DAYS = 7

function isDismissed(): boolean {
  try {
    const until = localStorage.getItem(DISMISS_KEY)
    return until !== null && Number(until) > Date.now()
  } catch {
    return false
  }
}

export default function AdBanner() {
  const [dismissed, setDismissed] = useState(isDismissed)
  if (dismissed) return null

  const handleDismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, String(Date.now() + DISMISS_DAYS * 24 * 60 * 60 * 1000))
    } catch {
      // localStorage 불가(프라이빗 모드 등)면 세션 단위로만 닫힘
    }
    setDismissed(true)
  }

  return (
    <aside
      className="hidden lg:block fixed bottom-6 right-6 z-20 w-64 rounded-xl p-4"
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
      }}
    >
      <button
        onClick={handleDismiss}
        aria-label="광고 닫기"
        className="absolute top-2 right-2 leading-none text-base"
        style={{ color: 'var(--color-text-tertiary)', background: 'none', border: 'none', cursor: 'pointer' }}
      >
        ×
      </button>

      <div className="text-xs mb-1" style={{ color: 'var(--color-text-tertiary)' }}>
        제가 만든 또 다른 서비스예요
      </div>
      <a
        href="https://www.woomunhyundap.com/?utm_source=pyosim&utm_medium=banner"
        target="_blank"
        rel="noopener noreferrer"
        className="no-underline"
      >
        <div className="text-lg font-bold mb-1" style={{ color: 'var(--color-accent)' }}>
          우문현답
        </div>
        <div className="text-sm leading-relaxed mb-3" style={{ color: 'var(--color-text-secondary)' }}>
          AI 면접관과 1:1 모의면접으로 꼬리질문까지 대비하는 공채 면접 연습.
          <br />
          진짜 면접은 두 번째 질문부터입니다.
        </div>
        <div
          className="rounded-lg px-3 py-2 text-sm font-semibold text-center"
          style={{ backgroundColor: 'var(--color-accent)', color: '#0C0F14' }}
        >
          모의면접 해보기 →
        </div>
      </a>
    </aside>
  )
}
