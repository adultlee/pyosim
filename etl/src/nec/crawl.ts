/**
 * 9회 전국동시지방선거(0020260603) 개표결과 전체 수집.
 *
 * 선거종류별 파라미터 전략:
 *  - ec2(교육감), ec4(구시군장), ec9(기초비례): sggCityCode(7자리) + townCodeFromSgg(4자리)
 *  - ec3(시도지사), ec8(구시군의원지역): townCode(4자리), sggCityCode=-1
 *  - ec5(시도의원지역), ec6(시도의원비례): sggCityCode(7자리) 선거구 단위로 별도 파일
 *
 * 출력: data/raw/0020260603/ec{code}_city{cityCode}_sgg{sggCode}.html
 */

import { resolve } from "node:path";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  bootstrapSession,
  fetchCities,
  fetchSggs,
  fetchSggCityCodes,
  fetchResultsHtml,
  cacheRaw,
} from "./client.js";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const OUT_DIR = resolve(__dirname, "../../..", "data/raw/0020260603");
const ELECTION_ID = "0020260603";

// townCode 방식: sggCityCode=-1, townCode=구시군코드
const TOWN_CODE_ECS = new Set(["3", "8"]);
// sggCityCode 선거구 단위 방식 (파일명에 선거구코드 사용)
const SGG_DISTRICT_ECS = new Set(["5", "6"]);

const ELECTION_CODES = ["2", "3", "4", "5", "6", "8", "9"];

function isEmptyHtml(path: string): boolean {
  try {
    return readFileSync(path, "utf8").includes("검색된 결과가 없습니다");
  } catch {
    return true;
  }
}

async function fetchAndCache(
  outPath: string,
  query: Parameters<typeof fetchResultsHtml>[0],
  cookie: string,
  onRefresh: () => Promise<string>,
): Promise<{ saved: boolean; cookie: string }> {
  try {
    const html = await fetchResultsHtml(query, cookie);
    await cacheRaw(outPath, html);
    process.stdout.write(`  저장: ${outPath.split("/").pop()} (${html.length}b)\n`);
    return { saved: true, cookie };
  } catch {
    const newCookie = await onRefresh();
    try {
      const html = await fetchResultsHtml(query, newCookie);
      await cacheRaw(outPath, html);
      process.stdout.write(`  재시도 성공: ${outPath.split("/").pop()} (${html.length}b)\n`);
      return { saved: true, cookie: newCookie };
    } catch (err) {
      console.error(`  실패: ${outPath.split("/").pop()} — ${err}`);
      return { saved: false, cookie: newCookie };
    }
  }
}

async function main() {
  console.log("세션 획득 중...");
  let cookie = await bootstrapSession();

  let total = 0;
  let skipped = 0;

  for (const electionCode of ELECTION_CODES) {
    const citiesRaw = (await fetchCities(ELECTION_ID, electionCode, cookie)) as any;
    const cities: { CODE: number; NAME: string }[] = citiesRaw?.jsonResult?.body ?? [];

    if (cities.length === 0) {
      console.log(`[ec${electionCode}] 시도 없음 — 건너뜀`);
      continue;
    }

    console.log(`\n[ec${electionCode}] 시도 ${cities.length}개`);

    for (const city of cities) {
      const sggs = await fetchSggs(ELECTION_ID, electionCode, city.CODE, cookie);
      if (sggs.length === 0) continue;

      if (TOWN_CODE_ECS.has(electionCode)) {
        // ec3, ec8: townCode 방식 — 구시군 단위 파일
        for (const sgg of sggs) {
          const fileName = `ec${electionCode}_city${city.CODE}_sgg${sgg.CODE}.html`;
          const outPath = `${OUT_DIR}/${fileName}`;
          if (existsSync(outPath) && !isEmptyHtml(outPath)) { skipped++; continue; }

          const result = await fetchAndCache(
            outPath,
            { electionId: ELECTION_ID, electionCode, cityCode: String(city.CODE),
              sggCityCode: "-1", townCodeFromSgg: "-1", townCode: String(sgg.CODE) },
            cookie,
            () => bootstrapSession().then(c => { cookie = c; return c; }),
          );
          if (result.saved) total++;
          cookie = result.cookie;
        }
      } else if (SGG_DISTRICT_ECS.has(electionCode)) {
        // ec5, ec6: sggCityCode(7자리) 선거구 단위 — 파일명에 선거구코드 사용
        const districts = await fetchSggCityCodes(ELECTION_ID, electionCode, city.CODE, cookie);
        if (districts.length === 0) continue;

        for (const dist of districts) {
          // 파일명: ec5_city1100_sgg5110101.html (선거구코드)
          const fileName = `ec${electionCode}_city${city.CODE}_sgg${dist.CODE}.html`;
          const outPath = `${OUT_DIR}/${fileName}`;
          if (existsSync(outPath) && !isEmptyHtml(outPath)) { skipped++; continue; }

          // townCodeFromSgg: 선거구코드 중간 4자리 (구시군코드)
          const townCodeFromSgg = dist.CODE.slice(1, -2);

          const result = await fetchAndCache(
            outPath,
            { electionId: ELECTION_ID, electionCode, cityCode: String(city.CODE),
              sggCityCode: dist.CODE, townCodeFromSgg },
            cookie,
            () => bootstrapSession().then(c => { cookie = c; return c; }),
          );
          if (result.saved) total++;
          cookie = result.cookie;
        }
      } else {
        // ec2, ec4, ec9: sggCityCode(7자리) + townCodeFromSgg(4자리)
        const sggCityCodes = await fetchSggCityCodes(ELECTION_ID, electionCode, city.CODE, cookie);
        const sggCityMap = new Map(sggCityCodes.map(s => [s.CODE.slice(1, -2), s.CODE]));

        for (const sgg of sggs) {
          const fileName = `ec${electionCode}_city${city.CODE}_sgg${sgg.CODE}.html`;
          const outPath = `${OUT_DIR}/${fileName}`;
          if (existsSync(outPath) && !isEmptyHtml(outPath)) { skipped++; continue; }

          const sggCityCode = sggCityMap.get(sgg.CODE) ?? sgg.CODE;

          const result = await fetchAndCache(
            outPath,
            { electionId: ELECTION_ID, electionCode, cityCode: String(city.CODE),
              sggCityCode, townCodeFromSgg: String(sgg.CODE) },
            cookie,
            () => bootstrapSession().then(c => { cookie = c; return c; }),
          );
          if (result.saved) total++;
          cookie = result.cookie;
        }
      }
    }
  }

  console.log(`\n완료 — 저장 ${total}건 / 스킵 ${skipped}건`);
}

main().catch((err) => {
  console.error("치명적 오류:", err);
  process.exit(1);
});
