# Role

DevOps 및 CI/CD 전문가

# Task

제공된 CD 관련 라벨 구성표를 기반으로 GitHub 리포지토리의 라벨을 생성하거나 기존 정보를 업데이트하라.

# Label Data

- name: cd, color: #0e8a16, description: CD 파이프라인 및 배포 관련
- name: docker, color: #2496ed, description: Docker 이미지 및 컨테이너화 관련
- name: e2e-testing, color: #c5def5, description: Playwright 등 E2E 테스트 관련
- name: infrastructure, color: #5319e7, description: 인프라 및 배포 환경 설정 관련

# Execution Logic

1. GitHub CLI(`gh`)를 사용하여 작업을 수행한다.
2. 각 라벨에 대해:
   - 라벨이 리포지토리에 없으면 `gh label create` 명령어로 생성한다.
   - 라벨이 이미 존재하면 `gh label edit` 명령어로 색상과 설명을 업데이트한다.
3. 명령어 실행 중 오류가 발생하더라도 중단하지 않고 다음 라벨로 넘어간다.

# Output

작업이 완료되면 생성된 라벨과 업데이트된 라벨의 목록을 요약하여 보고한다.
