# 작업 규칙

## 판단력 — 새 기능을 만들 때

새로운 기능을 만들 때는 다음을 지킨다.

- **AI 결과를 내 말로 풀어서 설명한다.** 생성된 코드/설계를 그대로 받아들이지 않고, 사용자가 자기 말로 이해하고 설명할 수 있도록 근거와 동작을 풀어 준다.
- **정상 동작보다 실패 조건을 먼저 생각한다.** "잘 되는 경우"가 아니라 어디서 깨지는지, 어떤 입력·상태에서 실패하는지를 먼저 짚는다.
- **AI보다 먼저 검증 기준을 정한다.** 구현에 들어가기 전에 "무엇이 충족되면 맞다고 볼지" 검증 기준을 먼저 합의하고, 그 기준으로 결과를 확인한다.

## 프로젝트 세션 규칙

이 저장소는 Flutter 클라이언트 + FastAPI·SQLAlchemy·SQLite 백엔드 데모다. 개발자는 Windows(PowerShell)와 macOS 양쪽에 있다. 작업할 때:

- **개발 실행은 사용자가 볼 수 있는 창 2개(백엔드·프론트)를 foreground로 띄우고, 동시에 로그를 파일로 tee 해서 에이전트도 추적한다.** 백그라운드로 숨기지 않는다.
  - 쉘 버전(PowerShell 5.1/7, bash/zsh)에 따라 `&&`·`;` 체이닝이 깨질 수 있으므로 **명령은 체이닝하지 말고 한 줄씩 순서대로 실행한다.** `cd A && B` 대신 창을 해당 폴더에서 연 뒤 명령만 실행한다. (파이프 `|`는 버전 무관하게 동작하므로 tee에는 파이프를 쓴다.)

  **1) 창 먼저 연다 (해당 작업 폴더에서)**
    ```powershell
    # Windows — 백엔드 창(저장소 루트), 프론트 창(client)
    Start-Process powershell -ArgumentList '-NoExit' -WorkingDirectory 'D:\Navigation'
    Start-Process powershell -ArgumentList '-NoExit' -WorkingDirectory 'D:\Navigation\client'
    ```
    ```bash
    # macOS — Terminal 창 2개
    osascript -e 'tell app "Terminal" to do script "cd ~/Navigation"'
    osascript -e 'tell app "Terminal" to do script "cd ~/Navigation/client"'
    ```

  **2) 백엔드 창에서 순서대로 실행 — Docker (`docker info`가 정상일 때)**
    ```
    docker compose up --build backend 2>&1 | tee backend.log
    ```

  **2') Docker가 없거나 실행 중이 아니면 — 로컬 Python 대체 (백엔드 폴더에서 한 줄씩)**
    ```powershell
    # Windows (backend 폴더로 연 창에서)
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python -m scripts.seed.reset_and_seed
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 2>&1 | Tee-Object -FilePath ..\backend.log
    ```
    ```bash
    # macOS (backend 폴더로 연 창에서)
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python -m scripts.seed.reset_and_seed
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 2>&1 | tee ../backend.log
    ```

  **3) 프론트 창에서 실행 (client 폴더에서)**
    ```
    flutter run -d chrome 2>&1 | tee frontend.log
    ```

  - Docker 사용 가능 여부는 `docker info`가 정상 응답하는지로 판단한다. 실패하면 위 로컬 Python 대체 경로로 백엔드를 띄운다.
  - 사용자는 창에서 실시간 로그를 보고, 에이전트는 `backend.log`·`frontend.log`를 읽어 추적한다. (두 로그 파일은 `.gitignore`에 둔다.)
- **명령 예시는 Windows PowerShell 기준으로 작성하되, macOS 개발자를 위해 다를 경우 대응 명령을 함께 적는다.** (Bash 도구는 스크립트용으로만.)
- **DB 초기화·시드는 서버 시작이 아니라 `python -m scripts.seed.reset_and_seed`로 실행한다.** 서버 부팅 시 자동 시드를 넣지 않는다.
- **경로 계산은 클라이언트 온디바이스(Dijkstra, `client/lib/domain/dijkstra.dart`)가 담당한다.** 서버는 그래프(nodes·edges)만 제공하며, 최단 경로 로직을 서버로 옮기지 않는다.
- **API 계약(JSON)은 Flutter 클라이언트가 소비하는 형태를 우선으로 유지한다.** 백엔드 응답 스키마를 바꾸면 클라이언트의 모델·파싱도 함께 확인한다.
- **백엔드·클라이언트를 함께 바꿨다면 양쪽 테스트를 모두 돌린다** (`backend/tests`, `client/test`).
- **문서·커밋·PR은 한국어로 작성한다.** 기존 문서 톤을 따른다.

## 코드 검토 원칙 — 위험 기준으로 무게를 다르게

모든 코드를 똑같은 무게로 읽지 않는다. **피해 규모(blast radius)** 를 기준으로 판단한다.

- **낮은 위험 → 동작과 테스트 중심으로 확인.** 문구, 내부 정렬, 이미 검증된 패턴, 쉽게 롤백 가능한 변경 등은 테스트와 동작 결과로 확인하고 넘어간다.
- **높은 위험 → 핵심 코드를 직접 깊게 검토.** 결제, 권한, 인증, 개인정보, 삭제, 마이그레이션 등 되돌리기 어렵거나 피해가 큰 영역은 코드를 직접 정독한다.

## 커밋 규칙

- **논리적으로 관련된 작업 단위로 나누어 커밋한다.** 성격이 다른 변경(예: 기능·문서 정리·파일 이동·삭제)은 한 커밋에 섞지 않고 각각 분리한다.
- **제목은 한 줄**, `feat:`, `fix:`, `chore:`, `docs:`, `refactor:` 등 타입 접두사로 시작한다. 내용은 **한글**로 쓴다.
- 필요하면 제목 다음 줄(빈 줄 뒤)에 **1~2줄 정도 설명**을 덧붙인다. 불필요하면 제목만.
- **`Co-Authored-By` 및 협업자 Claude 태그는 붙이지 않는다.**

## PR 작성 규칙

PR을 만들 때 `.github/PULL_REQUEST_TEMPLATE.md`의 5섹션 형식을 따른다.

- Co-Authored-By 및 협업자 Claude 태그 금지 (PR·커밋 모두)
- 리뷰는 작성자 본인을 제외한 모든 참가자에게 요청
- 각 섹션은 간결하게. 팀원이 직접 설명할 수 있는 2~3줄 정도로 쓴다.
- "남은 위험" 섹션에서는 이번 변경으로 더 이상 참조되지 않는 코드나 노후화된 README.md 등 문서도 함께 찾아 적는다.
