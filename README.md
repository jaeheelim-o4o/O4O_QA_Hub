# PBO QA Hub

QA 업무 자동화 도구 모음입니다.  
사이드바 메뉴로 각 도구를 전환하며 사용할 수 있습니다.

---

## 현재 제공 기능

| 도구 | 설명 |
|------|------|
| 📋 TC 생성기 | PRD/Figma 링크 입력 → TestCase 자동 생성 |
| 📊 Jira 대시보드 생성기 | 에픽 번호 입력 → QA 대시보드 자동 생성 |

---

## 실행 방법

### 1단계 — 폴더 생성 및 start.command 준비

1. 원하는 위치에 폴더를 하나 만듭니다. (예: 바탕화면에 `QA_Hub` 폴더)
2. GitHub에서 `start.command` 파일을 다운로드합니다.
3. 다운로드한 `start.command`를 만든 폴더 안으로 이동합니다.

> `start.command`를 실행한 폴더 안에 모든 파일이 설치되므로,  
> Downloads 폴더가 아닌 **전용 폴더**를 만들어 사용하는 것을 권장합니다.

> **처음 실행 시 "확인되지 않은 개발자" 경고가 뜨는 경우**  
> 파일 우클릭 → [열기] → [열기] 를 선택해 한 번만 허용해주세요.

> **더블클릭해도 반응이 없는 경우**  
> 터미널에서 아래 명령어를 한 번만 실행 후 다시 시도하세요.
> ```bash
> chmod +x ~/Downloads/start.command
> ```

> **위 방법으로도 실행이 안 되는 경우 (보안 경고 반복)**  
> Mac 격리 속성을 제거하는 아래 명령어를 추가로 실행하세요.
> ```bash
> xattr -d com.apple.quarantine ~/Downloads/start.command
> ```
> 파일을 전용 폴더로 이동했다면 경로를 맞게 수정해주세요.  
> 예: `xattr -d com.apple.quarantine ~/Desktop/QA_Hub/start.command`

### 2단계 — 실행

폴더 안의 `start.command` 파일을 더블클릭합니다.

처음 실행 시 자동으로:
- TC 생성기 소스 (`namseok-ko/TestCase_Generator`) 다운로드
- QA Hub 소스 다운로드 및 설치
- 두 서버 동시 실행

이후 실행부터는 최신 버전 여부를 확인 후 바로 시작합니다.

### 3단계 — .env 설정

처음 실행 시 `.env` 파일이 자동 생성되며 텍스트 에디터로 열립니다.  
본인의 Jira 정보를 입력 후 저장하고 엔터를 누르면 실행됩니다.

```
JIRA_EMAIL=your-email@company.com
JIRA_TOKEN=your-jira-api-token
JIRA_BASE_URL=https://musinsa-oneteam.atlassian.net
BUG_PROJECT=OFFSYSM
```

> Jira API 토큰 발급: https://id.atlassian.com/manage-profile/security/api-tokens

> `.env` 파일이 Finder에서 안 보이는 경우 해당 폴더에서 `Cmd + Shift + .` 을 누르면 숨김 파일이 표시됩니다.

---

## 실행 구조

`start.command` 하나로 두 서버가 동시에 실행됩니다.

| 프로그램 | 포트 | 소스 |
|----------|------|------|
| TC 생성기 | localhost:5000 | `namseok-ko/TestCase_Generator` |
| QA Hub | localhost:5001 | `jaeheelim-o4o/O4O_QA_Hub` |

브라우저는 QA Hub(`localhost:5001`)로 자동 열리며,  
사이드바에서 TC 생성기를 선택하면 화면 안에서 바로 사용할 수 있습니다.

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

## 팀원 공유 방법

1. 이 저장소의 `start.command` 파일을 공유합니다.
2. 팀원이 더블클릭하면 모든 설치가 자동으로 진행됩니다.
3. `.env` 파일에 본인의 Jira 토큰만 입력하면 완료입니다.

> `.env` 파일은 Git에 포함되지 않으므로 각자 개별 설정이 필요합니다.

---

## 문제 해결

### 서버 재시작이 필요한 경우

아래 상황에서는 터미널 창에서 `Ctrl+C`로 서버를 종료하고 `start.command`를 다시 실행해야 합니다.

- `.env` 파일을 수정한 경우 (Jira 토큰 변경 등)
- `start.command`를 통해 코드가 업데이트된 경우

---

### 잘못 생성된 대시보드/필터 삭제 방법

Jira에서 직접 삭제할 수 있습니다.

**대시보드 삭제**
1. Jira → 대시보드 목록에서 해당 대시보드 선택
2. 우측 상단 `...` 메뉴 → [대시보드 삭제]

**필터 삭제**
1. Jira → 필터 → 내 필터
2. 삭제할 필터 우측 `...` → [삭제]

> 대시보드를 삭제해도 필터는 남아 있으므로 필터도 따로 삭제해주세요.  
> 필터명은 `[에픽키] 버그 전체` 형식으로 생성됩니다. (예: `[OFFPRD-1007] 버그 전체`)

---

## 향후 추가 예정

- 📝 Test Plan 자동 생성
- 📈 Feature Estimation
