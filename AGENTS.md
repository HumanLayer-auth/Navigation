# AGENTS.md

이 리포지토리의 CI/CD 자동화 작업은 `prompt/` 디렉토리에 작업별 프롬프트로 정의되어 있다.
에이전트는 아래 작업 중 하나를 요청받으면 **해당 프롬프트 파일을 먼저 읽고**, 그 안의
Role / Task / Execution Logic / Constraints를 그대로 따른다.

## 프롬프트 라우팅 표

| 요청 의도 | 읽을 프롬프트 파일 | 요약 |
|---|---|---|
| CI 관련 라벨 생성/업데이트 (`ci`, `testing`, `static-analysis`) | [prompt/label-ci.md](prompt/label-ci.md) | `gh label`로 CI 라벨 일괄 생성/수정 |
| CD 관련 라벨 생성/업데이트 (`cd`, `docker`, `e2e-testing`, `infrastructure`) | [prompt/label-cd.md](prompt/label-cd.md) | `gh label`로 CD 라벨 일괄 생성/수정 |
| GitHub Actions CI/CD 파이프라인 설계 -> `cicd-issues.md` 작성 | [prompt/design-cicd-issues.md](prompt/design-cicd-issues.md) | 아키텍처 분석 후 CI/CD 이슈 명세를 파일로 발행 |
| `cicd-issues.md` -> GitHub 이슈 자동 생성 + Kanban `Todo` 할당 | [prompt/create-issues.md](prompt/create-issues.md) | 이슈 파일 파싱 후 `gh issue create`로 순차 생성 |
| Projects 보드 최우선 이슈를 GitHub Flow로 구현 | [prompt/implement-issue.md](prompt/implement-issue.md) | `Todo` 최상단 이슈를 골라 PR까지 완료 |
| 새 PR 자동 분류(labels / assignee / board status) | [prompt/triage-pr.md](prompt/triage-pr.md) | PR 성격 분석 후 라벨/담당자/보드 Status 기입 |

## 권장 실행 순서

`label-ci` / `label-cd`로 라벨을 준비한 뒤, `design-cicd-issues`로 CI/CD 작업을 쪼개고,
`create-issues`로 이슈를 발행한 다음 `implement-issue`로 하나씩 구현한다.

## PR 자동 분류

PR이 열리면 [.github/workflows/pr-triage.yml](.github/workflows/pr-triage.yml)이 Claude Code 에이전트를 띄워
[prompt/triage-pr.md](prompt/triage-pr.md) 규칙대로 **labels / Assignee / Projects Status**를 기입한다.

최초 1회 설정:

- `CLAUDE_CODE_OAUTH_TOKEN`: Claude Pro/Max 구독 토큰(`claude setup-token` 발급)
- `PROJECT_PAT`: `project` + `repo` 스코프 PAT. 없으면 `GITHUB_TOKEN`으로 동작하지만 Projects 단계가 실패할 수 있다.

## 마일스톤 이슈 초안

마일스톤별로 만들 GitHub 이슈의 초안과 설명은 `issues/` 디렉토리에 기록한다.
각 이슈는 왜 필요한지, 어떤 작업을 포함하는지, 어떤 기준이면 완료인지까지 적는다.

- 작성 규칙과 템플릿은 [issues/issue.md](issues/issue.md)를 따른다.
- 식별자는 `ISSUE-NNN` 형식, 상태는 `Draft / Ready / Created / Done` 중 하나로 기록한다.

## 사용 규칙

- 작업 시작 전 라우팅 표에서 의도에 맞는 파일을 찾아 전문을 읽는다.
- 프롬프트 파일의 지시가 이 문서와 충돌하면 프롬프트 파일을 우선한다.
- 새 자동화 프롬프트를 추가할 때는 `prompt/`에 파일을 만들고 위 표에 한 줄을 추가한다.
- 설명과 커밋 메시지는 한국어, 코드와 식별자는 영어로 작성한다.
