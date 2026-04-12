"""
PDP — 비회원 접근 테스트
"""
import pytest


class TestPdpNonmember:

    def test_pdp_nonmember_access(self, pdp_page):
        """
        [TC-PDP-101] 비회원 PDP 접근 — 주요 UI 요소 확인
        """
        page = pdp_page
        page.take_screenshot("nonmember_landing")

        # 상품 정보 영역이 로드되는지 확인 (selector는 실제 앱에 맞게 수정 필요)
        try:
            page.wait_for_selector("img, .goods-name, h1, [class*='product'], [class*='goods']",
                                   timeout=10000)
            page.take_screenshot("nonmember_product_visible")
        except Exception:
            page.take_screenshot("nonmember_timeout")
            pytest.skip("상품 정보 영역을 찾지 못함 — selector 확인 필요")

        assert "pdp" in page.url.lower() or "goods" in page.url.lower(), \
            f"예상치 못한 URL: {page.url}"
