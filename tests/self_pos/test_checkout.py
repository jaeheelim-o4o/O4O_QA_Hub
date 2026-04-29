"""
Self-POS — 결제 플로우 테스트
Suite: 정상 결제 케이스
"""
import allure

from tests.self_pos.pages.checkout_page import CheckoutPage


@allure.feature("Self-POS")
@allure.story("정상 결제")
class TestSelfPosCheckout:

    @allure.title("[TC-CHECKOUT-001] 비회원 정상 결제 — 위탁 상품 바코드 스캔 후 신용카드 일시불 결제")
    def test_nonmember_normal_payment(self, self_pos_page):
        """
        비회원 결제 정상 플로우 전체를 하나의 TC로 검증한다.

        Steps:
          1.  셀프계산 시작하기 화면에서 '비회원' 선택
          2.  바코드 스캔 화면에서 테스트 바코드 '위탁-2 - 3422886' 선택
          3.  '결제하기' 버튼 클릭
          4.  '쇼핑백을 선택해주세요' 레이어에서 [취소] 선택
          5.  '사용할 수 있는 쿠폰이 있어요' 레이어에서 0원 할인 적용 선택
          6.  '보안택 옷걸이를 제거해주세요' 화면에서 [확인] 선택 (조건부)
          7.  '무신사 가입하면 10% 즉시할인' 화면에서 혜택 없이 결제 선택 (조건부)
          8.  '택스리펀을 신청하시겠어요?' 레이어에서 건너뛰기 선택
          9.  결제 화면에서 신용/체크카드 선택
          10. '할부 기간을 선택해주세요' 레이어에서 일시불 선택 후 확인
          11. '영수증을 챙겨주세요' 화면 노출 확인
          12. '처음으로' 선택 후 셀프계산 시작하기 화면 복귀 확인
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

        # 경우에 따라 노출되는 레이어 — 없으면 스킵
        _dismiss_if_visible(page, checkout.confirm_security_tag_removal, "보안 스티커")
        page.take_screenshot("after_security_tag")

        _dismiss_if_visible(page, checkout.skip_musinsa_membership_benefit, "무신사 가입하면")
        page.take_screenshot("after_membership_benefit")

        checkout.skip_tax_refund()
        page.take_screenshot("tax_refund_skipped")

        checkout.select_credit_card()
        page.take_screenshot("credit_card_selected")

        checkout.select_lump_sum_payment()
        page.take_screenshot("lump_sum_selected")

        checkout.verify_receipt_screen()
        page.take_screenshot("receipt_screen")

        checkout.go_to_home()
        page.take_screenshot("back_to_home")


def _dismiss_if_visible(page, step_fn, trigger_text: str, timeout: int = 3000):
    """
    trigger_text가 화면에 있을 때만 step_fn을 실행한다.
    조건부 레이어(경우에 따라 노출)에 사용.
    """
    try:
        page.wait_for_selector(f"text={trigger_text}", timeout=timeout)
        step_fn()
    except Exception:
        pass  # 레이어 미노출 → 정상 케이스
