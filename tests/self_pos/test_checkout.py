"""
Self-POS — 결제 플로우 테스트
Suite: 정상 결제 케이스
"""
import allure
import pytest

from tests.self_pos.pages.checkout_page import CheckoutPage


@allure.feature("Self-POS")
@allure.story("정상 결제")
class TestSelfPosCheckout:

    @allure.title("[TC-CHECKOUT-001] 비회원 정상 결제 — 위탁 상품 바코드 스캔 후 결제 (쇼핑백 취소, 0원 쿠폰 적용)")
    def test_nonmember_normal_payment(self, self_pos_page):
        """
        비회원 결제 정상 플로우 전체를 하나의 TC로 검증한다.

        Steps:
          1. 셀프계산 시작하기 화면에서 '비회원' 선택
          2. 바코드 스캔 화면에서 테스트 바코드 '위탁-2 - 3422886' 선택
          3. '결제하기' 버튼 클릭
          4. '쇼핑백을 선택해주세요' 레이어에서 [취소] 클릭
          5. '사용할 수 있는 쿠폰이 있어요' 레이어에서 0원 할인 적용 선택
        """
        page = self_pos_page
        checkout = CheckoutPage(page)

        page.take_screenshot("initial")

        checkout.select_nonmember()
        page.take_screenshot("nonmember_selected")

        checkout.scan_test_barcode("위탁-2 - 3422886")
        page.take_screenshot("barcode_scanned")

        checkout.click_payment_button()
        page.take_screenshot("payment_clicked")

        checkout.dismiss_shopping_bag_layer()
        page.take_screenshot("shopping_bag_dismissed")

        checkout.apply_zero_discount_coupon()
        page.take_screenshot("coupon_applied")
