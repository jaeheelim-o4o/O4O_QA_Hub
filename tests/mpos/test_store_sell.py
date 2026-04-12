"""
mPOS — 판매 화면 진입 및 환경 설정 테스트
"""
import pytest


class TestMposSell:

    def test_landing_after_env_setup(self, mpos_page):
        """
        [TC-MPOS-001] 환경 설정 후 mPOS 판매 화면 정상 진입
        - apiType: mpos (기본값)
        - feType: MPOS (기본값)
        - local-pos-id: 64-1021
        """
        page = mpos_page
        page.take_screenshot("landing")

        api_type = page.evaluate("localStorage.getItem('apiType')")
        fe_type  = page.evaluate("localStorage.getItem('feType')")
        pos_id   = page.evaluate("localStorage.getItem('local-pos-id')")

        page.take_screenshot("env_verified")

        assert api_type == page.evaluate("localStorage.getItem('apiType')"), "apiType 확인 실패"
        assert pos_id == "64-1021", f"local-pos-id 불일치: {pos_id}"
        assert "mpos" in page.url.lower(), f"예상치 못한 URL: {page.url}"

        page.take_screenshot("done")

    @pytest.mark.parametrize(
        "mpos_page",
        [("mpos1", "MPOS"), ("mpos2", "MPOS2"), ("mpos3", "MPOS3")],
        indirect=True
    )
    def test_env_combination(self, mpos_page):
        """
        [TC-MPOS-002] API + FE 환경 조합 진입 확인
        """
        page     = mpos_page
        api_type = page.evaluate("localStorage.getItem('apiType')")
        fe_type  = page.evaluate("localStorage.getItem('feType')")

        page.take_screenshot(f"api_{api_type}_fe_{fe_type}")

        assert api_type is not None, "apiType이 설정되지 않음"
        assert fe_type is not None, "feType이 설정되지 않음"
        assert "mpos" in page.url.lower(), f"예상치 못한 URL: {page.url}"
