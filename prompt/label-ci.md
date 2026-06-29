# Role

소프트웨어 엔지니어 및 자동화 전문가

# Task

제공된 라벨 구성표를 기반으로 GitHub 리포지토리의 라벨을 생성하거나 기존 정보를 업데이트하라.

# Label Data

- name: ci, color: #0075ca, description: CI 파이프라인 관련
- name: testing, color: #d93f0b, description: 테스트 관련
- name: static-analysis, color: #0e8a16, description: 정적 분석 관련

# Execution Logic

1. GitHub CLI(`gh`)를 사용하여 작업을 수행한다.
2. 각 라벨에 대해:
   - 라벨이 리포지토리에 없으면 `gh label create` 명령어로 생성한다.
   - 라벨이 이미 존재하면 `gh label edit` 명령어로 색상과 설명을 업데이트한다.
3. 명령어 실행 중 오류가 발생하더라도 중단하지 않고 다음 라벨로 넘어간다.

# Output

작업이 완료되면 생성된 라벨과 업데이트된 라벨의 목록을 요약하여 보고하라.
