"""
세션 갱신 CLI 스크립트
QA Hub 백엔드에서 호출하거나 직접 터미널에서 실행 가능

사용법:
  python tests/session_manager.py self_pos
  python tests/session_manager.py mpos
  python tests/session_manager.py pdp
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import refresh_okta_session, PROFILE_DIRS, profile_exists
from dotenv import load_dotenv

load_dotenv()


def refresh_pdp_session():
    """PDP 고객 계정 로그인 세션 저장"""
    from playwright.sync_api import sync_playwright

    email    = os.environ.get("CUSTOMER_EMAIL", "")
    password = os.environ.get("CUSTOMER_PASSWORD", "")

    if not email or not password:
        raise ValueError(".env에 CUSTOMER_EMAIL과 CUSTOMER_PASSWORD를 설정해주세요.")

    print("\n[세션 갱신] pdp — 브라우저가 열립니다.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page    = context.new_page()

        page.goto("https://pdp-web.dev.musinsa.com/pdp/goods?goodsNo=1015777&shopNo=64")

        # 로그인 버튼 클릭 (페이지 구조에 따라 selector 수정 필요)
        try:
            page.click("text=로그인", timeout=5000)
            page.wait_for_selector("input[type='email'], input[name='email']", timeout=10000)
            page.fill("input[type='email'], input[name='email']", email)
            page.fill("input[type='password']", password)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            print(f"  ⚠ 로그인 자동화 실패, 수동으로 로그인해주세요: {e}")
            input("  로그인 완료 후 엔터를 누르세요...")

        context.storage_state(path=SESSION_FILES["pdp"])
        print(f"  ✅ 세션 저장 완료: {SESSION_FILES['pdp']}")
        browser.close()


def check_sessions():
    """모든 서비스 프로필 상태 출력"""
    print("\n[프로필 상태]")
    for service, path in PROFILE_DIRS.items():
        exists = profile_exists(service)
        status = "✅ 있음" if exists else "❌ 없음"
        print(f"  {service:10s}: {status}  ({path})")
    print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "status":
        check_sessions()
        sys.exit(0)

    service = args[0].lower()

    if service == "pdp":
        refresh_pdp_session()
    elif service in ("self_pos", "mpos"):
        refresh_okta_session(service)
    else:
        print(f"알 수 없는 서비스: {service}")
        print("사용법: python tests/session_manager.py [self_pos|mpos|pdp|status]")
        sys.exit(1)
