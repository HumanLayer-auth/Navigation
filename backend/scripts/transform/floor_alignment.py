# local_m 좌표에 2D 아핀을 적용하는 유틸.
#
# 예전에는 여기서 층 정렬 아핀을 피팅했다. Studio가 층마다 좌표 변환을 따로
# 피팅해 내보내 층별 local_m 스케일이 달랐고(2F 111x94m · 3F 70x85m · 4F 67x102m),
# 백엔드는 건물당 변환을 하나만 쓰므로 엘리베이터를 대응점 삼아 모든 층을
# 기준층 프레임으로 맞춰야 했다.
#
# 지금은 다베오 원본 좌표계를 전 층이 그대로 공유한다
# (scripts/transform/build_studio_from_dabeeo.py). 맞출 것이 없으므로 피팅도,
# shear/잔차 게이트도 필요 없다 — 좌표를 찍는 함수만 남는다.
#
# 다른 좌표 프레임의 층을 섞어야 할 일이 생기면 정렬 로직을 되살려야 한다.
# 커밋 c81aad3 이전 이력에 남아 있다.

from __future__ import annotations

Affine = tuple[tuple[float, float, float], tuple[float, float, float]]
IDENTITY: Affine = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))


def apply(affine: Affine, x: float, y: float) -> tuple[float, float]:
    (a, b, c), (d, e, f) = affine
    return a * x + b * y + c, d * x + e * y + f


def apply_point(affine: Affine, point: dict) -> dict:
    x, y = apply(affine, point["x"], point["y"])
    return {"x": round(x, 6), "y": round(y, 6)}
