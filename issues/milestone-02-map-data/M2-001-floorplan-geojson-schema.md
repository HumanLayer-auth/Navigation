# M2-001 · 평면도 GeoJSON 스키마와 샘플 데이터 확정

- **상태**: Draft
- **마일스톤**: M2 · 실내 지도 데이터와 기본 경로
- **권장 진행**: 2주차 초반
- **컴포넌트**: data / api
- **GitHub**: -
- **선행 이슈**: M1-002

## 설명

Navigation의 실내 지도, 경로 계산, Particle Filter, RAG 목적지 검색은 모두 같은 평면도 데이터를
바라봐야 한다. 이 이슈는 데모 건물 1개를 기준으로 GeoJSON 스키마를 고정하고, 이후 기능들이
공통으로 사용할 샘플 데이터를 준비한다.

데이터는 처음부터 완벽할 필요가 없다. 대신 벽, 보행 가능 영역, POI, 입구, 경로 그래프가 한 파일
또는 명확한 파일 묶음 안에서 일관되게 표현되어야 한다.

## 작업 내용

### 1. 스키마 확정

- `building` 메타 정보에 `id`, `name`, `floors`, `entrances`를 포함한다.
- 층별 GeoJSON Feature에 아래 `properties.type`을 사용한다.
  - `wall`: 통과 불가 선분
  - `corridor`: 보행 가능 영역
  - `door`: 문/입구 후보
  - `poi`: 목적지 후보
  - `node`: 경로 그래프 노드
  - `edge`: 경로 그래프 간선
- POI에는 `id`, `name`, `floor`, `aliases`, `category`를 둔다.

### 2. 샘플 데이터 작성

- 데모 건물 1개와 1~2개 층을 만든다.
- 최소 POI 5개를 포함한다.
  - 예: 입구, 화장실, 엘리베이터, 계단, 카페/강의실
- 경로 계산이 가능하도록 node/edge를 연결한다.
- 좌표계는 PDR과 잘 맞는 건물 로컬 좌표(미터)를 우선 사용한다.

### 3. 백엔드 응답 정리

- `/buildings`, `/buildings/{id}`, `/buildings/{id}/floors/{floor}` 응답이 새 스키마를 반환하도록 맞춘다.
- 잘못된 건물 ID나 층 요청에 대한 404 응답을 유지한다.
- 데이터 구조를 `api/README.md` 또는 `docs/research/06-tech-stack.md`에 연결해 설명한다.

## 수용 기준

- 데모 건물 1개가 실제 앱 렌더링과 경로 계산에 쓸 수 있는 수준으로 준비되어 있다.
- 벽, POI, 입구, route node/edge가 스키마상 구분된다.
- `/buildings/{id}/floors/{floor}` 응답만 보고도 클라이언트가 층 평면도를 그릴 수 있다.
- POI aliases가 있어 M5의 자연어 목적지 파싱으로 이어질 수 있다.

## 검증

```powershell
cd api
pytest
uvicorn app.main:app --reload
```

- `GET /buildings`
- `GET /buildings/{id}`
- `GET /buildings/{id}/floors/{floor}`

위 응답을 Swagger UI 또는 curl로 확인한다.

## 범위 밖

- 실제 건물 CAD/이미지 자동 변환
- 다건물 관리 UI
- RAG 인덱싱
- Particle Filter 벽 교차 판정 최적화
