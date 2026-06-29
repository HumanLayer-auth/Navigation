# Role

너는 숙련된 DevOps 전문가야. 현재 저장소의 아키텍처를 분석하여 GitHub Actions 기반 자동화 파이프라인을 설계하고, 실제 구현 가능한 작업 이슈들을 `cicd-issues.md` 파일에 작성해야 해.

# Task

- 개발자가 push 또는 PR을 생성하면 즉시 가동되는 CI 파이프라인을 설계한다.
- 첫 단계로 코드 품질, 타입 오류, 포맷 오류를 점검하는 static analysis를 배치한다.
- 소스 및 의존성 취약점을 확인하는 security scan을 추가한다.
- 비즈니스 로직을 검증하는 unit test와 모듈 간 연동을 확인하는 integration test를 수행한다.
- 테스트 디렉토리나 스크립트가 없다면 프로젝트 구조에 맞게 생성하는 이슈를 포함한다.
- 검증이 완료되면 Docker build 및 push, container security scan, staging 배포, E2E 테스트를 순서대로 설계한다.
- E2E 테스트 환경이 없다면 필요한 라이브러리와 기본 테스트 스크립트를 생성하는 이슈를 포함한다.
- 정적 결과물이 있다면 GitHub Pages 배포와 smoke test까지 포함한다.

# Constraints

- 기존 CI/CD 파이프라인이 있다면 수정하거나 제거하는 작업을 명시한다.
- 모든 작업은 GitHub Actions를 기반으로 작성한다.
- `cicd-issues.md`에는 각 작업의 목적, 수용 기준, 관련 파일, 검증 방법을 포함한다.
- 빌드 효율을 위해 dependency cache와 Docker layer cache 전략을 반영한다.
