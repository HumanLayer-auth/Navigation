# 개발 요청·SQL 로그

기본 실행에서는 진단 파일을 만들지 않는다. PowerShell에서 환경변수를 켠 뒤 서버를 시작한다.

```powershell
$env:NAV_SQL_ECHO = '1'
$env:NAV_HTTP_CAPTURE = '1'
python -m uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8001 2>&1 | ForEach-Object { $_; $_ | Out-File ..\backend-local.log -Append -Encoding utf8 }
```

macOS/Linux:

```bash
export NAV_SQL_ECHO=1
export NAV_HTTP_CAPTURE=1
python -m uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8001 2>&1 | tee ../backend-local.log
```

- `backend/app/sql/queries.sql`: SQLAlchemy가 DB에 전달한 SQL과 바인딩 파라미터
- `backend/app/args/*.json`: API의 실제 GET/POST 요청 경로·쿼리·JSON 인자와 응답 상태 코드
- `backend-local.log`: 사용자가 창에서 본 Uvicorn 로그와 같은 UTF-8 출력

`args` 로그의 GET 요청은 `query_string`에 쿼리 파라미터가 남고 `json`은 `null`이다. 응답 본문과
헤더는 저장하지 않는다. 필요한 값은 실제 요청 인자(예: 매장명·건물 ID·현재 층)와 상태 코드뿐이다.

`/health`는 Docker healthcheck가 주기적으로 호출하더라도 서버 프로세스당 첫 요청 한 건만 남긴다.
FastAPI 서버가 정상 종료되면 `backend/app/sql/`과 `backend/app/args/`는 자동 삭제된다.

`Authorization`, `token`, `password`, `secret`, `api_key`/`apikey`를 포함하는 헤더·JSON 키·이름 있는
SQL 파라미터는 `***`로 마스킹된다. TMAP처럼 Flutter가 외부 API로 직접 보내는 요청은 백엔드를 거치지
않으므로 이 로그에 나타나지 않는다.
