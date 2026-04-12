"""
Self-POS 결제 플로우 Page Object
각 step 함수는 @allure.step으로 데코레이트되어 allure 리포트에 단계별 결과가 표시된다.
"""
import allure
from playwright.sync_api import Page


class CheckoutPage:
    """셀프계산 결제 플로우 Step 집합"""

    def __init__(self, page: Page):
        self.page = page

    # ── Step 1: 비회원 선택 ──────────────────────────────────────
    @allure.step("셀프계산 시작하기 화면에서 '비회원' 선택")
    def select_nonmember(self):
        nonmember_btn = self.page.get_by_role("button", name="비회원")
        nonmember_btn.wait_for(state="visible", timeout=10000)
        nonmember_btn.click()

        self.page.wait_for_selector("text=바코드를 스캔해주세요", timeout=10000)

    # ── Step 2: 바코드 스캔 (테스트 상품 선택) ──────────────────
    @allure.step("바코드 스캔 화면에서 테스트 바코드 '위탁-2 - 3422886' 선택")
    def scan_test_barcode(self, barcode: str = "위탁-2 - 3422886"):
        barcode_item = self.page.get_by_text(barcode, exact=True)
        barcode_item.wait_for(state="visible", timeout=10000)
        barcode_item.click()

        self.page.wait_for_selector("button:has-text('결제하기')", timeout=10000)

    # ── Step 3: 결제하기 버튼 클릭 ──────────────────────────────
    @allure.step("'결제하기' 버튼 클릭")
    def click_payment_button(self):
        pay_btn = self.page.get_by_role("button", name="결제하기")
        pay_btn.wait_for(state="visible", timeout=10000)
        pay_btn.click()

        self.page.wait_for_selector("text=쇼핑백을 선택해주세요", timeout=10000)

    # ── Step 4: 쇼핑백 레이어 → 취소 ───────────────────────────
    @allure.step("'쇼핑백을 선택해주세요' 레이어에서 [취소] 선택")
    def dismiss_shopping_bag_layer(self):
        cancel_btn = self.page.get_by_role("button", name="취소")
        cancel_btn.wait_for(state="visible", timeout=10000)
        cancel_btn.click()

        self.page.wait_for_selector(
            "text=쇼핑백을 선택해주세요", state="hidden", timeout=10000
        )

    # ── Step 5: 쿠폰 레이어 → 0원 할인 적용 ────────────────────
    @allure.step("'사용할 수 있는 쿠폰이 있어요' 레이어에서 0원 할인 적용 선택")
    def apply_zero_discount_coupon(self):
        self.page.wait_for_selector("text=사용할 수 있는 쿠폰이 있어요", timeout=10000)

        zero_coupon = self.page.get_by_text("0원 할인 적용", exact=True)
        zero_coupon.wait_for(state="visible", timeout=5000)
        zero_coupon.click()

        self.page.wait_for_selector(
            "text=사용할 수 있는 쿠폰이 있어요", state="hidden", timeout=10000
        )

    # ── Step 6: 보안택·옷걸이 제거 안내 → 확인 ──────────────────
    @allure.step("'보안택 옷걸이를 제거해주세요' 화면에서 [확인] 선택")
    def confirm_security_tag_removal(self):
        self.page.wait_for_selector("text=보안택", timeout=10000)

        confirm_btn = self.page.get_by_role("button", name="확인")
        confirm_btn.wait_for(state="visible", timeout=5000)
        confirm_btn.click()

        self.page.wait_for_selector("text=보안택", state="hidden", timeout=10000)

    # ── Step 7: 무신사 가입 혜택 화면 → 혜택 없이 결제 ──────────
    @allure.step("'무신사 가입하면 10% 즉시할인' 화면에서 혜택 없이 결제 선택")
    def skip_musinsa_membership_benefit(self):
        self.page.wait_for_selector("text=무신사 가입하면", timeout=10000)

        skip_btn = self.page.get_by_text("혜택 없이 결제", exact=True)
        skip_btn.wait_for(state="visible", timeout=5000)
        skip_btn.click()

        self.page.wait_for_selector("text=무신사 가입하면", state="hidden", timeout=10000)

    # ── Step 8: 택스리펀 레이어 → 건너뛰기 ─────────────────────
    @allure.step("'택스리펀을 신청하시겠어요?' 레이어에서 건너뛰기 선택")
    def skip_tax_refund(self):
        self.page.wait_for_selector("text=택스리펀", timeout=10000)

        skip_btn = self.page.locator("button", has_text="건너뛰기")
        skip_btn.wait_for(state="visible", timeout=5000)
        self.page.wait_for_timeout(1000)  # 슬라이드 인 애니메이션 완료 대기
        # JS 직접 호출: 애니메이션/오버레이 관계없이 클릭 핸들러 직접 실행
        skip_btn.evaluate("el => el.click()")

        self.page.wait_for_selector("text=택스리펀", state="hidden", timeout=10000)

    # ── Step 9: 결제 수단 선택 → 신용/체크카드 ──────────────────
    @allure.step("결제 화면에서 신용/체크카드 선택")
    def select_credit_card(self):
        card_btn = self.page.get_by_text("신용·체크카드", exact=False)
        card_btn.wait_for(state="visible", timeout=10000)
        card_btn.click()

        self.page.wait_for_selector("text=할부 기간을 선택해주세요", timeout=10000)

    # ── Step 10: 할부 기간 레이어 → 일시불 선택 후 확인 ─────────
    @allure.step("'할부 기간을 선택해주세요' 레이어에서 일시불 선택 후 확인")
    def select_lump_sum_payment(self):
        self.page.wait_for_selector("text=할부 기간을 선택해주세요", timeout=10000)

        lump_sum_btn = self.page.get_by_text("일시불", exact=True)
        lump_sum_btn.wait_for(state="visible", timeout=5000)
        lump_sum_btn.click()

        confirm_btn = self.page.get_by_role("button", name="확인")
        confirm_btn.wait_for(state="visible", timeout=5000)
        confirm_btn.click()

        self.page.wait_for_selector(
            "text=할부 기간을 선택해주세요", state="hidden", timeout=10000
        )

    # ── Step 11: 영수증 화면 확인 ───────────────────────────────
    @allure.step("'영수증을 챙겨주세요' 화면 노출 확인")
    def verify_receipt_screen(self):
        self.page.wait_for_selector("text=영수증을 챙겨주세요", timeout=30000)

    # ── Step 12: 처음으로 → 셀프계산 시작하기 복귀 ──────────────
    @allure.step("'처음으로' 선택 후 셀프계산 시작하기 화면 복귀 확인")
    def go_to_home(self):
        home_btn = self.page.get_by_role("button", name="처음으로")
        home_btn.wait_for(state="visible", timeout=10000)
        home_btn.click()

        self.page.wait_for_selector("text=셀프계산 시작하기", timeout=10000)
