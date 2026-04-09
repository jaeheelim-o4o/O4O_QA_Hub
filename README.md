# PBO QA Hub

QA 업무 자동화 도구 모음입니다.  
사이드바 메뉴로 각 도구를 전환하며 사용할 수 있습니다.

---

## 현재 제공 기능

| 도구 | 설명 |
|------|------|
| 📊 Jira 대시보드 생성기 | 에픽 번호 입력 → QA 대시보드 자동 생성 |
| 📋 TC 생성기 | 별도 실행 후 연동 (localhost:5000) |

---

## 실행 방법

### 1단계 — .env 설정

처음 실행 시 `.env.example`을 참고해서 `.env` 파일에 본인의 Jira 정보를 입력합니다.

```
JIRA_EMAIL=your-email@company.com
JIRA_TOKEN=your-jira-api-token
JIRA_BASE_URL=https://musinsa-oneteam.atlassian.net
BUG_PROJECT=OFFSYSM
```

> Jira API 토큰 발급: https://id.atlassian.com/manage-profile/security/api-tokens

> `.env` 파일이 Finder에서 안 보이는 경우 해당 폴더에서 `Cmd + Shift + .` 을 누르면 숨김 파일이 표시됩니다.

### 2단계 — 실행

`start.command` 파일을 더블클릭합니다.  
브라우저가 자동으로 열리며 `http://localhost:5001` 에서 실행됩니다.

> **처음 실행 시 "확인되지 않은 개발자" 경고가 뜨는 경우**  
> 파일 우클릭 → [열기] → [열기] 를 선택해 한 번만 허용해주세요.

> **더블클릭해도 반응이 없는 경우**  
> 터미널에서 아래 명령어를 한 번만 실행 후 다시 시도하세요.
> ```bash
> chmod +x ~/QA_Hub/start.command
> ```

---

## Jira 대시보드 생성기

에픽 티켓 번호를 입력하면 아래 구성으로 QA 대시보드를 자동 생성합니다.

### 생성되는 필터 (6개)

| 필터명 | 내용 |
|--------|------|
| 버그 전체 | 전체 상태 버그 |
| 버그 오픈 | SUGGESTED 상태 |
| 버그 IN PROGRESS | In Progress / In Developer Test / In Code Review |
| 버그 IN QA | in QA / Ready To Test |
| 버그 CLOSED | Done 상태 |
| 버그 심각도순 | 심각도 + 생성일 기준 정렬 |

### 생성되는 가젯 (9개)

| 위치 | 가젯 |
|------|------|
| 왼쪽 | 생성 대비 해결됨 차트 |
| 왼쪽 | 버그 오픈 종류 (기능/디자인) |
| 왼쪽 | 일별 버그 등록 추이 캘린더 |
| 오른쪽 | 심각도순 버그 취합 |
| 오른쪽 | 담당자별 버그 취합 |
| 오른쪽 | 버그 오픈 리스트 |
| 오른쪽 | 버그 IN PROGRESS |
| 오른쪽 | 버그 IN QA |
| 오른쪽 | 버그 CLOSED |

---

## TC 생성기 연동

TC 생성기는 별도 프로그램(`TestCase_Generator-main`)으로 실행됩니다.  
QA Hub에서 **TC 생성기** 메뉴를 클릭하면 `http://localhost:5000` 이 새 탭으로 열립니다.

두 프로그램을 함께 사용하려면 각각의 `start.command`를 실행해주세요.

| 프로그램 | 포트 |
|----------|------|
| TC 생성기 (`TestCase_Generator-main`) | localhost:5000 |
| QA Hub (`QA_Hub`) | localhost:5001 |

---

## 팀원 공유 방법

1. `QA_Hub` 폴더를 공유합니다. (`.env` 파일은 제외)
2. 팀원은 `.env.example`을 복사해서 `.env`로 저장 후 본인 Jira 토큰 입력
3. `start.command` 더블클릭으로 실행

---

## 향후 추가 예정

- 📝 Test Plan 자동 생성
- 📈 Feature Estimation
