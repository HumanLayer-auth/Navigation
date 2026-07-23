"""실데이터 29개로 최종 AI 하이브리드 경로와 FAISS 단독 결과를 비교한다.

`backend/`에서 실행:
    python -m scripts.seed.reset_and_seed
    python -m scripts.evaluate_query_hybrid

기대 패턴은 이름·카테고리·서브카테고리에 대한 최소 자동 판정이다. 숫자는 회귀 비교용이며,
최종 안내 적합성은 실패 행을 사람이 함께 확인한다.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.database import SessionLocal
from app.repositories import query_search, query_semantic

BUILDING_ID = "thehyundai-seoul"

POSITIVE_QUERIES = [
    ("음식", "밥 먹을 곳", "restaurant|식음료|취식"),
    ("음식", "배고픈데 뭐 먹지", "restaurant|식음료"),
    ("분식", "김밥 같은 분식", "restaurant|김밥|분식"),
    ("카페", "커피 마시고 싶어", "커피|카페|restaurant"),
    ("디저트", "디저트랑 케이크", "베이커리|케이크|restaurant"),
    ("뷰티", "화장품 사려고", "화장품"),
    ("뷰티", "향수 보고 싶어", "화장품|향수"),
    ("뷰티", "립스틱 어디", "화장품"),
    ("키즈", "애들 옷", "키즈|아동|유아"),
    ("키즈", "아기 장난감", "토이|완구|키즈"),
    ("슈즈", "신발 파는 데", "슈즈"),
    ("슈즈", "운동화 사고 싶다", "슈즈|스포츠"),
    ("패션", "가방 보러 왔어", "잡화|액세서리|명품|가방"),
    ("패션", "남자 정장", "컨템포러리|정장|수트"),
    ("명품", "명품 매장", "명품"),
    ("스포츠", "등산복 아웃도어", "아웃도어|스포츠"),
    ("리빙", "그릇이나 주방용품", "리빙|주방"),
    ("문구", "예쁜 문구류", "문구|팬시"),
    ("시설", "화장실 급해", "restroom|화장실"),
    ("시설", "엘리베이터 어디", "elevator|엘리베이터"),
    ("시설", "에스컬레이터", "escalator|에스컬레이터"),
    ("시설", "현금 뽑을 데", "ATM|현금|은행"),
    ("시설", "짐 맡길 곳", "보관|facility"),
    ("선물", "선물 살 만한 곳", "기프트|선물|facility"),
    ("정확명", "스타벅스", "스타벅스|커피|restaurant"),
]

NEGATIVE_QUERIES = ["asdfqwerzxcv", "ㅋㅋㅋㅋㅋ", "zzzzzzz", "19283746"]


def _match_text(match: dict[str, Any] | None) -> str:
    if match is None:
        return ""
    return " ".join(
        str(match.get(key) or "") for key in ("name", "category", "subcategory")
    )


def _semantic_text(hit: tuple[Any, Any, Any] | None) -> str:
    if hit is None:
        return ""
    _score, store, _floor = hit
    return " ".join(
        str(value or "") for value in (store.name, store.category, store.subcategory)
    )


def _matches(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def evaluate() -> dict[str, Any]:
    session = SessionLocal()
    try:
        rows = query_search._load_stores(session, BUILDING_ID)
        query_semantic.reset_indexes()
        results = []

        for label, text, expected_pattern in POSITIVE_QUERIES:
            light = query_search._rank_with_candidate(rows, text)
            final = query_search.match_ai_destination(session, BUILDING_ID, text)
            semantic = query_semantic.semantic_search(session, BUILDING_ID, text)
            final_match = final["match"]
            results.append(
                {
                    "label": label,
                    "query": text,
                    "route": (
                        "light"
                        if query_search._is_confident_light_match(light)
                        else "semantic"
                    ),
                    "light_tier": light[0][0] if light else None,
                    "light_name": light[0][4].name if light else None,
                    "final_name": final_match["name"] if final_match else None,
                    "final_floor": final_match["floor_name"] if final_match else None,
                    "final_pass": _matches(
                        expected_pattern, _match_text(final_match)
                    ),
                    "semantic_name": semantic[1].name if semantic else None,
                    "semantic_floor": semantic[2].name if semantic else None,
                    "semantic_score": round(semantic[0], 3) if semantic else None,
                    "semantic_pass": _matches(
                        expected_pattern, _semantic_text(semantic)
                    ),
                }
            )

        for text in NEGATIVE_QUERIES:
            final = query_search.match_ai_destination(session, BUILDING_ID, text)
            semantic = query_semantic.semantic_search(session, BUILDING_ID, text)
            results.append(
                {
                    "label": "부정",
                    "query": text,
                    "route": "semantic",
                    "light_tier": None,
                    "light_name": None,
                    "final_name": final["match"]["name"] if final["match"] else None,
                    "final_floor": (
                        final["match"]["floor_name"] if final["match"] else None
                    ),
                    "final_pass": final["status"] == "no_match",
                    "semantic_name": semantic[1].name if semantic else None,
                    "semantic_floor": semantic[2].name if semantic else None,
                    "semantic_score": round(semantic[0], 3) if semantic else None,
                    "semantic_pass": semantic is None,
                }
            )

        return {
            "summary": {
                "total": len(results),
                "positive": len(POSITIVE_QUERIES),
                "negative": len(NEGATIVE_QUERIES),
                "final_pass": sum(row["final_pass"] for row in results),
                "semantic_pass": sum(row["semantic_pass"] for row in results),
                "light_routes": sum(row["route"] == "light" for row in results),
                "semantic_routes": sum(row["route"] == "semantic" for row in results),
            },
            "results": results,
        }
    finally:
        session.close()


def main() -> None:
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
