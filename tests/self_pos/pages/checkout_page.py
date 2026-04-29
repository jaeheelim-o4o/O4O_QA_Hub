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

        self.page.wait_for_selector("text=바구니에 담고 스캔해주세요", timeout=10000)

    # ── Step 2: 바코드 스캔 (테스트 상품 선택) ──────────────────
    @allure.step("바코드 스캔 화면에서 테스트 바코드 '위탁-2 - 3422886' 선택")
    def scan_test_barcode(self, barcode: str = "위탁-2 - 3422886"):
        # 테스트 바코드 패널이 보이는지 확인
        barcode_item = self.page.get_by_text(barcode, exact=True)
        barcode_item.wait_for(state="visible", timeout=10000)

        # 바코드 번호 부분만 추출 ("위탁-2 - 3422886" → "3422886")
        barcode_number = barcode.split(" - ")[-1].strip() if " - " in barcode else barcode

        # POS 바코드 스캐너 시뮬레이션: 바코드 번호를 빠르게 키보드 입력 후 Enter
        # (실제 바코드 스캐너는 키보드 HID처럼 동작 - 빠른 키 입력 후 Enter)
        self.page.keyboard.type(barcode_number, delay=30)
        self.page.keyboard.press("Enter")

        # 바코드 스캔 후 결제하기 버튼이 활성화될 때까지 대기
        self.page.wait_for_function(
            "() => { const btn = document.querySelector('[data-testid=\"goods-scan-submit-btn\"]'); return !btn || !btn.disabled; }",
            timeout=15000,
        )

        # 테스트 바코드 패널 닫기 (✕ 버튼) — 이후 결제 레이어 상호작용 방해 방지
        try:
            close_btn = self.page.locator("button").filter(has_text="✕").first
            close_btn.click(timeout=3000)
            self.page.wait_for_selector("text=테스트 바코드", state="hidden", timeout=5000)
        except Exception:
            pass  # 패널이 이미 닫혔거나 없으면 무시

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
        self.page.wait_for_selector("text=쇼핑백을 선택해주세요", timeout=10000)

        # '취소' = 쇼핑백 선택 취소 → 스캔 화면으로 복귀
        cancel_btn = self.page.get_by_role("button", name="취소")
        cancel_btn.wait_for(state="visible", timeout=10000)
        cancel_btn.click()

        self.page.wait_for_selector(
            "text=쇼핑백을 선택해주세요", state="hidden", timeout=10000
        )

        # 쇼핑백 취소 후 스캔 화면으로 돌아옴 → 결제하기 재클릭으로 결제 진행
        # ant-modal-wrap이 pointer 이벤트를 차단하므로 force=True로 우회
        pay_btn = self.page.get_by_test_id("goods-scan-submit-btn")
        pay_btn.wait_for(state="visible", timeout=10000)
        pay_btn.click(force=True)

        # 주문 확인 화면 도달 시 '상품 수를 확인해주세요' 팝업 즉시 처리
        # (팝업이 열려있는 동안 이후 쿠폰/보안택 등 팝업이 차단되므로 여기서 닫아야 함)
        try:
            self.page.wait_for_selector("text=상품 수를 확인해주세요", timeout=5000)
            confirm_btn = self.page.get_by_role("button", name="확인")
            confirm_btn.wait_for(state="visible", timeout=5000)
            confirm_btn.click()
            self.page.wait_for_selector(
                "text=상품 수를 확인해주세요", state="hidden", timeout=10000
            )
        except Exception:
            pass  # 팝업 미노출 → 스킵

    # ── Step 5: 쿠폰 레이어 → 0원 할인 적용 ────────────────────
    @allure.step("'사용할 수 있는 쿠폰이 있어요' 레이어에서 0원 할인 적용 선택")
    def apply_zero_discount_coupon(self):
        # 쿠폰 팝업이 없으면 스킵 (비회원이거나 쿠폰 없는 경우)
        try:
            self.page.wait_for_selector("text=사용할 수 있는 쿠폰이 있어요", timeout=5000)
        except Exception:
            return  # 쿠폰 팝업 미노출 → 스킵

        zero_coupon = self.page.get_by_text("0원 할인 적용", exact=True)
        zero_coupon.wait_for(state="visible", timeout=5000)
        zero_coupon.click()

        self.page.wait_for_selector(
            "text=사용할 수 있는 쿠폰이 있어요", state="hidden", timeout=10000
        )

    # ── Step 6: 보안택·옷걸이 제거 안내 → 확인 ──────────────────
    @allure.step("'보안 스티커·옷걸이가 있다면 제거해주세요' 화면에서 [확인] 선택")
    def confirm_security_tag_removal(self):
        self.page.wait_for_selector("text=보안 스티커", timeout=10000)

        confirm_btn = self.page.get_by_role("button", name="확인")
        confirm_btn.wait_for(state="visible", timeout=5000)
        confirm_btn.click()

        self.page.wait_for_selector("text=보안 스티커", state="hidden", timeout=10000)

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
        # 택스리펀 팝업이 없으면 스킵 (비회원/내국인 등 조건부 노출)
        try:
            self.page.wait_for_selector("text=택스리펀", timeout=5000)
        except Exception:
            return  # 팝업 미노출 → 스킵

        # data-testid로 정확히 지정 (같은 텍스트 '건너뛰기' 버튼이 2개 존재)
        skip_btn = self.page.get_by_test_id("taxfree-dialog-cancel")
        skip_btn.wait_for(state="visible", timeout=5000)
        skip_btn.click()

        skip_btn.wait_for(state="hidden", timeout=10000)

    # ── Step 9: 결제 수단 선택 → 신용/체크카드 ──────────────────
    @allure.step("결제 화면에서 신용/체크카드 선택")
    def select_credit_card(self):
        # 결제 수단 선택 화면에서 바로 신용·체크카드 클릭
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
