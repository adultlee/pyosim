"""tidy row 스키마 정의."""

import pandas as pd

COLUMNS = [
    "선거_회차", "선거일", "선거종류", "시도", "구시군", "읍면동",
    "선거구명", "선거인수", "투표수", "후보자", "정당", "득표수",
    "무효투표수", "기권수", "level",
]

LEVEL_MAP = {
    "선거일투표": "당일투표",
    "관내사전투표": "사전투표",
    "관외사전투표": "관외사전투표",
    "거소투표": "거소선상",
    "거소·선상투표": "거소선상",
    "선상투표": "거소선상",
    "거소우편투표": "거소선상",
    # 오투입표: 회차마다 원본 라벨이 달라(7·8회는 '잘못 투입·구분된 투표지')
    # 하나로 통일한다.
    "잘못 투입·구분된 투표지": "잘못투입",
    "잘못 투입·구분된 투표": "잘못투입",
    "잘못투입된투표지": "잘못투입",
}


def normalize_level(raw):
    """원본 구분/읍면동 값을 표준 level로 변환. 미매핑은 그대로 반환."""
    key = str(raw or "").strip()
    return LEVEL_MAP.get(key, key)


def to_dataframe(rows):
    """tidy row dict 리스트를 COLUMNS 순서의 DataFrame으로."""
    return pd.DataFrame(rows, columns=COLUMNS)
