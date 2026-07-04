# Navigation

> 경진대회용 Navigation 프로젝트 - 경로 안내, 사용자 흐름, 데모 구현을 한 저장소에서 관리한다.

## 디렉토리 구조

```text
.
|-- .gitignore
|-- .github/
|   `-- workflows/
|       `-- project-automation.yml   # 이슈/PR 이벤트 -> Projects 보드 Status 자동 이동
|-- docs/
|   |-- navigation-overview.md        # 프로젝트 개요와 결정 기록
|   `-- research-notes.md             # 조사/근거/레퍼런스 정리
|-- prompt/                           # CI/CD 자동화 작업별 프롬프트
|   |-- create-issues.md              # cicd-issues.md -> GitHub 이슈 생성
|   |-- design-cicd-issues.md         # CI/CD 파이프라인 설계 -> 이슈 명세
|   |-- implement-issue.md            # 보드 최우선 이슈를 GitHub Flow로 구현
|   |-- label-cd.md                   # CD 라벨 생성/업데이트
|   `-- label-ci.md                   # CI 라벨 생성/업데이트
|-- issues/
|   `-- issue.md                      # 마일스톤별 이슈 초안과 설명
|-- AGENTS.md                         # 에이전트 작업 라우팅 / 규칙
|-- HISTORY.md                        # 변경 이력
|-- VERSION.md                        # 버전 정보
`-- README.md                         # 이 문서
```

## 초기 운영 규칙

- 프로젝트 기획, 기술 선택, 일정 변경은 `docs/navigation-overview.md`에 먼저 남긴다.
- 자동화 작업은 `AGENTS.md`의 라우팅 표를 기준으로 `prompt/`의 전문을 먼저 읽고 수행한다.
- 큰 병합이나 버전 변경은 `HISTORY.md`와 `VERSION.md`를 함께 갱신한다.
- 마일스톤별 GitHub 이슈 초안과 설명은 `issues/issue.md`에 먼저 정리한다.

## 더현대서울 지도 데이터셋 구축

더현대서울 실내 내비게이션 데모용 원천 데이터를 추출한다.

생성 산출물:

- `output/thehyundai_building.geojson`
- `output/thehyundai_building_summary.json`
- `output/floor_assets/manifest.json`
- `output/floor_assets/page_screenshot.png`
- `output/floor_assets/highres_screenshot.png`
- `output/floor_assets/map_element_screenshot.png`
- `output/thehyundai_dataset_summary.json`

입력 SHP 기본 파일명은 `AL_D010_11_20260609.shp`이다. 스크립트는 현재 작업 디렉토리 아래에서
`서울특별시 gis 데이터`, `서울특별시 GIS데이터` 등 유사 폴더명을 먼저 찾고, 실패하면 같은 파일명을 재귀 검색한다.

### 실행 방법

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python scripts/extract_thehyundai_building.py
python scripts/extract_ehyundai_floor_assets.py
python scripts/build_thehyundai_dataset.py
python scripts/build_navigation_map.py
python scripts/generate_preview.py
```

SHP 경로를 명시하려면 다음처럼 실행한다.

```bash
python scripts/extract_thehyundai_building.py --shp "서울특별시 GIS데이터/AL_D010_11_20260609.shp"
python scripts/build_thehyundai_dataset.py --shp "서울특별시 GIS데이터/AL_D010_11_20260609.shp"
```

후처리 파이프라인은 `output/navigation_map.json`, `output/preview.html`, `output/debug/*.png`를 생성한다.
상세 실행 옵션은 `scripts/README.md`를 참고한다.
