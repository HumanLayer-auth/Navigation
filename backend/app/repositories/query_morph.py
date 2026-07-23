# 질의 형태소 정규화 (Kiwi). 조사·어미·용언을 떼어 경량 매칭이 쓰는 질의를 안정화한다.
# 설계 근거: docs/backend/native/KIWI.md
#
# 핵심 원칙:
# - Kiwi 인스턴스는 지연 로드 싱글턴. 로드가 실패해도 예외를 삼켜 None을 돌려주고,
#   호출부(query_search)는 기존 꼬리 제거 규칙으로 폴백한다. 매칭 품질만 떨어지고 서버는 산다.
# - 형태소를 다시 이어 붙이지 않고 **원문에서 제거 대상 스팬만 지운다.**
#   토큰을 공백으로 join하면 "가게A" → "가게 A"가 되어 이름 정확 일치가 깨진다.
#   반대로 공백 없이 join하면 "TAX REFUND" → "TAXREFUND"가 되어 또 깨진다. 원문 보존이 유일한 안전한 답.
# - 태그는 허용 목록이 아니라 **제거 목록**으로 다룬다. 모르는 태그는 남기는 쪽이 기존 동작에 가깝다.

from __future__ import annotations

import re
import threading
from typing import Any

# 제거할 품사 태그. 접두사로 검사한다.
#   J*   조사        — "화장실이", "스타벅스는", "엘리베이터까지"
#   E*   어미        — "-야", "-어", "-고"
#   V*   용언        — "가고 싶어", "급해"
#   MM   관형사      — "몇"
#   MA*  부사        — "빨리", "혹시"
#   NP   대명사      — "어디", "여기"
#   XSV/XSA 용언파생접미사
# 남기는 것: NNG·NNP(명사), NNB(의존명사 — Kiwi가 "주차"를 NNB로 본다), SL(외국어),
#            SN(숫자), SH(한자), XSN(명사파생접미사 — "애들"의 "들").
_DROP_TAGS = ("J", "E", "V", "MM", "MA", "NP", "XSV", "XSA")

_WHITESPACE = re.compile(r"\s+")

_lock = threading.Lock()
_kiwi: Any | None = None
_load_failed = False


def _user_words() -> list[str]:
    # 브랜드 신조어가 "마뗑킴" → "마"+"뗑킴"으로 오분해되는 걸 막는다.
    # 동의어 사전의 키·값 양쪽을 그대로 쓴다 — 별도 리소스 파일을 새로 만들지 않는다.
    # import를 함수 안에서 하는 이유: query_search가 이 모듈을 import하므로 순환을 피한다.
    from app.repositories.query_search import _synonyms

    words = set()
    for alias, canonical in _synonyms().items():
        words.add(alias)
        words.add(canonical)
    return sorted(word for word in words if word)


def _get_kiwi() -> Any | None:
    """Kiwi를 한 번만 만들어 재사용. 실패 시 None → 호출부가 폴백한다."""
    global _kiwi, _load_failed

    if _kiwi is not None or _load_failed:
        return _kiwi

    # 락 안에서 재확인 — 동시 요청이 Kiwi를 두 번 만들지 않게(생성 비용이 수백 ms).
    with _lock:
        if _kiwi is None and not _load_failed:
            try:
                from kiwipiepy import Kiwi

                kiwi = Kiwi()
                for word in _user_words():
                    kiwi.add_user_word(word, "NNP")
                _kiwi = kiwi
            except Exception as error:  # noqa: BLE001 - 어떤 실패든 경량 경로는 살린다
                print(f"형태소 분석기 로드 실패(kiwipiepy): {error}")
                _load_failed = True
    return _kiwi


def _is_dropped(tag: str) -> bool:
    return tag.startswith(_DROP_TAGS)


def normalize(text: str) -> str | None:
    """조사·어미·용언을 뗀 질의를 돌려준다. 분석 불가·남는 게 없으면 None(→ 호출부 폴백).

    원문의 문자 위치를 유지하므로 "가게A 어디야" → "가게A", "TAX REFUND" → "TAX REFUND".
    """
    kiwi = _get_kiwi()
    if kiwi is None:
        return None

    try:
        tokens = kiwi.tokenize(text)
    except Exception as error:  # noqa: BLE001 - 이 질의만 폴백, 서버는 계속
        print(f"형태소 분석 실패({text!r}): {error}")
        return None

    # 제거 대상 스팬을 공백으로 덮는다. 삭제가 아니라 공백 치환인 이유는
    # "화장실이 어디야"에서 "이"만 지웠을 때 앞뒤 토큰이 잘못 붙는 걸 막기 위해서다.
    chars = list(text)
    removed_any = False
    for token in tokens:
        if token.len > 0 and _is_dropped(token.tag):
            chars[token.start : token.start + token.len] = [" "] * token.len
            removed_any = True

    if not removed_any:
        return _WHITESPACE.sub(" ", text).strip() or None

    result = _WHITESPACE.sub(" ", "".join(chars)).strip()
    return result or None  # 전부 떨어져 나갔으면 폴백 — 분석기가 브랜드명을 날린 경우 방어
