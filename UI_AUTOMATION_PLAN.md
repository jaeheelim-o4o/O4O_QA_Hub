# O4O QA Hub — 시스템 설계 및 구현 문서

> 작성일: 2026-04-13
> 작성자: O4O QA팀
> 상태: Phase 1 완료 / Phase 2 계획 중

---

## 1. QA Hub 전체 구조

QA Hub는 O4O QA팀의 업무 자동화 통합 플랫폼이다. Flask 기반 웹 서버(포트 5001)를 중심으로 세 개의 기능 영역으로 구성된다.

```
+-------------------------------------------------------------+
|                      QA Hub (port 5001)                     |
|                                                             |
|  +---------------+  +------------------+  +-------------+  |
|  |   TC 생성기    |  |  테스트 수행 Util |  |  UI 테스트  |  |
|  |  (port 5000)  |  |                  |  |             |  |
|  |               |  |  [v] Jira        |  |  [v] Self-  |  |
|  |  Jira 이슈    |  |      대시보드     |  |      POS    |  |
|  |  기반 TC      |  |      생성        |  |  [v] mPOS   |  |
|  |  자동 생성    |  |  [ ] Test Plan   |  |  [v] PDP    |  |
|  |               |  |      생성 (예정) |  |             |  |
|  |               |  |  [ ] Test Report |  |  Playwright |  |
|  |               |  |      생성 (예정) |  |  + pytest   |  |
|  +---------------+  +------------------+  +-------------+  |
+-------------------------------------------------------------+
```

### 1-1. 디렉토리 구조

```
QA_Hub/
├── app.py                          # Flask 메인 서버 (포트 5001)
├── start.command                   # macOS 원클릭 실행 스크립트
├── pytest.ini                      # pytest 실행 설정
├── requirements.txt                # Python 의존성
├── .env                            # 인증 정보 (gitignore)
│
├── tc_generator/                   # TC 생성기 서브 서버 (포트 5000)
│   └── app.py
│
├── tests/                          # UI 자동화 테스트 루트
│   ├── conftest.py                 # 공통 Fixture / Hook
│   ├── session_manager.py          # Okta 세션 갱신 CLI
│   ├── slack_notify.py             # Slack 알림 유틸
│   │
│   ├── self_pos/                   # Self-POS 테스트
│   │   ├── pages/
│   │   │   └── checkout_page.py   # Page Object (결제 플로우)
│   │   └── test_checkout.py
│   │
│   ├── mpos/                       # mPOS 테스트
│   │   └── test_store_sell.py
│   │
│   └── pdp/                        # PDP 테스트
│       ├── test_member.py
│       └── test_nonmember.py
│
├── test_results/                   # 실행 결과 저장
│   ├── allure-results/<run_id>/    # Allure raw 결과
│   ├── allure-report/<run_id>/     # Allure 생성 리포트
│   ├── html/<run_id>/              # pytest-html 리포트 (fallback)
│   ├── traces/                     # Playwright trace (.zip)
│   ├── screenshots/                # 스텝별 스크린샷
│   └── videos/                     # 테스트 녹화 (.webm)
│
└── tests/profiles/                 # Okta 세션 프로필 (gitignore)
    ├── self_pos/
    ├── mpos/
    └── pdp/
```

---

## 2. TC 생성기

별도 Flask 서버(포트 5000)로 실행되며, Jira 이슈 정보를 기반으로 테스트케이스를 자동 생성한다. QA Hub 메인 서버와 별개 프로세스로 동작하며 `start.command`에서 자동 시작된다.

- **레포지토리**: GitHub `namseok-ko/TestCase_Generator`
- **실행 방식**: `start.command` 실행 시 자동 clone/업데이트 후 백그라운드 실행
- **접근 URL**: `http://localhost:5000`

---

## 3. 테스트 수행 Util

### 3-1. Jira 대시보드 생성기

#### 기능 개요

에픽 번호를 입력하면 버그 트래킹용 Jira 대시보드를 자동으로 생성한다. 대시보드 생성에 필요한 필터 6개와 가젯 9개를 API로 자동 구성한다.

#### 시스템 흐름

```
사용자 입력 (에픽 번호)
    │
    ▼
[1] 에픽 정보 조회 (Jira REST API)
    │  GET /rest/api/3/issue/{epic_key}
    │
    ▼
[2] 버그 필터 6개 생성
    │  POST /rest/api/3/filter
    │
    │  생성되는 필터:
    │  ├── [epic] 버그 전체 (전체 상태)
    │  ├── [epic] 버그 오픈 (SUGGESTED)
    │  ├── [epic] 버그 IN PROGRESS
    │  ├── [epic] 버그 IN QA
    │  ├── [epic] 버그 CLOSED (Done)
    │  └── [epic] 버그 심각도순
    │
    ▼
[3] 대시보드 생성
    │  POST /rest/api/3/dashboard
    │
    ▼
[4] 가젯 9개 배치
       POST /rest/api/3/dashboard/{id}/gadget
       PUT  /rest/api/3/dashboard/{id}/gadget/{gid}  (설정)

       배치되는 가젯:
       Col 0: 생성 대비 해결됨 차트 | 버그 오픈 종류(기능/디자인) | 일별 등록 캘린더
       Col 1: 심각도순 취합 | 담당자별 취합 | 오픈 리스트
               IN PROGRESS 리스트 | IN QA 리스트 | CLOSED 리스트
```

#### API

```
POST /api/create-dashboard
Body: { "epic_key": "OFFSYSM-1234" }
```

#### .env 설정

```
JIRA_EMAIL=your-email@musinsa.com
JIRA_TOKEN=your-atlassian-api-token
JIRA_BASE_URL=https://musinsa-oneteam.atlassian.net
BUG_PROJECT=OFFSYSM
```

---

### 3-2. 향후 추가 예정 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| Test Plan 생성 | Jira 이슈 → 테스트 계획서 자동 생성 | 계획 |
| Test Report 생성 | 수행 결과 → Confluence 리포트 자동 게시 | 계획 |

---

## 4. UI 테스트

### 4-1. 테스트 대상 서비스

| 서비스 | URL | 인증 방식 | FE 환경 |
|--------|-----|----------|---------|
| Self-POS | `self-pos.dev.one.musinsa.com` | Okta ID/PW (MFA 없음) | 1개 고정 |
| mPOS | `mpos.dev.one.musinsa.com/store/sell` | Okta ID/PW (MFA 없음) | MPOS / MPOS2 / MPOS3 |
| PDP | `pdp-web.dev.musinsa.com/pdp/goods` | 고객 계정 또는 비회원 | 1개 고정 |

**API 환경 (서비스 공통)**: `mpos` / `mpos1` ~ `mpos5`

### 4-2. 기술 스택

| 역할 | 기술 |
|------|------|
| 테스트 프레임워크 | pytest + pytest-playwright |
| 브라우저 자동화 | Playwright (Python, Chromium) |
| 실행 추적 | Playwright Trace (.zip) |
| 테스트 리포트 | Allure (CLI 우선, allure-combine fallback) |
| HTML 리포트 | pytest-html (fallback) |
| 알림 | Slack Block Kit (Webhook) |
| 서버 | Flask (QA Hub 내장) |

### 4-3. Okta 인증 전략

```
[최초 실행 또는 세션 만료 시]
QA Hub "세션 갱신" 버튼 클릭
  → Python session_manager.py 실행
  → Playwright headed 브라우저 실행
  → Okta 로그인 페이지 접속
  → ID / PW 자동 입력 (.env 로드)
  → Okta 승인 후 앱 진입 확인
  → 브라우저 프로필 저장 (tests/profiles/<service>/)
  → 이후 실행 시 프로필 재사용 → Okta 스킵

[테스트 실행 시 자동 로그인 흐름]
headless 모드 시도
  → Okta 감지 시 ID/PW 자동 입력 (_auto_login)
  → 실패 시 headed 모드로 폴백 (_get_authenticated_context)
  → 앱 URL 도달 확인 (_wait_for_app)
  → 로그인 성공 시 테스트 진행
```

**핵심 결정사항**
- Okta Device Bound Sessions → storage_state 방식 불가 → **Persistent Context(브라우저 프로필)** 방식 채택
- Single Session 충돌 → 각 테스트 전 앱 도메인 쿠키만 삭제, Okta SSO 쿠키는 유지
- `page.reload()` 대신 `page.goto()` 사용 (SPA ERR_ABORTED 방지)

### 4-4. localStorage 환경 주입 방식

```python
# add_init_script: JS 실행 전에 주입 → 앱 초기화 시 값이 이미 설정됨
page.add_init_script(f"""
    if (location.hostname === '{target_domain}') {{
        localStorage.setItem('apiType', '{api_type}');
        localStorage.setItem('local-pos-id', '{POS_ID}');
    }}
""")

# Okta 경유 후 페이지 재진입 시 값이 초기화될 수 있음 → 앱 도달 후 재설정
page.evaluate(f"""
    localStorage.setItem('apiType', '{api_type}');
    localStorage.setItem('local-pos-id', '{POS_ID}');
""")
```

| localStorage 키 | 설명 | 대상 서비스 |
|----------------|------|-----------|
| `apiType` | API 서버 환경 (mpos~mpos5) | 전체 |
| `local-pos-id` | POS 단말 ID (64-1021) | Self-POS, mPOS |
| `feType` | FE 환경 (MPOS/MPOS2/MPOS3) | mPOS |

### 4-5. 시스템 흐름 (QA Hub → 테스트 실행 → 리포트)

```
QA Hub UI (브라우저)
    │
    │  POST /api/ui-test/run
    │  { service, api_type, fe_type, tests, headless }
    │
    ▼
Flask app.py
    │
    ├── run_id 생성 (UUID 8자리)
    ├── allure-results/<run_id>/ 디렉토리 생성
    ├── html/<run_id>/report.html 경로 설정
    └── 백그라운드 스레드 실행 (_run)
            │
            ▼
        pytest 실행
            │  python -m pytest tests/<service>/
            │  --alluredir=test_results/allure-results/<run_id>/
            │  --html=test_results/html/<run_id>/report.html
            │
            ▼
        conftest.py — Fixture 실행
            │
            ├── <service>_context (module scope)
            │     └── Playwright 브라우저 컨텍스트 생성
            │     └── Okta 인증 (_get_authenticated_context)
            │
            └── <service>_page (function scope, 테스트마다)
                  ├── 앱 도달 대기 (_wait_for_app)
                  ├── localStorage 주입
                  ├── Trace 시작 (context.tracing.start)
                  ├── [yield] ← 테스트 실행
                  ├── Trace 저장 (per-test .zip)
                  └── 비디오 저장 (.webm)
            │
            ▼
        pytest_runtest_makereport hook (trylast=True)
            ├── Allure 비디오 첨부 (.webm)
            └── Allure Trace 링크 첨부
                  (https://trace.playwright.dev/?trace=...)
            │
            ▼
        Allure 리포트 생성
            ├── allure CLI (설치된 경우) → allure-report/<run_id>/index.html
            └── allure-combine (Python fallback) → allure-report/<run_id>/complete.html
            │
            ▼
        Slack 알림 전송
            └── send_slack_notification()
                  ├── 환경 정보 (API, FE)
                  ├── 결과 요약 (통과/실패/전체)
                  ├── TC별 상세 결과
                  └── Allure 리포트 링크 버튼

    │
    │  GET /api/ui-test/status/<run_id>
    ▼
QA Hub UI — 완료 표시 + 리포트 보기 버튼
```

### 4-6. Flask API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/ui-test/run` | 테스트 실행 (비동기) |
| `GET` | `/api/ui-test/status/<run_id>` | 실행 상태 및 결과 조회 |
| `POST` | `/api/ui-test/session/refresh` | Okta 세션 갱신 브라우저 실행 |
| `GET` | `/api/ui-test/report/<run_id>` | Allure/HTML 리포트 서빙 |
| `GET` | `/api/ui-test/allure/<run_id>/<path>` | Allure 정적 파일 서빙 |
| `GET` | `/api/ui-test/trace-file/<filename>` | Trace 파일 서빙 (CORS 포함) |
| `GET` | `/api/ui-test/trace/<run_id>` | Trace .zip 다운로드 |

### 4-7. Allure 리포트 구성

| 항목 | 내용 |
|------|------|
| 스텝별 스크린샷 | `page.take_screenshot(name)` 호출 시 즉시 Allure Attachments에 첨부 |
| 테스트 녹화 | teardown 후 `.webm` 파일을 Attachments 탭에 첨부 |
| Playwright Trace | teardown 후 `🔍 Playwright Trace 열기` 버튼 생성 |
| Trace 뷰어 | `https://trace.playwright.dev/?trace=http://localhost:5001/api/ui-test/trace-file/<filename>` |

**리포트 생성 우선순위**
```
allure CLI (brew 설치)
    → allure generate allure-results/ -o allure-report/ → index.html
    ↓ 실패 시
allure-combine (Python 패키지)
    → complete.html (단일 파일, 서버 불필요)
    ↓ 실패 시
pytest-html fallback
    → report.html
```

### 4-8. Slack 알림

```
✅ [O4O QA] Self-POS 회귀 테스트 완료
──────────────────────────────────────
환경:  API: mpos  |  (FE 고정)
결과:  ✅ 4건 통과  /  ❌ 0건 실패  /  전체 4건
완료:  2026-04-13 15:42
실행자: jaeheelim
──────────────────────────────────────
테스트케이스 상세
✅  test_checkout::test_nonmember_normal_payment
──────────────────────────────────────
[ 📄 HTML 리포트 보기 ]
```

---

## 5. 테스트 코드 구조 (실제 구현)

### 5-1. conftest.py — 공통 Fixture 설계 원칙

```
scope="module"  → <service>_context
    Playwright 브라우저 컨텍스트 1개를 모듈 전체에서 공유
    이유: 테스트마다 새 컨텍스트 생성 시 Okta Single Session 충돌 발생

scope="function" → <service>_page
    테스트마다 새 page 생성 + localStorage 재주입
    Trace / 비디오 per-test로 분리 저장
```

### 5-2. Page Object 패턴 (Self-POS 예시)

각 서비스의 화면 조작 로직을 Page Object 클래스로 분리한다. 각 메서드는 `@allure.step`으로 데코레이트되어 Allure 리포트에 단계별 결과가 표시된다.

```python
# tests/self_pos/pages/checkout_page.py

class CheckoutPage:
    def __init__(self, page: Page):
        self.page = page

    @allure.step("셀프계산 시작하기 화면에서 '비회원' 선택")
    def select_nonmember(self):
        nonmember_btn = self.page.get_by_role("button", name="비회원")
        nonmember_btn.wait_for(state="visible", timeout=10000)
        nonmember_btn.click()
        self.page.wait_for_selector("text=바코드를 스캔해주세요", timeout=10000)

    @allure.step("바코드 스캔 화면에서 테스트 바코드 선택")
    def scan_test_barcode(self, barcode: str = "위탁-2 - 3422886"):
        barcode_item = self.page.get_by_text(barcode, exact=True)
        barcode_item.wait_for(state="visible", timeout=10000)
        barcode_item.click()
        self.page.wait_for_selector("button:has-text('결제하기')", timeout=10000)

    @allure.step("'택스리펀을 신청하시겠어요?' 레이어에서 건너뛰기 선택")
    def skip_tax_refund(self):
        self.page.wait_for_selector("text=택스리펀", timeout=10000)
        # 같은 텍스트 버튼이 복수 존재하는 경우 data-testid로 정확히 지정
        skip_btn = self.page.get_by_test_id("taxfree-dialog-cancel")
        skip_btn.wait_for(state="visible", timeout=5000)
        skip_btn.click()

    # ... (Step 12개 전체 구현 완료)
```

### 5-3. 테스트 케이스 작성 패턴

```python
# tests/self_pos/test_checkout.py

@allure.feature("Self-POS")
@allure.story("정상 결제")
class TestSelfPosCheckout:

    @allure.title("[TC-CHECKOUT-001] 비회원 정상 결제 — 위탁 상품 바코드 스캔 후 신용카드 일시불 결제")
    def test_nonmember_normal_payment(self, self_pos_page):
        page = self_pos_page
        checkout = CheckoutPage(page)

        # 스텝 실행 + 스크린샷 (Allure Attachments에 자동 첨부)
        page.take_screenshot("initial")

        checkout.select_nonmember()
        page.take_screenshot("nonmember_selected")

        checkout.scan_test_barcode("위탁-2 - 3422886")
        page.take_screenshot("barcode_scanned")

        # 조건부 레이어 — 미노출 시 스킵
        _dismiss_if_visible(page, checkout.confirm_security_tag_removal, "보안택")

        checkout.skip_tax_refund()
        checkout.select_credit_card()
        checkout.select_lump_sum_payment()

        # 최종 검증
        checkout.verify_receipt_screen()
        checkout.go_to_home()
        page.take_screenshot("back_to_home")
```

### 5-4. 환경 파라미터화 (mPOS 예시)

```python
# tests/mpos/test_store_sell.py

# API + FE 환경 조합을 파라미터로 실행
@pytest.mark.parametrize(
    "mpos_page",
    [("mpos1", "MPOS"), ("mpos2", "MPOS2"), ("mpos3", "MPOS3")],
    indirect=True
)
def test_env_combination(self, mpos_page):
    page     = mpos_page
    api_type = page.evaluate("localStorage.getItem('apiType')")
    fe_type  = page.evaluate("localStorage.getItem('feType')")
    assert api_type is not None
    assert "mpos" in page.url.lower()
```

---

## 6. .env 설정

```
# Jira
JIRA_EMAIL=your-email@musinsa.com
JIRA_TOKEN=your-atlassian-api-token
JIRA_BASE_URL=https://musinsa-oneteam.atlassian.net
BUG_PROJECT=OFFSYSM

# Okta (Self-POS / mPOS 자동 로그인)
OKTA_EMAIL=your-email@musinsa.com
OKTA_PASSWORD=your-password

# PDP 고객 계정 (선택)
CUSTOMER_EMAIL=test@example.com
CUSTOMER_PASSWORD=test-password

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# UI 테스트 실행 옵션
UI_TEST_HEADLESS=true          # true: headless 우선 (실패 시 headed 폴백)
UI_TEST_API_TYPE=mpos           # 기본 API 환경
UI_TEST_FE_TYPE=MPOS            # 기본 FE 환경 (mPOS)

# QA Hub 서버 주소 (Trace URL 생성 시 사용)
QA_HUB_URL=http://localhost:5001
```

---

## 7. start.command 동작

macOS에서 더블클릭으로 실행하면 다음 순서로 동작한다.

```
1. .env 파일 존재 확인 → 없으면 .env.example에서 복사 후 편집기 오픈

2. Python 3.9+ 감지

3. [TC 생성기]
   - GitHub에서 clone 또는 최신 버전 pull
   - venv 생성 및 의존성 설치
   - 포트 5000으로 백그라운드 실행

4. [QA Hub]
   - GitHub에서 최신 버전 pull (.env 보존)
   - venv 생성 및 의존성 설치
   - [Allure CLI] brew install allure 시도
       ✅ 성공: allure CLI로 리포트 생성
       ⚠ 실패: Python allure-combine으로 자동 대체
   - 포트 5001로 포그라운드 실행

5. http://localhost:5001 브라우저 자동 오픈
```

---

## 8. 구현 현황 및 로드맵

### 완료된 구현 (Phase 1)

| 항목 | 내용 |
|------|------|
| 인프라 | Playwright + pytest 환경, venv, start.command (Allure 자동 설치) |
| 인증 | Okta Persistent Context 방식, 자동 로그인(_auto_login), headed/headless 폴백 |
| Fixture | self_pos / mpos / pdp context + page fixture (per-test trace) |
| 테스트 | Self-POS 결제 TC 1개 완성 (12 Step), mPOS 환경 검증 TC 2개 |
| 리포트 | Allure (CLI/combine 자동 선택), pytest-html fallback |
| 리포트 첨부 | 스텝별 스크린샷, 테스트 녹화(.webm), Playwright Trace 뷰어 링크 |
| QA Hub 연동 | 실행 버튼, 상태 폴링, 리포트 조회 API |
| Slack 알림 | Block Kit, TC별 상세, 리포트 링크 버튼 |
| Jira 대시보드 | 필터 6개 + 가젯 9개 자동 생성 |

---

### Phase 2 — 리그레션 테스트 확장 + 오류 자동 처리

**목표**: 서비스 전체 리그레션 케이스 커버 + 오류 발생 시 Jira 티켓 자동 등록

#### 2-1. 리그레션 테스트 케이스 확장

| 서비스 | 추가할 TC |
|--------|-----------|
| Self-POS | 회원 결제, 할인 쿠폰 적용, 환불 플로우, 오류 케이스 |
| mPOS | 판매 플로우, FE 환경별 동작 검증 |
| PDP | 회원 로그인 후 구매, 비회원 구매, 상품 정보 렌더링 |

#### 2-2. 오류 발생 시 자동 처리 흐름

```
테스트 실행
    |
    +-- [PASS] --> Slack 성공 알림 (기존)
    |
    +-- [FAIL]
            |
            v
        실패 정보 수집
          - 테스트명 / 실패 Step
          - 에러 메시지 + 스택 트레이스
          - 실패 시점 스크린샷
          - Playwright Trace 경로
            |
            v
        Jira 버그 티켓 자동 등록
          - 프로젝트 : BUG_PROJECT (OFFSYSM)
          - 이슈 타입: Bug
          - 제목     : [자동] {서비스} - {테스트명} 실패
          - 설명     : 실패 Step, 에러 메시지, 환경 정보
          - 첨부     : 스크린샷, Trace 링크
          - 우선순위 : Critical (기본)
            |
            v
        Slack 실패 알림
          - 기존 알림 + [ Jira 티켓 보기 ] 버튼 추가
```

#### 2-3. 구현 포인트

- `pytest_runtest_makereport` hook에서 `report.failed` 시 Jira REST API 호출
- 동일 TC 재실패 시 중복 티켓 방지 (기존 티켓 검색 후 댓글 추가)
- 티켓 자동 등록 on/off 환경변수 (`JIRA_AUTO_TICKET=true`)

---

### Phase 3 — AI 기반 UI 테스트 자동 생성

**목표**: `testcase.md` + 개발팀 GitHub 레포 + Figma 파일을 입력하면 UI 테스트 코드를 자동 생성

#### 3-1. 전체 흐름

```
[ 입력 소스 3가지 ]

  testcase.md          GitHub 레포              Figma 파일
  - TC 목록            - 컴포넌트 구조          - 화면 레이아웃
  - 스텝 설명          - API 엔드포인트         - 버튼/텍스트 레이블 정확값
  - 검증 조건          - 데이터 모델

                              |
                              v

  Claude AI (claude-sonnet-4-6) + MCP 도구
    - GitHub MCP     : 코드 구조 분석
    - Figma MCP      : 컴포넌트 셀렉터, 실제값 추출
    - Playwright MCP : 브라우저 조작 검증

                              |
                              v

  테스트 코드 자동 생성
    - tests/<service>/test_<feature>.py
    - tests/<service>/pages/<feature>_page.py
    - @allure.step 데코레이터 포함
    - Page Object 패턴 준수
    - 기존 conftest fixture 재사용
```

#### 3-2. 각 입력 소스의 역할

| 소스 | MCP / 도구 | 추출 정보 |
|------|-----------|----------|
| `testcase.md` | 직접 파싱 | TC 번호, 스텝 순서, 검증 조건 |
| GitHub 레포 | GitHub MCP | 컴포넌트명, API 경로, data-testid 속성, 이벤트 핸들러 |
| Figma 파일 | Figma MCP | 버튼 레이블 정확값, 화면 구조, 레이어명 |

#### 3-3. testcase.md 형식 (입력 규격)

```markdown
## TC-CHECKOUT-002 회원 정상 결제

**서비스**: Self-POS
**전제조건**: 무신사 회원 계정으로 로그인

### 스텝
1. 셀프계산 시작하기 화면에서 '무신사 회원' 선택
2. 회원 바코드 스캔 또는 전화번호 입력
3. 상품 바코드 스캔 (테스트 상품)
4. '결제하기' 버튼 클릭
5. 회원 할인 쿠폰 자동 적용 확인
6. 신용카드 결제 선택 → 일시불
7. '영수증을 챙겨주세요' 화면 노출 확인

### 검증 조건
- 회원 할인이 적용된 결제 금액 표시
- 영수증 화면에 회원명 표시
```

#### 3-4. 생성되는 코드 예시

```python
# 자동 생성 결과: tests/self_pos/test_member_checkout.py

@allure.feature("Self-POS")
@allure.story("회원 결제")
class TestSelfPosMemberCheckout:

    @allure.title("[TC-CHECKOUT-002] 회원 정상 결제")
    def test_member_normal_payment(self, self_pos_page):
        page = self_pos_page
        checkout = MemberCheckoutPage(page)  # 자동 생성된 Page Object

        page.take_screenshot("initial")
        checkout.select_member()
        page.take_screenshot("member_selected")
        # ... (testcase.md 스텝 기반 자동 생성)
        checkout.verify_member_discount_applied()
        checkout.verify_receipt_shows_member_name()
```

#### 3-5. QA Hub UI 연동 계획

```
[ AI 테스트 생성 ] 탭
┌─────────────────────────────────────┐
│  서비스 선택: [ Self-POS ▼ ]        │
│                                     │
│  testcase.md 업로드: [ 파일 선택 ]  │
│  GitHub 레포 URL: [ 입력 ]          │
│  Figma 파일 URL: [ 입력 ]           │
│                                     │
│  [ 🤖 테스트 코드 자동 생성 ]       │
│                                     │
│  생성 결과 미리보기                  │
│  ┌───────────────────────────────┐  │
│  │ test_member_checkout.py       │  │
│  │ pages/member_checkout_page.py │  │
│  └───────────────────────────────┘  │
│  [ 저장 및 적용 ]                   │
└─────────────────────────────────────┘
```
