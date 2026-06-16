# 표심 프로젝트 셋업 디자인

**날짜:** 2026-06-10
**범위:** 프로젝트 초기 폴더 구조 + web/ 스캐폴딩

---

## 목표

기존 레포(`pyosim/`)에 `web/`(Vite + React + TypeScript + Tailwind)과 `etl/` 폴더를 추가한다. DB 폴더·모노레포 툴링 없이 단순 폴더 분리.

## 폴더 구조

```
pyosim/
├── web/                   # Vite + React + TypeScript
│   ├── src/
│   │   ├── App.tsx
│   │   └── styles/
│   │       └── globals.css
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── etl/                   # 파서 스크립트 placeholder
│   └── README.md
├── data_raw/              # 기존 원본 데이터 (변경 없음)
├── docs/                  # 기존 문서 (변경 없음)
├── unzip_all.py           # 기존 스크립트 (변경 없음)
└── package.json           # 루트 진입점 스크립트만
```

## web/ 스택

- Vite 6 + React 18 + TypeScript
- Tailwind CSS v4
- lucide-react (아이콘)

## web/src/ 초기 파일

- `App.tsx` — 빈 껍데기 컴포넌트
- `styles/globals.css` — DESIGN.md CSS 변수 토큰 전체 (컬러·타이포·폰트)

## tailwind.config.ts

DESIGN.md §2 토큰을 `theme.extend.colors`에 연동. `theme.extend.fontFamily`에 Pretendard + JetBrains Mono.

## 루트 package.json

`web/` 진입을 편하게 하는 스크립트만:

```json
{
  "scripts": {
    "dev": "cd web && npm run dev",
    "build": "cd web && npm run build"
  }
}
```

## etl/

폴더 생성 + `README.md` 한 줄("ETL 파서 예정"). 이 세션에서 코드 없음.

## 비결정 사항 (다음 세션)

- ETL 언어 (Python vs TypeScript)
- Supabase 스키마 설계 및 마이그레이션
- 프론트 페이지 라우팅 구조
