# 프로젝트 셋업 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 pyosim 레포에 web/(Vite + React + TypeScript + Tailwind) 와 etl/ 폴더를 추가해 개발 가능한 상태로 만든다.

**Architecture:** 단순 폴더 분리. 모노레포 툴링 없이 루트 package.json에 진입 스크립트만 두고, web/는 독립적인 Vite 앱으로 동작한다.

**Tech Stack:** Vite 6, React 18, TypeScript, Tailwind CSS v4, lucide-react

---

## 파일 맵

| 경로 | 역할 |
|------|------|
| `package.json` (루트) | `dev`/`build` 진입 스크립트 |
| `web/package.json` | web 의존성 |
| `web/vite.config.ts` | Vite 설정 |
| `web/tsconfig.json` | TypeScript 설정 |
| `web/index.html` | Vite HTML 진입점 |
| `web/src/main.tsx` | React 마운트 |
| `web/src/App.tsx` | 루트 컴포넌트 (빈 껍데기) |
| `web/src/styles/globals.css` | DESIGN.md CSS 변수 토큰 |
| `web/tailwind.config.ts` | Tailwind 토큰 연동 |
| `etl/README.md` | ETL placeholder |

---

### Task 1: 루트 package.json 업데이트

**Files:**
- Modify: `package.json`

- [ ] **Step 1: 루트 package.json을 진입 스크립트만 가진 형태로 교체**

```json
{
  "name": "pyosim",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "cd web && npm run dev",
    "build": "cd web && npm run build",
    "preview": "cd web && npm run preview"
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add package.json
git commit -m "chore: add root dev/build scripts"
```

---

### Task 2: web/ Vite 프로젝트 스캐폴딩

**Files:**
- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/index.html`
- Create: `web/src/main.tsx`
- Create: `web/src/App.tsx`

- [ ] **Step 1: web/ 디렉토리 생성 후 npm init**

```bash
mkdir web && cd web && npm create vite@latest . -- --template react-ts
```

프롬프트가 나오면:
- "Current directory is not empty. Remove existing files and continue?" → `y`
- 선택: `React` → `TypeScript`

- [ ] **Step 2: 의존성 설치**

```bash
cd web && npm install
```

- [ ] **Step 3: 불필요한 Vite 보일러플레이트 제거**

`web/src/` 안에서 아래 파일 삭제:
```bash
cd web && rm -f src/App.css src/assets/react.svg public/vite.svg src/index.css
```

- [ ] **Step 4: web/src/App.tsx를 빈 껍데기로 교체**

```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-bg text-text">
      <p className="font-mono text-sm text-text-secondary p-4">표심</p>
    </div>
  )
}
```

- [ ] **Step 5: web/src/main.tsx 확인 — globals.css import 포함하도록 수정**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles/globals.css'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 6: dev 서버 실행 확인**

```bash
cd web && npm run dev
```

Expected: `http://localhost:5173` 에서 흰 화면 또는 기본 Vite 페이지 정상 렌더.

- [ ] **Step 7: Commit**

```bash
git add web/
git commit -m "chore: scaffold web/ with Vite + React + TypeScript"
```

---

### Task 3: Tailwind CSS v4 설치 및 설정

**Files:**
- Create: `web/tailwind.config.ts`
- Create: `web/src/styles/globals.css`
- Modify: `web/vite.config.ts`
- Modify: `web/package.json`

- [ ] **Step 1: Tailwind v4 + Vite 플러그인 설치**

```bash
cd web && npm install tailwindcss@^4 @tailwindcss/vite
```

- [ ] **Step 2: web/vite.config.ts에 Tailwind 플러그인 추가**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    tailwindcss(),
    react(),
  ],
})
```

- [ ] **Step 3: web/src/styles/globals.css 생성 — DESIGN.md 토큰 전체**

```css
@import "tailwindcss";

@theme {
  /* surfaces */
  --color-bg: #0C0F14;
  --color-surface: #141921;
  --color-surface-2: #1B212B;
  --color-border: rgba(255, 255, 255, 0.10);
  --color-border-strong: rgba(255, 255, 255, 0.18);

  /* text */
  --color-text: #E5E9EF;
  --color-text-secondary: #9BA6B2;
  --color-text-tertiary: #66707C;

  /* accent */
  --color-accent: #3DBDA7;
  --color-accent-hover: #54CDB8;

  /* semantic */
  --color-verified: #46B07E;
  --color-warning: #D6A53C;
  --color-error: #D9534F;

  /* party */
  --color-party-dem: #4671B8;
  --color-party-ppp: #C7504B;
  --color-party-etc: #7E8895;

  /* typography */
  --font-sans: "Pretendard", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "IBM Plex Mono", ui-monospace, monospace;
}

body {
  background-color: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}
```

- [ ] **Step 4: dev 서버 재실행 후 토큰 동작 확인**

```bash
cd web && npm run dev
```

브라우저에서 배경이 `#0C0F14` (거의 검정)이고 텍스트가 `#E5E9EF` (밝은 회색)이면 정상.

- [ ] **Step 5: Commit**

```bash
git add web/
git commit -m "chore: add Tailwind CSS v4 with design tokens"
```

---

### Task 4: lucide-react 설치

**Files:**
- Modify: `web/package.json`

- [ ] **Step 1: lucide-react 설치**

```bash
cd web && npm install lucide-react
```

- [ ] **Step 2: App.tsx에서 아이콘 임포트 동작 확인**

`web/src/App.tsx`를 아래처럼 수정해 아이콘이 렌더되는지 확인:

```tsx
import { Database } from 'lucide-react'

export default function App() {
  return (
    <div className="min-h-screen bg-bg text-text">
      <div className="flex items-center gap-2 p-4">
        <Database size={16} className="text-accent" />
        <p className="font-mono text-sm text-text-secondary">표심</p>
      </div>
    </div>
  )
}
```

브라우저에서 teal 색 아이콘과 텍스트가 보이면 정상.

- [ ] **Step 3: Commit**

```bash
git add web/
git commit -m "chore: add lucide-react"
```

---

### Task 5: etl/ placeholder 생성

**Files:**
- Create: `etl/README.md`

- [ ] **Step 1: etl/ 폴더와 README.md 생성**

```bash
mkdir etl
```

`etl/README.md`:

```markdown
# etl

선관위 XLSX 원본을 파싱해 정규화된 레코드로 변환하는 ETL 스크립트.

언어 및 구현은 추후 결정.
```

- [ ] **Step 2: Commit**

```bash
git add etl/
git commit -m "chore: add etl/ placeholder"
```

---

### Task 6: .gitignore 정리

**Files:**
- Create or Modify: `.gitignore`

- [ ] **Step 1: 루트 .gitignore 확인 및 web/ node_modules 추가**

`.gitignore` (루트):

```
# deps
node_modules/
web/node_modules/

# build
web/dist/

# env
.env
.env.local

# OS
.DS_Store

# data (원본은 LFS 또는 로컬 전용)
data_raw/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore"
```
