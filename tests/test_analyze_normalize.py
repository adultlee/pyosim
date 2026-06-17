"""analyze_twin_votes 의 읍면동 정규화(투표구→읍면동 합산) 테스트.

3회 지방선거 원본은 읍면동 컬럼에 투표구 단위(`동면제1투`)나
동명 중복(`가평읍 가평읍`)이 들어 있어 같은 동이 여러 키로 쪼개진다.
그룹핑 키를 읍면동으로 통일하기 위한 정규화 함수를 검증한다.
"""

import pandas as pd

from analyze_twin_votes import (
    _normalize_emd_local,
    _emd_from_precinct,
    _emd_turnout_map,
)


def test_precinct_suffix_제N투_제거():
    assert _normalize_emd_local("동면제1투") == "동면"
    assert _normalize_emd_local("후평2동제3투") == "후평2동"
    assert _normalize_emd_local("석사동제7투") == "석사동"


def test_동명_중복_제거():
    assert _normalize_emd_local("가평읍 가평읍") == "가평읍"
    assert _normalize_emd_local("신사동 신사동") == "신사동"
    assert _normalize_emd_local("논현제1동 논현제1동") == "논현제1동"


def test_정상_읍면동은_그대로():
    # 4~9회의 깨끗한 읍면동명은 건드리지 않는다
    assert _normalize_emd_local("청운효자동") == "청운효자동"
    assert _normalize_emd_local("중화산1동") == "중화산1동"
    assert _normalize_emd_local("조치원읍") == "조치원읍"


def test_서로_다른_동은_중복으로_합치지_않음():
    # 공백 두 토큰이라도 같은 단어 반복이 아니면 그대로 둔다
    assert _normalize_emd_local("일도1동") == "일도1동"
    assert _normalize_emd_local("강일동 고덕제2동") == "강일동 고덕제2동"


def test_투표구_동명에_중점_들어간_경우():
    # 총선 18·19대: '종로1.2.3.4가동제1투', '미아제6.7동제2투' 형태.
    # 동명에 깨진 중점(.)이 들어 있어도 제N투를 떼고 동명을 보존해야 한다.
    assert _emd_from_precinct("종로1.2.3.4가동제1투") == "종로1.2.3.4가동"
    assert _emd_from_precinct("미아제6.7동제2투") == "미아제6.7동"
    assert _emd_from_precinct("신천1.2동제3투") == "신천1.2동"


def test_숫자없이_투로_끝나는_투표구():
    # 총선 16대: '중앙동투' (제N 없이 투만 붙음)
    assert _emd_from_precinct("중앙동투") == "중앙동"
    assert _emd_from_precinct("팔달동투") == "팔달동"


def test_구시군_접두_공백이_붙은_투표구():
    # 총선 19대: '연기군 장기면제1투' (구시군명 + 공백 + 동명+제N투)
    assert _emd_from_precinct("연기군 장기면제1투") == "장기면"
    assert _emd_from_precinct("연기군 부용면제2투") == "부용면"


def test_emd_turnout_map_투표구별_한번씩_합산():
    # 같은 정규화 동(동면)의 투표구 2개(동면제1투/제2투)에서
    # 투표수는 투표구별로 한 번씩만 더해야 한다(후보 행마다 중복 제거).
    df = pd.DataFrame({
        "회차": [9, 9, 9, 9],
        "동": ["동면", "동면", "동면", "동면"],
        "원본동": ["동면제1투", "동면제1투", "동면제2투", "동면제2투"],
        "투표수": [100, 100, 50, 50],
        "선거인수": [120, 120, 60, 60],
    })
    result = _emd_turnout_map(df, ["회차", "동"], "원본동")
    # 동면: 투표수 100+50=150, 선거인수 120+60=180
    assert result[(9, "동면")] == {"투표수": 150, "선거인수": 180}


def test_enrich_location_1위와_투표수_채움():
    from analyze_twin_votes import _enrich_location
    loc = {"읍면동": "삼서면"}
    vote_by_id = {"더불어민주당": 716, "국민의힘": 41, "진보당": 28}
    turnout = {"투표수": 964, "선거인수": 1000}
    _enrich_location(loc, vote_by_id, turnout)
    assert loc["투표수"] == 964
    assert loc["선거인수"] == 1000
    assert loc["1위"] == "더불어민주당"
    assert loc["1위득표"] == 716


def test_enrich_location_turnout_없으면_생략():
    from analyze_twin_votes import _enrich_location
    loc = {"읍면동": "삼서면"}
    _enrich_location(loc, {"진보당": 28, "정의당": 5}, None)
    assert "투표수" not in loc
    assert loc["1위"] == "진보당"
