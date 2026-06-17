"""기존 data_processed/*.csv 무결성 점검 (다운로드 기능 전제 확인용 일회성 스크립트).

ETL 검증 게이트(validate.py) 중 CSV만으로 재현 가능한 검사를 그대로 재실행한다:
  - check_no_duplicate_rows : 키 중복 행
  - check_value_ranges      : 득표 ≤ 투표수 ≤ 선거인수
  - check_official_totals   : 코드에 박힌 공식 1위 득표 대조 (핵심 정답지)
totals 기반 합계 대조(check_totals_match)는 런타임 totals가 필요해 제외.
"""
import pandas as pd

from etl.local import validate as local_v
from etl.assembly import validate as assembly_v
from etl.pres import validate as pres_v
from etl.local.official_totals import OFFICIAL_TOP as LOCAL_TOP
from etl.pres.official_totals import OFFICIAL_TOP as PRES_TOP

try:
    from etl.assembly.official_totals import OFFICIAL_TOP as ASSEMBLY_TOP
except ImportError:
    ASSEMBLY_TOP = {}


def report(name, errors):
    print(f"\n===== {name} =====")
    if not errors:
        print("  ✅ 위반 없음")
        return 0
    print(f"  ❌ 위반 {len(errors)}건")
    for check_name, detail in errors[:30]:
        print(f"    [{check_name}] {detail}")
    if len(errors) > 30:
        print(f"    ... 외 {len(errors) - 30}건")
    return len(errors)


total = 0

# --- 지방선거 ---
df = pd.read_csv("data_processed/지방선거.csv", dtype=str)
for col in ["선거인수", "투표수", "득표수"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df["선거_회차"] = pd.to_numeric(df["선거_회차"], errors="coerce")
errors = local_v.check_no_duplicate_rows(df)
errors += local_v.check_value_ranges(df)
errors += local_v.check_official_totals(df, LOCAL_TOP)
total += report("지방선거", errors)

# --- 총선 ---
df = pd.read_csv("data_processed/국회의원선거.csv", dtype=str)
for col in ["선거인수", "투표수", "득표수"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
errors = assembly_v.check_no_duplicate_rows(df)
errors += assembly_v.check_value_ranges(df)
if ASSEMBLY_TOP:
    errors += assembly_v.check_official_totals(df, ASSEMBLY_TOP)
total += report("국회의원선거", errors)

# --- 대선 ---
df = pd.read_csv("data_processed/대통령선거.csv", dtype=str)
for col in ["선거인수", "투표수", "득표수"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
df["선거_회차"] = pd.to_numeric(df["선거_회차"], errors="coerce")
errors = pres_v.check_no_duplicate_rows(df)
errors += pres_v.check_value_ranges(df)
errors += pres_v.check_official_totals(df, PRES_TOP)
total += report("대통령선거", errors)

print(f"\n총 위반: {total}건")
raise SystemExit(1 if total else 0)
