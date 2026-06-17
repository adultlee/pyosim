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
      className="hidden lg:block fixed bottom-16 right-6 z-20 w-64 rounded-xl p-4"
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
      }}
    >
      <button
        onClick={() => setDismissed(true)}
        aria-label="광고 닫기"
        className="absolute top-2 right-2 leading-none text-base"
        style={{ color: 'var(--color-text-tertiary)', background: 'none', border: 'none', cursor: 'pointer' }}
      >
        ×
      </button>

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
