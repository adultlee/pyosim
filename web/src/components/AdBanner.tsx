import { useState } from 'react'

/**
 * 만든 사람의 다른 서비스(우문현답) 떠있는 사이드 배너.
 * 데스크톱(lg 이상)에서만 화면 우측 하단에 고정 노출, 모바일에선 숨김(본문 보호).
 * 닫기 버튼으로 끌 수 있고, 닫힘은 현재 방문 동안만 유지(새로고침하면 다시 뜸).
 */
export default function AdBanner() {
  const [dismissed, setDismissed] = useState(false)
  if (dismissed) return null

  return (
    <aside
      className="hidden lg:flex fixed bottom-5 right-5 z-20 items-center gap-2 rounded-full pl-3 pr-2 py-1.5"
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
      }}
    >
      <a
        href="https://www.woomunhyundap.com/?utm_source=pyosim&utm_medium=banner"
        target="_blank"
        rel="noopener noreferrer"
        className="no-underline text-xs"
        style={{ color: 'var(--color-text-secondary)' }}
      >
        제가 만든 서비스 <span style={{ color: 'var(--color-accent)' }}>우문현답 ↗</span>
      </a>
      <button
        onClick={() => setDismissed(true)}
        aria-label="닫기"
        className="leading-none text-sm"
        style={{ color: 'var(--color-text-tertiary)', background: 'none', border: 'none', cursor: 'pointer' }}
      >
        ×
      </button>
    </aside>
  )
}
