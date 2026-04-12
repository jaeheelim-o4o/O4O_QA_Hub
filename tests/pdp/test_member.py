"""
PDP — 회원 접근 테스트
"""
import pytest


class TestPdpMember:

    def test_pdp_landing(self, pdp_page):
        """
        [TC-PDP-001] PDP 화면 정상 진입 (비회원 / 회원 공통)
        - goodsNo: 1015777, shopNo: 64
        - apiType: mpos (기본값)
        """
        page = pdp_page
        page.take_screenshot("landing")

        api_type = page.evaluate("localStorage.getItem('apiType')")

        assert api_type is not None, "apiType이 설정되지 않음"
        assert "pdp" in page.url.lower() or "goods" in page.url.lower(), \
            f"예상치 못한 URL: {page.url}"

        page.take_screenshot("done")

    @pytest.mark.parametrize(
        "pdp_page",
        [
            {"goods_no": "1015777", "api_type": "mpos"},
            {"goods_no": "1015777", "api_type": "mpos2"},
        ],
        indirect=True
    )
    def test_api_type_switch(self, pdp_page):
        """
        [TC-PDP-002] API 환경 변경 후 PDP 화면 진입 확인
        """
        page     = pdp_page
        api_type = page.evaluate("localStorage.getItem('apiType')")

        page.take_screenshot(f"api_{api_type}_pdp")

        assert api_type is not None, "apiType이 설정되지 않음"
        assert "mpos" in api_type, f"예상치 못한 apiType: {api_type}"
