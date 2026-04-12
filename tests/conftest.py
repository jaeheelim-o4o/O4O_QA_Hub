"""
QA Hub — UI 자동화 공통 Fixtures
persistent context 방식으로 브라우저 프로필을 재사용해 Okta Device bound sessions 문제 해결
"""
import os
import re
import base64
import pytest
import allure
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

# ── 경로 상수 ────────────────────────────────────────────────
ROOT_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_DIR    = os.path.join(ROOT_DIR, "tests", "profiles")
TRACES_DIR      = os.path.join(ROOT_DIR, "test_results", "traces")
SCREENSHOTS_DIR = os.path.join(ROOT_DIR, "test_results", "screenshots")

# 브라우저 프로필 경로 (로그인 상태 영구 저장)
PROFILE_DIRS = {
    "self_pos": os.path.join(PROFILES_DIR, "self_pos"),
    "mpos":     os.path.join(PROFILES_DIR, "mpos"),
    "pdp":      os.path.join(PROFILES_DIR, "pdp"),
}

URLS = {
    "self_pos": "https://self-pos.dev.one.musinsa.com",
    "mpos":     "https://mpos.dev.one.musinsa.com/store/sell",
    "pdp":      "https://pdp-web.dev.musinsa.com/pdp/goods",
}

POS_ID = "64-1021"


# ── 유틸 ────────────────────────────────────────────────────
def profile_exists(service: str) -> bool:
    """프로필 디렉토리가 존재하고 비어있지 않은지 확인"""
    path = PROFILE_DIRS[service]
    return os.path.exists(path) and bool(os.listdir(path))


def _is_okta_page(page) -> bool:
    return "sso.ops.musinsa.com" in page.url or "okta.com" in page.url


def _is_app_page(page, domain: str) -> bool:
    return domain in page.url and not _is_okta_page(page)


def _dismiss_auth_failed_popup(page) -> bool:
    """
    앱의 '인증에 실패했습니다' 팝업 감지 시 확인 버튼 클릭.
    - True 반환: 팝업이 있었음 (확인 클릭 → Okta 재리다이렉트 가능)
    - False 반환: 팝업 없음 (정상)
    setup 단계에서는 dismiss 후 재시도 루프로 넘기고,
    최종적으로 앱 URL에 도달 실패 시에만 FAIL 처리한다.
    """
    try:
        count = page.locator("text=인증에 실패했습니다").count()
    except Exception:
        return False  # 페이지 상태 이상 → 무시

    if count > 0:
        print(f"  [팝업] '인증에 실패했습니다' 감지 → 확인 클릭 후 재시도")
        try:
            page.click("button:has-text('확인')", timeout=2000)
            # 클릭 후 페이지 이동(Okta 리다이렉트 등) 완료까지 대기
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        return True
    return False


def _auto_login(page, target_domain: str):
    """
    Okta 로그인 페이지에서 ID/PW 자동 입력 (MFA 없는 서비스용).
    Self-POS / mPOS는 PW 단일 인증이므로 완전 자동화 가능.
    """
    email    = os.environ.get("OKTA_EMAIL", "")
    password = os.environ.get("OKTA_PASSWORD", "")

    print(f"\n  [자동 로그인] Okta 로그인 화면 감지 → 자동 입력 시작")

    # ID 입력 (표준 로그인 플로우)
    # 없으면 "비밀번호 확인" 재인증 화면 (Okta가 이미 계정을 인식한 경우) → 스킵
    try:
        page.wait_for_selector("input[name='identifier'], input[type='email']", timeout=5000)
        page.fill("input[name='identifier'], input[type='email']", email)
        page.wait_for_timeout(300)
        next_btn = page.query_selector(
            "input[value='Next'], button:has-text('Next'), "
            "button:has-text('다음'), input[type='submit']"
        )
        if next_btn:
            next_btn.click()
        else:
            page.keyboard.press("Enter")
        print(f"  [자동 로그인] ID 입력 완료")
    except Exception:
        print(f"  [자동 로그인] ID 입력창 없음 → 비밀번호 확인 플로우(재인증)")

    try:
        page.wait_for_selector("input[type='password']", timeout=10000)
        page.fill("input[type='password']", password)
        page.wait_for_timeout(300)
        submit_btn = page.query_selector(
            "input[value='Verify'], input[value='Sign In'], "
            "button:has-text('Verify'), button:has-text('Sign In'), "
            "button[type='submit']"
        )
        if submit_btn:
            submit_btn.click()
        else:
            page.keyboard.press("Enter")
    except Exception as e:
        raise RuntimeError(f"PW 입력 실패: {e}")

    # 콜백(login/callback)을 거쳐 실제 앱 메인으로 돌아올 때까지 대기
    # ※ url.split("?")[0] 로 쿼리 파라미터(redirect_uri 포함) 제거 후 비교
    page.wait_for_url(
        lambda url: url.split("?")[0].startswith(f"https://{target_domain}"),
        timeout=60000,
    )
    # 앱이 세션 오류 팝업("인증에 실패했습니다") 노출 후 Okta로 재리다이렉트할 수 있음 → 팝업 dismiss
    try:
        page.wait_for_selector("button:has-text('확인'), button:has-text('OK')", timeout=5000)
        page.click("button:has-text('확인'), button:has-text('OK')")
        print(f"  [자동 로그인] 세션 오류 팝업 닫기 완료")
    except Exception:
        pass
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    print(f"  [자동 로그인] 완료 ✅  (최종 URL: {page.url})")


def _attach_screenshot_helper(page, ts_dir: str, shot_paths: list):
    step_counter = {"n": 0}

    def screenshot(name: str):
        step_counter["n"] += 1
        path = os.path.join(ts_dir, f"{step_counter['n']:02d}_{name}.png")
        page.screenshot(path=path, full_page=True)
        shot_paths.append(path)
        # Allure 스텝별 스크린샷 첨부
        try:
            allure.attach.file(
                path,
                name=f"{step_counter['n']:02d}. {name}",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:
            pass
        return path

    page.take_screenshot = screenshot


def _goto_with_env(page, url: str, api_type: str, fe_type: str = None):
    """
    add_init_script으로 localStorage를 앱 JS보다 먼저 주입한다.
    이렇게 하면 auth 체크 전에 값이 설정되어 리다이렉트 없이 진입 가능.
    """
    script = f"localStorage.setItem('apiType', '{api_type}');"
    if fe_type:
        script += f"localStorage.setItem('feType', '{fe_type}');"
    script += f"localStorage.setItem('local-pos-id', '{POS_ID}');"
    page.add_init_script(script)
    page.goto(url, wait_until="networkidle", timeout=30000)


# ── Okta 세션 갱신 (persistent context 방식) ─────────────────
def refresh_okta_session(service: str):
    """
    persistent context로 Okta 로그인 후 브라우저 프로필에 세션을 저장한다.
    이후 테스트도 같은 프로필을 사용해 Okta Device bound sessions 통과.
    """
    email    = os.environ.get("OKTA_EMAIL", "")
    password = os.environ.get("OKTA_PASSWORD", "")
    url      = URLS[service]
    profile  = PROFILE_DIRS[service]
    target_domain = url.split("//")[1].split("/")[0]

    if not email or not password:
        raise ValueError(".env에 OKTA_EMAIL과 OKTA_PASSWORD를 설정해주세요.")

    os.makedirs(profile, exist_ok=True)
    print(f"\n[세션 갱신] {service} — 브라우저가 열립니다.")
    print(f"  → 로그인이 필요하면 수동으로 진행해주세요. 최대 120초 대기합니다.")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=False,
        )
        page = context.new_page()
        page.goto(url)

        # ID 입력
        try:
            page.wait_for_selector("input[name='identifier'], input[type='email']", timeout=8000)
            page.fill("input[name='identifier'], input[type='email']", email)
            page.wait_for_timeout(500)
            # Enter 키 또는 Next 버튼
            next_btn = page.query_selector(
                "input[value='Next'], button:has-text('Next'), button:has-text('다음'), "
                "input[type='submit']"
            )
            if next_btn:
                next_btn.click()
            else:
                page.keyboard.press("Enter")
            print("  → ID 입력 완료")
        except Exception:
            print("  → ID 입력 화면 없음 (자동 로그인 진행 중)")

        # PW 입력 (Self-POS / mPOS는 MFA 없이 PW만 필요)
        try:
            page.wait_for_selector("input[type='password']", timeout=10000)
            page.fill("input[type='password']", password)
            page.wait_for_timeout(500)
            submit_btn = page.query_selector(
                "input[value='Verify'], input[value='Sign In'], "
                "button:has-text('Verify'), button:has-text('Sign In'), "
                "button[type='submit']"
            )
            if submit_btn:
                submit_btn.click()
            else:
                page.keyboard.press("Enter")
            print("  → PW 입력 완료")
        except Exception:
            print("  → PW 입력 화면 없음 (Okta 푸시 인증 또는 자동 로그인 진행 중)")
            print("  → 폰에서 Okta 승인이 필요하면 눌러주세요.")

        print(f"  → 서비스 페이지 로딩 대기 중...")
        try:
            page.wait_for_url(f"**{target_domain}**", timeout=120000)
        except Exception:
            input("  → 브라우저에서 로그인을 완료한 후 엔터를 누르세요...")

        # 앱이 완전히 초기화되고 auth 토큰을 localStorage에 저장할 때까지 대기
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)

        context.close()
        print(f"  ✅ 프로필 저장 완료: {profile}")


# ── headless/headed 자동 전환 컨텍스트 ──────────────────────

def _get_authenticated_context(p, service: str, record_video_dir: str = None):
    """
    UI_TEST_HEADLESS=true  → headless에서 Okta ID/PW 로그인 시도
                             성공 시 headless 유지, 실패(Device Trust 등) 시 headed 폴백
    UI_TEST_HEADLESS=false → headed 모드로 바로 실행 (실패 직접 확인용)
    record_video_dir       → 지정 시 해당 경로에 비디오 녹화
    반환: (context, auth_page)
    """
    want_headless = os.environ.get("UI_TEST_HEADLESS", "true").lower() != "false"
    profile       = PROFILE_DIRS[service]
    url           = URLS[service]
    target_domain = url.split("//")[1].split("/")[0]
    os.makedirs(profile, exist_ok=True)

    # 이전 실행이 비정상 종료된 경우 프로필 잠금 파일 자동 제거
    for lock_file in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        lock_path = os.path.join(profile, lock_file)
        try:
            os.remove(lock_path)
            print(f"  [프로필] 잠금 파일 제거: {lock_file}")
        except FileNotFoundError:
            pass

    def _ctx_options(headless: bool) -> dict:
        opts = dict(
            user_data_dir=profile,
            headless=headless,
        )
        if headless:
            opts["args"] = ["--disable-blink-features=AutomationControlled"]
        if record_video_dir:
            opts["record_video_dir"]  = record_video_dir
            opts["record_video_size"] = {"width": 1280, "height": 720}
        return opts

    def _inject_localstorage(ctx):
        """프로필 초기화 후 local-pos-id 없을 때 접근 권한 팝업 방지"""
        if service == "self_pos":
            ctx.add_init_script(
                f"if(location.hostname==='{target_domain}')"
                f"  localStorage.setItem('local-pos-id','{POS_ID}');"
            )

    def _try_headless():
        ctx = p.chromium.launch_persistent_context(**_ctx_options(headless=True))
        _inject_localstorage(ctx)
        # 이전 실행에서 저장된 앱 세션 쿠키 삭제 → 신선한 단일 세션 보장
        # Okta SSO 쿠키(다른 도메인)는 유지되므로 수동 로그인 불필요
        try:
            ctx.clear_cookies(domain=target_domain)
        except Exception:
            pass
        pg  = ctx.new_page()
        pg.goto(url, wait_until="domcontentloaded", timeout=20000)
        try:
            pg.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        if _is_app_page(pg, target_domain):
            return ctx, pg

        if _is_okta_page(pg):
            print(f"\n  [{service}] headless에서 Okta 감지 → ID/PW 로그인 시도")
            try:
                _auto_login(pg, target_domain)
                if _is_app_page(pg, target_domain):
                    print(f"\n  [{service}] 🤖 headless 로그인 성공")
                    return ctx, pg
            except Exception as e:
                print(f"\n  [{service}] headless 로그인 실패: {e}")

        print(f"\n  [{service}] headless 진입 불가 (URL: {pg.url[:80]})")
        pg.close()
        ctx.close()
        return None, None

    def _open_headed():
        ctx = p.chromium.launch_persistent_context(**_ctx_options(headless=False))
        _inject_localstorage(ctx)
        try:
            ctx.clear_cookies(domain=target_domain)
        except Exception:
            pass
        pg  = ctx.new_page()
        pg.goto(url, wait_until="domcontentloaded", timeout=20000)
        _login_if_needed(pg, target_domain)
        return ctx, pg

    if not want_headless:
        print(f"\n  [{service}] 👁 Headed 모드로 실행")
        return _open_headed()

    ctx, pg = _try_headless()
    if ctx is not None:
        return ctx, pg

    print(f"\n  [{service}] headless 불가 → headed 모드 폴백")
    return _open_headed()


# ── 공통: Okta 로그인 대기 및 앱 URL 복귀 대기 ───────────────

def _wait_for_app(page, target_domain: str, timeout: int = 90000):
    """
    Okta PKCE 플로우가 완료될 때까지 기다린 뒤 앱 URL로 돌아오면 반환.
    - SSO 쿠키가 유효하면 Okta가 자동 재인증해서 앱으로 돌아옴.
    - SSO 쿠키가 만료된 경우 Okta 로그인 화면에서 자동 입력 시도.
    """
    start = __import__("time").time()

    def _is_app_url(url: str) -> bool:
        # 쿼리 파라미터 제거 후 비교 (redirect_uri 오탐 방지)
        return url.split("?")[0].startswith(f"https://{target_domain}")

    # Okta → 앱 URL 복귀 대기 (최대 timeout ms)
    try:
        page.wait_for_url(_is_app_url, timeout=timeout)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        # ※ networkidle 중 앱이 Okta로 재리다이렉트할 수 있음 → URL 재확인
        if _is_app_url(page.url) and not _is_okta_page(page):
            if not _dismiss_auth_failed_popup(page):
                return  # 팝업 없음 → 정상 복귀
            # 팝업 dismiss → Okta 재리다이렉트 가능 → 재시도 루프로 fall-through
        # Okta로 재리다이렉트됐거나 에러 페이지 → 아래 로그인 처리로 fall-through
    except Exception:
        pass

    # 앱 URL에 없거나 팝업 dismiss 후 Okta 리다이렉트 → 자동 로그인 재시도 (최대 3회)
    for attempt in range(3):
        if _is_app_url(page.url) and not _is_okta_page(page):
            if not _dismiss_auth_failed_popup(page):
                return  # 팝업 없음 → 정상 복귀
            # 팝업 있었음 → Okta로 이동 중 → 루프 계속
        print(f"  [_wait_for_app] 앱 URL 아님 (현재: {page.url[:60]}), 로그인 시도 {attempt + 1}/3")
        try:
            _auto_login(page, target_domain)
        except Exception as e:
            print(f"  [_wait_for_app] 로그인 시도 {attempt + 1} 실패: {e}")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

    # 최종 검증: 앱 URL에 없으면 FAIL
    if not _is_app_url(page.url) or _is_okta_page(page):
        raise RuntimeError(
            f"_wait_for_app: 3회 시도 후에도 앱 URL에 도달하지 못했습니다\n"
            f"현재 URL: {page.url}"
        )
    # 최종 앱 도달 후 팝업 한 번 더 확인 — 있으면 dismiss 후 재시도 없이 에러
    if _dismiss_auth_failed_popup(page):
        raise RuntimeError(
            f"_wait_for_app: 3회 재시도 후에도 '인증에 실패했습니다' 팝업이 계속 나타납니다\n"
            f"현재 URL: {page.url}"
        )


# ── Self-POS fixtures ────────────────────────────────────────

def _login_if_needed(page, target_domain: str):
    """
    networkidle까지 기다린 뒤 Okta에 있으면 자동 로그인.
    완료 후 앱 URL에 있으면 반환, 실패하면 예외.
    """
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass  # networkidle timeout은 무시하고 URL 체크

    if _is_okta_page(page):
        print(f"\n  → Okta 감지, 자동 로그인 시작...")
        _auto_login(page, target_domain)

    # 앱이 세션 오류 후 Okta로 재리다이렉트 → 1회 재시도
    if _is_okta_page(page):
        print(f"\n  → Okta 재리다이렉트 감지, 재로그인 시도...")
        _auto_login(page, target_domain)

    if not _is_app_page(page, target_domain):
        raise RuntimeError(f"로그인 후에도 앱 URL 아님: {page.url}")


@pytest.fixture(scope="module")
def self_pos_context():
    """
    모듈 단위 컨텍스트.
    auth_page를 닫지 않고 유지 → self_pos_page에서 reload()로 재사용.
    new_page() + goto() 방식은 Okta 재인증으로 새 서버 세션이 생성되어
    Single Session 정책 충돌 팝업이 반복 발생하므로 사용하지 않음.
    """
    service    = "self_pos"
    run_id     = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_dir     = os.path.join(SCREENSHOTS_DIR, f"{service}_{run_id}")
    videos_dir = os.path.join(ROOT_DIR, "test_results", "videos", f"{service}_{run_id}")
    os.makedirs(ts_dir, exist_ok=True)
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(TRACES_DIR, exist_ok=True)

    with sync_playwright() as p:
        try:
            context, auth_page = _get_authenticated_context(
                p, service, record_video_dir=videos_dir
            )
        except Exception as e:
            pytest.fail(f"[{service}] 로그인 실패: {e}\n.env의 OKTA_EMAIL/PASSWORD 확인")

        # auth_page는 SSO 쿠키 확보 목적으로만 사용, 이후 닫음
        # 테스트마다 새 페이지를 생성하되 쿠키를 사전 삭제해 Single Session 충돌 방지
        auth_page.close()
        yield context, ts_dir, videos_dir, run_id

        context.close()


@pytest.fixture
def self_pos_page(self_pos_context, request):
    api_type = request.param if hasattr(request, "param") else os.environ.get("UI_TEST_API_TYPE", "mpos")
    context, ts_dir, videos_dir, run_id = self_pos_context

    safe_name = re.sub(r'[^\w\-]', '_', request.node.name)[:60]
    per_test_trace = os.path.join(TRACES_DIR, f"self_pos_{safe_name}_{run_id}.zip")

    shot_paths = []
    request.node._shot_paths = shot_paths
    request.node._video_path = None
    request.node._trace_path = per_test_trace

    target_domain = URLS["self_pos"].split("//")[1].split("/")[0]

    # ── Single Session 충돌 방지 전략 ────────────────────────────
    try:
        context.clear_cookies(domain=target_domain)
    except Exception:
        pass

    page = context.new_page()
    page.add_init_script(f"""
        if (location.hostname === '{target_domain}') {{
            localStorage.setItem('apiType', '{api_type}');
            localStorage.setItem('local-pos-id', '{POS_ID}');
        }}
    """)

    # Okta SSO 완료까지 대기 (trace 시작 전) — Okta 네트워크가 trace를 오염시키지 않도록
    try:
        page.goto(URLS["self_pos"], wait_until="domcontentloaded", timeout=20000)
        _wait_for_app(page, target_domain, timeout=60000)
    except Exception as e:
        try:
            fail_shot = os.path.join(ts_dir, "00_setup_failed.png")
            page.screenshot(path=fail_shot, full_page=True)
            shot_paths.append(fail_shot)
        except Exception:
            pass
        video = page.video
        page.close()
        if video:
            try:
                dst = os.path.join(ts_dir, "video_setup_failed.webm")
                video.save_as(dst)
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    request.node._video_path = dst
            except Exception:
                pass
        pytest.fail(f"self_pos_page setup 실패: {e}")

    # 앱 도달 후 localStorage 재확인 (Okta 경유 시 init_script 값 덮일 수 있음)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
        page.evaluate(f"""
            localStorage.setItem('apiType', '{api_type}');
            localStorage.setItem('local-pos-id', '{POS_ID}');
        """)
    except Exception as e:
        print(f"  [localStorage 재설정 스킵]: {e}")

    # 앱 진입 완료 후 trace 시작 — 셀프계산 시작하기 화면부터 TC 종료까지 전체 캡처
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    _attach_screenshot_helper(page, ts_dir, shot_paths)
    yield page

    # TC별 trace 저장
    try:
        context.tracing.stop(path=per_test_trace)
    except Exception as te:
        print(f"  ⚠ trace 저장 실패: {te}")

    # 비디오 저장 후 페이지 닫기
    video = page.video
    page.close()
    if video:
        try:
            dst = os.path.join(ts_dir, f"video_{safe_name}.webm")
            video.save_as(dst)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                request.node._video_path = dst
            else:
                print(f"  ⚠ 비디오 파일 비어 있음: {dst}")
        except Exception as e:
            print(f"  ⚠ 비디오 저장 실패: {e}")


# ── mPOS fixtures ────────────────────────────────────────────

@pytest.fixture(scope="module")
def mpos_context():
    service    = "mpos"
    run_id     = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_dir     = os.path.join(SCREENSHOTS_DIR, f"{service}_{run_id}")
    videos_dir = os.path.join(ROOT_DIR, "test_results", "videos", f"{service}_{run_id}")
    os.makedirs(ts_dir, exist_ok=True)
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(TRACES_DIR, exist_ok=True)

    with sync_playwright() as p:
        try:
            context, auth_page = _get_authenticated_context(
                p, service, record_video_dir=videos_dir
            )
        except Exception as e:
            pytest.fail(f"[{service}] 로그인 실패: {e}")

        auth_page.close()

        yield context, ts_dir, videos_dir, run_id

        context.close()


@pytest.fixture
def mpos_page(mpos_context, request):
    params                              = request.param if hasattr(request, "param") else (
        os.environ.get("UI_TEST_API_TYPE", "mpos"),
        os.environ.get("UI_TEST_FE_TYPE", "MPOS")
    )
    api_type, fe_type                   = params
    context, ts_dir, videos_dir, run_id = mpos_context

    safe_name      = re.sub(r'[^\w\-]', '_', request.node.name)[:60]
    per_test_trace = os.path.join(TRACES_DIR, f"mpos_{safe_name}_{run_id}.zip")

    shot_paths = []
    request.node._shot_paths = shot_paths
    request.node._video_path = None
    request.node._trace_path = per_test_trace

    target_domain = URLS["mpos"].split("//")[1].split("/")[0]

    page = context.new_page()
    page.goto(URLS["mpos"], wait_until="domcontentloaded", timeout=20000)
    try:
        _wait_for_app(page, target_domain, timeout=30000)
    except Exception as e:
        page.close()
        pytest.fail(f"mpos_page 인증 실패: {e}")

    page.evaluate(f"""
        localStorage.setItem('apiType', '{api_type}');
        localStorage.setItem('feType', '{fe_type}');
        localStorage.setItem('local-pos-id', '{POS_ID}');
    """)

    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    _attach_screenshot_helper(page, ts_dir, shot_paths)
    yield page

    # TC별 trace 저장
    try:
        context.tracing.stop(path=per_test_trace)
    except Exception as te:
        print(f"  ⚠ trace 저장 실패: {te}")

    # 비디오 저장
    video = page.video
    page.close()
    if video:
        try:
            dst = os.path.join(ts_dir, f"video_{safe_name}.webm")
            video.save_as(dst)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                request.node._video_path = dst
            else:
                print(f"  ⚠ 비디오 파일 비어 있음: {dst}")
        except Exception as e:
            print(f"  ⚠ 비디오 저장 실패: {e}")


# ── PDP fixtures ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def pdp_context():
    service = "pdp"
    profile = PROFILE_DIRS[service]
    os.makedirs(profile, exist_ok=True)

    run_id  = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_dir  = os.path.join(SCREENSHOTS_DIR, f"pdp_{run_id}")
    os.makedirs(ts_dir, exist_ok=True)
    os.makedirs(TRACES_DIR, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=True,
        )

        yield context, ts_dir, run_id

        context.close()


@pytest.fixture
def pdp_page(pdp_context, request):
    params   = request.param if hasattr(request, "param") else {}
    api_type = params.get("api_type", os.environ.get("UI_TEST_API_TYPE", "mpos"))
    goods_no = params.get("goods_no", "1015777")
    shop_no  = "64"
    context, ts_dir, run_id = pdp_context

    safe_name      = re.sub(r'[^\w\-]', '_', request.node.name)[:60]
    per_test_trace = os.path.join(TRACES_DIR, f"pdp_{safe_name}_{run_id}.zip")

    shot_paths = []
    request.node._shot_paths = shot_paths
    request.node._trace_path = per_test_trace

    url  = f"{URLS['pdp']}?goodsNo={goods_no}&shopNo={shop_no}"
    page = context.new_page()
    _goto_with_env(page, url, api_type)

    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    _attach_screenshot_helper(page, ts_dir, shot_paths)

    yield page

    # TC별 trace 저장
    try:
        context.tracing.stop(path=per_test_trace)
    except Exception as te:
        print(f"  ⚠ trace 저장 실패: {te}")

    page.close()


# ── pytest-html extras hook + Allure 아티팩트 첨부 ─────────────
# trylast=True: 가장 안쪽(innermost) 래퍼로 등록되어 post-yield가 가장 먼저 실행됨
# → allure가 테스트 라이프사이클을 닫기 전에 attach가 호출되어 Attachments 탭에 표시됨

@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()

    from pytest_html import extras as html_extras
    extra_list = []

    # setup 실패 시에도 캡처한 데이터가 리포트에 포함되도록
    # - 스크린샷/Trace: call 단계 또는 setup 실패 단계에 첨부
    # - 비디오: teardown 단계 또는 setup 실패 단계에 첨부
    if report.when == "call" or (report.when == "setup" and report.failed):
        # 스크린샷
        for path in getattr(item, "_shot_paths", []):
            if os.path.exists(path):
                with open(path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
                label = os.path.basename(path)
                extra_list.append(html_extras.html(
                    f'<div style="margin:6px 0">'
                    f'<p style="font-size:12px;color:#666;margin:2px 0">{label}</p>'
                    f'<img src="data:image/png;base64,{img_b64}" '
                    f'style="max-width:600px;border:1px solid #ddd;border-radius:4px"/>'
                    f'</div>'
                ))
        # Trace 경로
        trace_path = getattr(item, "_trace_path", None)
        if trace_path:
            extra_list.append(html_extras.html(
                f'<div style="margin:6px 0;font-size:12px">'
                f'🔍 Trace: <code>{trace_path}</code><br/>'
                f'<span style="color:#888">확인: <code>playwright show-trace {trace_path}</code></span>'
                f'</div>'
            ))

    if report.when == "teardown" or (report.when == "setup" and report.failed):
        # 비디오 (페이지 닫힌 후 확정된 파일)
        video_path = getattr(item, "_video_path", None)
        if video_path and os.path.exists(video_path):
            with open(video_path, "rb") as f:
                video_b64 = base64.b64encode(f.read()).decode("utf-8")
            extra_list.append(html_extras.html(
                f'<div style="margin:8px 0">'
                f'<p style="font-size:12px;color:#666;margin:2px 0">🎬 테스트 녹화</p>'
                f'<video controls style="max-width:100%;border:1px solid #ddd;border-radius:4px">'
                f'<source src="data:video/webm;base64,{video_b64}" type="video/webm">'
                f'</video>'
                f'</div>'
            ))

    if extra_list:
        report.extras = getattr(report, "extras", []) + extra_list

    # ── Allure 아티팩트 첨부 (teardown 완료 후, allure 라이프사이클 닫히기 전) ──
    if report.when == "teardown":
        hub_url = os.environ.get("QA_HUB_URL", "http://localhost:5001")

        # 비디오
        video_path = getattr(item, "_video_path", None)
        if video_path and os.path.exists(video_path):
            try:
                allure.attach.file(
                    video_path,
                    name="테스트 녹화",
                    attachment_type=allure.attachment_type.WEBM,
                )
            except Exception:
                pass

        # Trace → trace.playwright.dev 링크
        trace_path = getattr(item, "_trace_path", None)
        if trace_path and os.path.exists(trace_path):
            try:
                filename     = os.path.basename(trace_path)
                trace_url    = (
                    f"https://trace.playwright.dev/"
                    f"?trace={hub_url}/api/ui-test/trace-file/{filename}"
                )
                allure.attach(
                    (
                        f'<a href="{trace_url}" target="_blank" '
                        f'style="display:inline-block;padding:6px 14px;'
                        f'background:#1976d2;color:#fff;border-radius:4px;'
                        f'text-decoration:none;font-size:13px;font-weight:500">'
                        f'🔍 Playwright Trace 열기</a>'
                        f'<p style="margin:4px 0 0;font-size:11px;color:#888">'
                        f'{filename}</p>'
                    ),
                    name="Playwright Trace",
                    attachment_type=allure.attachment_type.HTML,
                )
            except Exception:
                pass
