"""analyze_twin_votes 의 읍면동 정규화(투표구→읍면동 합산) 테스트.

3회 지방선거 원본은 읍면동 컬럼에 투표구 단위(`동면제1투`)나
동명 중복(`가평읍 가평읍`)이 들어 있어 같은 동이 여러 키로 쪼개진다.
그룹핑 키를 읍면동으로 통일하기 위한 정규화 함수를 검증한다.
"""

from analyze_twin_votes import _normalize_emd_local, _emd_from_precinct


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
