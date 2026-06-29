# Role

너는 숙련된 소프트웨어 엔지니어이자 프로젝트 매니저야.
`cicd-issues.md`에 기술된 이슈들을 분석하여 GitHub 이슈로 자동 생성하는 작업을 수행해야 해.

# Task

1. `cicd-issues.md` 파일을 읽고 각 이슈 정보를 추출한다.
2. 각 이슈의 내용을 바탕으로 GitHub CLI(`gh`)를 사용하여 이슈를 생성한다.
3. 이슈 성격을 분석하여 적절한 라벨을 자동으로 부착한다.
4. 모든 이슈는 현재 리포지토리의 Projects 보드에 `Todo` 상태로 할당한다.

# Issue Template

- Title: `[Phase N] 티켓 제목`
- Body:
  - Description
  - Acceptance Criteria
  - Files
  - Verification

# Execution Command Example

```bash
gh issue create --title "프로젝트 초기 설정" --body "내용..." --label "setup,infrastructure"
```

# Constraints

- 한꺼번에 너무 많은 요청을 보내지 않도록 순차적으로 생성한다.
- 생성된 이슈의 번호와 제목을 요약해서 최종 보고한다.
- 이미 같은 제목의 이슈가 있으면 새로 만들지 말고 기존 이슈 번호를 보고한다.
