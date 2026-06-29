# M5-001 · 자연어 목적지 파싱 RAG baseline

- **상태**: Draft
- **마일스톤**: M5 · RAG, 평가, 발표 데모 완성
- **권장 진행**: 5주차 초반
- **컴포넌트**: api / rag / client
- **GitHub**: -
- **선행 이슈**: M2-001, M2-003, M4-003

## 설명

RAG는 사용자가 "3층 화장실 어디야?"처럼 자연어로 목적지를 입력했을 때 POI 후보를 찾아 경로 안내로
연결하는 기능이다. 이 이슈는 완전한 챗봇이 아니라, 데모에 필요한 자연어 목적지 파싱 baseline을 만든다.

시간이 부족하면 LLM 생성까지 가지 않고 POI aliases 기반 검색 + 후보 랭킹으로 축소한다.

## 작업 내용

### 1. POI 텍스트 인덱싱

- M2-001의 POI `name`, `aliases`, `category`, `floor`를 검색 텍스트로 변환한다.
- 초기 버전은 FastAPI 프로세스 내부 메모리 인덱스로 시작한다.
- 여유가 있으면 sentence-transformers + FAISS를 붙인다.

### 2. `/query/destination` 구현

- 기존 stub 응답을 실제 POI 검색 응답으로 바꾼다.
- 응답에 `poi`, `candidates`, `message`를 포함한다.
- 애매한 질의는 후보 2~3개를 반환한다.
- 결과 없음 상태를 명확히 반환한다.

### 3. 클라이언트 연결

- 목적지 검색 UI에서 자연어 텍스트를 입력받는다.
- `/query/destination` 응답의 POI를 경로 플래너에 전달한다.
- 후보가 여러 개면 사용자가 선택할 수 있게 한다.

### 4. 테스트 데이터

- 데모 POI별 한국어 별칭을 준비한다.
  - 예: 화장실, restroom, WC
  - 예: 엘리베이터, lift, elevator
- 데모 질의 10개 정도를 fixture로 둔다.

## 수용 기준

- 자연어 질의로 데모 POI를 찾을 수 있다.
- 후보 여러 개, 결과 없음, 정상 매칭 케이스가 모두 처리된다.
- 선택된 POI가 기존 경로 안내 흐름으로 연결된다.
- `/query/destination` 테스트가 통과한다.

## 검증

```powershell
cd api
pytest

cd ..\client
flutter analyze
flutter test
flutter run
```

## 범위 밖

- 완전한 건물 정보 Q&A
- 다국어 실시간 번역
- 공사/폐쇄 구간 RAG 우회
- 대규모 벡터 DB 운영
