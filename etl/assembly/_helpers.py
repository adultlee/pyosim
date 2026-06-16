"""파서 공통 유틸리티. 각 회차 파서에서 임포트."""

SIDO_NORMALIZE = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원도": "강원", "충청북도": "충북", "충청남도": "충남",
    "전라북도": "전북", "전라남도": "전남", "경상북도": "경북",
    "경상남도": "경남", "제주특별자치도": "제주",
    "서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천",
    "광주": "광주", "대전": "대전", "울산": "울산", "세종": "세종",
    "경기": "경기", "강원": "강원", "충북": "충북", "충남": "충남",
    "전북": "전북", "전남": "전남", "경북": "경북", "경남": "경남", "제주": "제주",
    "강원특별자치도": "강원", "전북특별자치도": "전북",
}

_SKIP_ROW_KEYWORDS = {"합계", "소계", "부재자", "부재자투표", "잘못투입된투표지",
                      "계", "잘못된투표지", "국내부재자투표"}


def normalize_sido(raw):
    return SIDO_NORMALIZE.get(str(raw).strip(), str(raw).strip())


def to_int(val):
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def parse_party_candidate(col_str):
    if not col_str or str(col_str).strip() in ("", "\n", "계"):
        return None, None
    raw = str(col_str)
    if "\n" in raw:
        parts = [part.strip() for part in raw.split("\n") if part.strip()]
        if len(parts) == 2:
            return parts[0], parts[1]
        if len(parts) == 1:
            return parts[0], ""
        return None, None
    return raw.strip(), ""


def is_skip_row(val):
    if not val:
        return True
    s = str(val).strip()
    if not s or s in _SKIP_ROW_KEYWORDS:
        return True
    return "소계" in s or "합계" in s
