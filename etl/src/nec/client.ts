/**
 * etl/src/nec/client.ts
 * 선관위 선거통계시스템(info.nec.go.kr) 개표결과 스크래퍼.
 *
 * 확정:
 *  - 세션(JSESSIONID/WMONID) + form-urlencoded POST.
 *  - 시도 목록: selectbox_cityCodeBySgJson.json → JSON.
 *  - 개표결과: electionInfo_report.xhtml 폼 전체 POST → HTML 표(Document).
 *    루프: 선거종류(electionCode) × 시도(cityCode) × 구시군(sgg) → 투표구 단위 표.
 *
 * 원칙: 출처가 곧 신뢰.
 *  - 요청 간 딜레이로 정중하게, 병렬 자제.
 *  - raw HTML을 그대로 디스크 캐싱. 공식 xlsx/CSV 풀리면 교차검증.
 */

import { writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const BASE = "https://info.nec.go.kr";
const REPORT_PAGE = `${BASE}/electioninfo/electionInfo_report.xhtml`;
const SELECTBOX = `${BASE}/bizcommon/selectbox`;

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** 리포트 페이지 GET → Set-Cookie(JSESSIONID/WMONID) 수집 */
export async function bootstrapSession(): Promise<string> {
  const res = await fetch(REPORT_PAGE, { headers: { "User-Agent": UA } });
  const cookie = (res.headers.getSetCookie?.() ?? [])
    .map((c) => c.split(";")[0])
    .join("; ");
  if (!cookie.includes("JSESSIONID")) {
    throw new Error("세션 쿠키 획득 실패 — 페이지 구조 변경 가능성.");
  }
  return cookie;
}

function headers(cookie: string, json: boolean) {
  return {
    "Accept": json
      ? "application/json, text/javascript, */*; q=0.01"
      : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": BASE,
    "Referer": REPORT_PAGE,
    "User-Agent": UA,
    ...(json ? { "X-Requested-With": "XMLHttpRequest" } : {}),
    "Cookie": cookie,
  };
}

/** [확정] 시도 목록(JSON). electionId=sgId(0020260603=9회 지선), electionCode=선거종류 */
export async function fetchCities(
  electionId: string,
  electionCode: string,
  cookie: string,
  delayMs = 400,
): Promise<unknown> {
  await sleep(delayMs);
  const res = await fetch(`${SELECTBOX}/selectbox_cityCodeBySgJson.json`, {
    method: "POST",
    headers: headers(cookie, true),
    body: new URLSearchParams({ electionId, electionCode }).toString(),
  });
  if (!res.ok) throw new Error(`cityCode → HTTP ${res.status}`);
  return res.json();
}

export interface ResultQuery {
  electionId: string;      // 0020260603
  electionCode: string;    // 선거종류 (예: "2")
  cityCode: string;        // 시도 (예: "2700")
  sggCityCode: string;     // 구시군 (예: "2270801")
  townCodeFromSgg: string; // 구시군 (예: "2708")
  townCode?: string;       // 읍면동, 기본 "-1"(=구시군 전체 개표단위)
}

/** [확정] 개표결과 HTML 표를 반환. 파싱은 parseResultsHtml()에서. */
export async function fetchResultsHtml(
  query: ResultQuery,
  cookie: string,
  delayMs = 600,
): Promise<string> {
  await sleep(delayMs);
  const body = new URLSearchParams({
    electionId: query.electionId,
    requestURI: `/electioninfo/${query.electionId}/vc/vccp08.jsp`,
    topMenuId: "VC",
    secondMenuId: "VCCP08",
    menuId: "VCCP08",
    statementId: "VCCP08_#00",
    electionCode: query.electionCode,
    cityCode: query.cityCode,
    sggCityCode: query.sggCityCode,
    townCodeFromSgg: query.townCodeFromSgg,
    townCode: query.townCode ?? "-1",
    sggTownCode: "-1",
    checkCityCode: "-1",
    x: "1",
    y: "1",
  }).toString();

  const res = await fetch(REPORT_PAGE, {
    method: "POST",
    headers: headers(cookie, false),
    body,
  });
  if (!res.ok) throw new Error(`results → HTTP ${res.status}`);
  return res.text();
}

/** raw HTML을 그대로 캐싱(가공 전 원본 보존 + 추후 교차검증) */
export async function cacheRaw(path: string, html: string): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, html, "utf8");
}

/* ─────────────── 캡처/샘플 들어오면 확정할 영역 ─────────────── */

export interface SggEntry {
  CODE: string;
  NAME: string;
}

/** [확정] 구시군 목록(townCode 4자리). selectbox_townCodeBySgJson.json */
export async function fetchSggs(
  electionId: string,
  electionCode: string,
  cityCode: number | string,
  cookie: string,
  delayMs = 400,
): Promise<SggEntry[]> {
  await sleep(delayMs);
  const res = await fetch(`${SELECTBOX}/selectbox_townCodeBySgJson.json`, {
    method: "POST",
    headers: headers(cookie, true),
    body: new URLSearchParams({
      electionId,
      electionCode,
      cityCode: String(cityCode),
    }).toString(),
  });
  if (!res.ok) throw new Error(`sggCode → HTTP ${res.status}`);
  const data = (await res.json()) as { jsonResult: { body: SggEntry[] | null } };
  return data.jsonResult.body ?? [];
}

/** [확정] sggCityCode 목록(7자리). selectbox_getSggCityCodeByCityIntgJson.json
 *  결과가 비면 townCode(4자리)를 sggCityCode로 그대로 사용한다. */
export async function fetchSggCityCodes(
  electionId: string,
  electionCode: string,
  cityCode: number | string,
  cookie: string,
  delayMs = 400,
): Promise<SggEntry[]> {
  await sleep(delayMs);
  const res = await fetch(`${SELECTBOX}/selectbox_getSggCityCodeByCityIntgJson.json`, {
    method: "POST",
    headers: headers(cookie, true),
    body: new URLSearchParams({
      electionId,
      electionCode,
      cityCode: String(cityCode),
    }).toString(),
  });
  if (!res.ok) throw new Error(`sggCityCode → HTTP ${res.status}`);
  const data = (await res.json()) as { jsonResult: { body: SggEntry[] | null } };
  return data.jsonResult.body ?? [];
}

/** [미확정] HTML 표 → tidy 레코드. 실제 응답 HTML 샘플로 셀렉터 확정 필요. */
export function parseResultsHtml(_html: string): unknown[] {
  // TODO: cheerio로 표 파싱. 컬럼은 8회 xlsx와 동일 개념
  //  (읍면동/구분/선거인수/투표수/후보별 득표/계/무효/기권), level 태깅.
  throw new Error("parseResultsHtml: 응답 HTML 샘플 필요");
}
