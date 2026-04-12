"""
Self-POS — 환경 설정 및 초기 진입 테스트
"""
import os


class TestSelfPosSetup:

    def test_landing_after_env_setup(self, self_pos_page):
        """
        [TC-SELFPOS-001] 환경 설정 후 Self-POS 화면 정상 진입
        - apiType: UI_TEST_API_TYPE 환경변수 값 (기본 mpos)
        - local-pos-id: 64-1021
        """
        page = self_pos_page
        page.take_screenshot("landing")

        api_type = page.evaluate("localStorage.getItem('apiType')")
        pos_id   = page.evaluate("localStorage.getItem('local-pos-id')")

        page.take_screenshot("env_verified")

        expected_api_type = os.environ.get("UI_TEST_API_TYPE", "mpos")
        assert api_type == expected_api_type, f"apiType 불일치: {api_type} (기대값: {expected_api_type})"
        assert pos_id   == "64-1021", f"local-pos-id 불일치: {pos_id}"

        # Okta redirect_uri에도 "self-pos"가 포함되므로 쿼리 파라미터 제거 후 비교
        clean_url = page.url.split("?")[0]
        assert clean_url.startswith("https://self-pos.dev.one.musinsa.com"), (
            f"앱 URL이 아님 (로그인 화면?): {page.url}"
        )

        page.take_screenshot("done")

    # TC-SELFPOS-002: mpos2/mpos3 환경 전환은 QA Hub UI에서 수동 선택하는 초기 설정용
    # 자동화 테스트에서는 제외
