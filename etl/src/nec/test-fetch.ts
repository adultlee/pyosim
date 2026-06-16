/**
 * 단일 쿼리 연결 테스트.
 * 서울 종로구(electionCode=2, cityCode=2700, sgg=2708) 개표결과 HTML을 받아
 * data/raw/0020260603/ 에 캐싱하고 앞 500자를 출력한다.
 */

import { bootstrapSession, fetchCities, fetchSggs, fetchResultsHtml, cacheRaw } from "./client.js";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

const ELECTION_ID = "0020260603";
const ELECTION_CODE = "2"; // 시도지사
const CITY_CODE = "2700";  // 대구광역시
const SGG_CITY_CODE = "2270801";
const TOWN_CODE_FROM_SGG = "2708";

const OUT_DIR = resolve(__dirname, "../../..", "data/raw", ELECTION_ID);

async function main() {
  console.log("1. 세션 획득 중...");
  const cookie = await bootstrapSession();
  console.log(`   쿠키: ${cookie.slice(0, 60)}...`);

  console.log("2. 시도 목록 조회 (electionCode=4 구시군장)...");
  const cities = await fetchCities(ELECTION_ID, "4", cookie) as any;
  const cityList: { CODE: number; NAME: string }[] = cities.jsonResult.body;
  console.log(`   시도 수: ${cityList.length}`);
  console.log("   처음 3개:", cityList.slice(0, 3).map(c => `${c.NAME}(${c.CODE})`).join(", "));

  console.log("2-1. 서울 구시군 목록 조회...");
  const seoulSggs = await fetchSggs(ELECTION_ID, "4", 1100, cookie);
  console.log(`   서울 구시군 수: ${seoulSggs.length}`);
  console.log("   처음 5개:", seoulSggs.slice(0, 5).map(s => `${s.NAME}(${s.CODE})`).join(", "));

  console.log("3. 개표결과 HTML 요청...");
  const html = await fetchResultsHtml(
    {
      electionId: ELECTION_ID,
      electionCode: ELECTION_CODE,
      cityCode: CITY_CODE,
      sggCityCode: SGG_CITY_CODE,
      townCodeFromSgg: TOWN_CODE_FROM_SGG,
    },
    cookie,
  );

  const outPath = join(OUT_DIR, `ec${ELECTION_CODE}_city${CITY_CODE}_sgg${TOWN_CODE_FROM_SGG}.html`);
  await cacheRaw(outPath, html);
  console.log(`4. 저장 완료: ${outPath}`);
  console.log(`   HTML 크기: ${html.length} bytes`);
  console.log(`   앞 500자:\n${html.slice(0, 500)}`);
}

main().catch((err) => {
  console.error("오류:", err);
  process.exit(1);
});
