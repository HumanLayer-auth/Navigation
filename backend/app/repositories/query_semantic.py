# 자연어 질의 의미 검색 (문장 임베딩 + FAISS).
# 형태소 정규화(query_morph)는 경량 1차에만 적용된다 — 여기엔 질의 원문이 그대로 들어온다.
# 문장 임베딩은 조사·어미가 붙은 문장을 그대로 처리하는 게 낫고, 인덱스 텍스트를 바꾸면
# 임계값 0.50의 튜닝 근거(8절)가 무효가 되기 때문이다.
# 경량 매칭이 놓쳤거나 서로 다른 이름을 여럿 잡은 부분 일치를 의미로 보완한다 — 하이브리드의 2차.
# 설계 근거: docs/backend/native/FAISS.md
#
# 핵심 원칙:
# - 모델(ko-sroberta-multitask)은 지연 로드 싱글턴. 로드가 실패해도 예외를 삼켜서
#   경량 경로(1차)는 계속 동작한다. AI 경로만 조용히 비활성된다.
# - faiss·sentence_transformers import는 함수 안에서만. 이 모듈을 건드리지 않는 테스트·요청은
#   무거운 의존성을 로드하지 않는다.
# - 인덱스는 건물별로 최초 질의 때 1회 빌드해 메모리 상주. 코퍼스가 작아 IndexFlatIP 브루트포스로 충분.
# - 코사인 유사도 = L2 정규화 임베딩 + IndexFlatIP 내적. 임계값 미만은 no_match(엉뚱한 매장 방지).

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

import numpy as np

from app.repositories.query_search import _load_stores  # 건물/층 조인 재사용

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Floor, Store

_MODEL_NAME = "jhgan/ko-sroberta-multitask"

# 코사인 유사도 임계값. 이 값 미만이면 no_match로 처리해 엉뚱한 매장 반환을 막는다.
# thehyundai-seoul 실데이터로 튜닝(FAISS.md 8절·11절):
#   유효한 ATM 질의 0.464와 무의미 문자열("asdfqwerzxcv") 0.458의 간격이 0.006뿐이다.
#   임계값을 내리면 둘 다 통과하므로, 틀린 길 안내보다 no_match를 택해 0.50을 유지한다.
#   데이터나 인덱스 문서를 바꾸면 29개 평가 세트로 다시 튜닝한다.
SIMILARITY_THRESHOLD = 0.50

# 상위 몇 건을 받아 층 필터를 적용할지. 코퍼스가 작아 넉넉히 받는다.
_TOP_K = 10

_model_lock = threading.Lock()
_model: Any | None = None
_model_load_failed = False

_index_lock = threading.Lock()
# building_id -> (faiss.Index, [store_id ...]) — 벡터 행 순서와 store_id를 짝지어 역참조.
_indexes: dict[str, tuple[Any, list[str]]] = {}


def _get_model() -> Any | None:
    """모델을 한 번만 로드해 재사용. 로드 실패 시 None을 돌려 AI 경로만 비활성한다."""
    global _model, _model_load_failed

    if _model is not None or _model_load_failed:
        return _model

    # 락 안에서 한 번 더 확인 — 동시 요청이 모델을 두 번 로드하지 않게.
    with _model_lock:
        if _model is None and not _model_load_failed:
            try:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(_MODEL_NAME)
            except Exception as error:  # noqa: BLE001 - 어떤 실패든 경량 경로는 살린다
                print(f"임베딩 모델 로드 실패({_MODEL_NAME}): {error}")
                _model_load_failed = True
    return _model


def _document_text(store: "Store") -> str:
    # 매장을 임베딩할 텍스트. 이름 + 카테고리로 의미 신호를 만든다.
    parts = [store.name or ""]
    if store.category:
        parts.append(store.category)
    if store.subcategory:
        parts.append(store.subcategory)
    return " ".join(part for part in parts if part).strip()


def _encode(model: Any, texts: list[str]) -> np.ndarray:
    # normalize_embeddings=True → 코사인용 L2 정규화. faiss는 float32 연속 배열을 요구한다.
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return np.ascontiguousarray(vectors, dtype="float32")


def _build_index(session: "Session", building_id: str) -> tuple[Any, list[str]] | None:
    model = _get_model()
    if model is None:
        return None

    rows = _load_stores(session, building_id)  # 건물 전체(층 필터는 검색 후 적용)
    if not rows:
        return None

    import faiss

    # 벡터 행 순서와 store_ids 순서가 1:1로 대응한다 — 검색 결과 position으로 역참조한다.
    store_ids = [store.id for store, _floor in rows]
    vectors = _encode(model, [_document_text(store) for store, _floor in rows])

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    return index, store_ids


def _get_index(session: "Session", building_id: str) -> tuple[Any, list[str]] | None:
    cached = _indexes.get(building_id)
    if cached is not None:
        return cached

    # 모델 로드와 같은 이유로 락 안에서 재확인 — 인덱스를 중복 빌드하지 않게.
    with _index_lock:
        cached = _indexes.get(building_id)
        if cached is None:
            built = _build_index(session, building_id)
            if built is None:
                return None  # 캐시하지 않음 — 모델 준비되면 다음 요청에서 재시도
            _indexes[building_id] = built
            cached = built
    return cached


def reset_indexes() -> None:
    """빌드된 인덱스 캐시를 비운다. 데이터가 바뀐 테스트 사이에서 쓴다."""
    with _index_lock:
        _indexes.clear()


def semantic_search(
    session: "Session",
    building_id: str,
    text: str,
    *,
    current_floor_id: str | None = None,
) -> tuple[float, "Store", "Floor"] | None:
    """건물 인덱스에서 임계값 이상 최상위 (score, Store, Floor) 1건. 없으면 None.

    모델·인덱스가 준비 안 됐거나(로드 실패 등) 임계값 미달이면 None → 호출부가 no_match로 처리.
    """
    model = _get_model()
    if model is None:
        return None

    got = _get_index(session, building_id)
    if got is None:
        return None
    index, store_ids = got

    # 인덱스는 store_id만 캐시한다(교차 요청 지속). ORM 객체는 매 요청 현재 세션으로 새로 로드해
    # detached 객체·stale 층 정보를 피한다.
    rows = {store.id: (store, floor) for store, floor in _load_stores(session, building_id)}

    query_vec = _encode(model, [text])
    k = min(_TOP_K, index.ntotal)
    scores, positions = index.search(query_vec, k)

    # 내림차순 정렬됨. 층 필터로 건너뛰다 처음 만난 온-층 후보로 판정한다.
    for score, pos in zip(scores[0], positions[0]):
        if pos < 0:
            continue
        pair = rows.get(store_ids[pos])
        if pair is None:
            continue  # 인덱스 빌드 후 삭제된 매장 방어
        store, floor = pair
        # 라벨("B2")·내부 id("FL-...") 둘 다 허용 — query_search._load_stores와 같은 규칙.
        # 두 경로가 다른 기준을 쓰면 같은 요청이 경량/의미 검색에서 다르게 걸러진다.
        if current_floor_id is not None and current_floor_id not in (floor.name, floor.id):
            continue
        if float(score) < SIMILARITY_THRESHOLD:
            return None  # 최상위(온-층) 후보가 미달이면 이후도 미달 → no_match
        return float(score), store, floor
    return None
