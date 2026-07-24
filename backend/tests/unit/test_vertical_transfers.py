"""수직 전이 간선 생성(build_transfers) 단위 테스트.

DB 없이 층 dict를 직접 만들어 순수 함수를 검증한다. 실데이터 스모크는
tests/integration/test_real_data_smoke.py가, 서빙은 test_building_graph.py가 덮는다.

검증 기준:
    V1  에스컬레이터는 단방향이고 방향이 층 level과 일치한다(불가능 경로 제거).
    V2  1~2층은 에스컬레이터, 3층+는 엘리베이터가 더 싸다(층수 기반 수단 선택).
"""

from scripts.transform import vertical_transfers as vt


def _esc(node_id: str, x: float, y: float, direction: str) -> dict:
    # trans_code로 방향을 준다 — 실데이터(OB-ESCALATOR_UP/DOWN)와 같은 경로.
    code = "OB-ESCALATOR_UP" if direction == "up" else "OB-ESCALATOR_DOWN"
    return {
        "id": node_id,
        "type": "escalator",
        "name": node_id,
        "position": {"local_m": {"x": x, "y": y}},
        "source": {"trans_code": code},
    }


def _elev(node_id: str, x: float, y: float) -> dict:
    return {
        "id": node_id,
        "type": "elevator",
        "name": node_id,
        "position": {"local_m": {"x": x, "y": y}},
        "source": {"trans_code": "OB-ELEVATOR"},
    }


def _floor(name: str, level: int, nodes: list[dict]) -> dict:
    return {"code": name.lower(), "floor_id": f"F-{name}", "name": name, "level": level, "nodes": nodes}


# V1 — 상행 에스컬레이터는 아래→위 단방향 간선만, 하행은 위→아래 단방향만 만든다.
def test_에스컬레이터는_방향을_지켜_단방향으로_잇는다():
    # 1F/2F에 같은 자리(10,10 상행 / 20,20 하행)의 상·하행 노드를 둔다.
    floors = [
        _floor("1F", 1, [_esc("1F:up", 10, 10, "up"), _esc("1F:dn", 20, 20, "down")]),
        _floor("2F", 2, [_esc("2F:up", 10, 10, "up"), _esc("2F:dn", 20, 20, "down")]),
    ]
    transfers, _unresolved = vt.build_transfers(floors)
    esc = [t for t in transfers if t["mode"] == "escalator"]

    assert esc, "에스컬레이터 전이 간선이 있어야 한다"
    assert all(t["bidirectional"] is False for t in esc), "에스컬레이터는 단방향"

    up = next(t for t in esc if t["from"] == "1F:up")
    assert up["to"] == "2F:up"  # 상행: 아래층 → 위층
    down = next(t for t in esc if t["from"] == "2F:dn")
    assert down["to"] == "1F:dn"  # 하행: 위층 → 아래층

    # 상행 노드가 하행 노드와 섞여 이어지지 않는다(반대 방향 통행 불가).
    assert not [t for t in esc if {t["from"], t["to"]} == {"1F:up", "2F:dn"}]


# 상행 전용을 하행으로 타는 간선이 생기지 않는다 — 상행 노드만 있으면 하행 간선 0.
def test_상행_전용은_하행_간선을_만들지_않는다():
    floors = [
        _floor("1F", 1, [_esc("1F:up", 10, 10, "up")]),
        _floor("2F", 2, [_esc("2F:up", 10, 10, "up")]),
    ]
    transfers, _ = vt.build_transfers(floors)
    esc = [t for t in transfers if t["mode"] == "escalator"]

    assert len(esc) == 1
    assert esc[0]["from"] == "1F:up" and esc[0]["to"] == "2F:up"  # 상행뿐


# 엘리베이터는 샤프트가 서비스하는 모든 층쌍을 양방향으로 잇는다.
def test_엘리베이터는_샤프트_전_층쌍을_직행_연결한다():
    # 같은 자리(10,10)의 엘리베이터가 3개 층에 있다.
    floors = [
        _floor("1F", 1, [_elev("1F:ev", 10, 10)]),
        _floor("2F", 2, [_elev("2F:ev", 10, 10)]),
        _floor("3F", 3, [_elev("3F:ev", 10, 10)]),
    ]
    transfers, _ = vt.build_transfers(floors)
    ele = [t for t in transfers if t["mode"] == "elevator"]

    # 3개 층 → 층쌍 3개(1-2, 2-3, 1-3) 모두 직행 간선.
    assert len(ele) == 3
    assert all(t["bidirectional"] for t in ele)
    pairs = {frozenset(t["floors"]) for t in ele}
    assert pairs == {frozenset(["1F", "2F"]), frozenset(["2F", "3F"]), frozenset(["1F", "3F"])}


# V2 — 층수 기반 비용: 1~2층은 에스컬레이터, 3층+는 엘리베이터가 최단.
def test_비용모델이_층수에_따라_수단을_가른다():
    # 순수 비용 함수로 교차점을 고정한다. 에스컬 = 20×n, 엘리베 = 35 + 5×n.
    def esc_cost(n):
        return vt.ESCALATOR_HOP_M * n

    def elev_cost(n):
        return vt.ELEVATOR_BOARD_M + vt.ELEVATOR_PER_FLOOR_M * n

    assert esc_cost(1) < elev_cost(1)  # 1층: 에스컬레이터
    assert esc_cost(2) < elev_cost(2)  # 2층: 에스컬레이터
    assert elev_cost(3) < esc_cost(3)  # 3층: 엘리베이터
    assert elev_cost(4) < esc_cost(4)  # 4층+: 엘리베이터


# 엘리베이터 비용이 이동 층수에 비례해 커진다(직행이라도 멀수록 비싸다).
def test_엘리베이터_비용은_층수에_비례한다():
    floors = [
        _floor("1F", 1, [_elev("1F:ev", 10, 10)]),
        _floor("2F", 2, [_elev("2F:ev", 10, 10)]),
        _floor("3F", 3, [_elev("3F:ev", 10, 10)]),
    ]
    transfers, _ = vt.build_transfers(floors)
    ele = {frozenset(t["floors"]): t["length_m"] for t in transfers if t["mode"] == "elevator"}

    one_hop = ele[frozenset(["1F", "2F"])]
    two_hop = ele[frozenset(["1F", "3F"])]
    assert one_hop == vt.ELEVATOR_BOARD_M + vt.ELEVATOR_PER_FLOOR_M * 1
    assert two_hop == vt.ELEVATOR_BOARD_M + vt.ELEVATOR_PER_FLOOR_M * 2
    assert two_hop > one_hop
