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
        """
        셀프계산 시작하기 화면에서 비회원 버튼을 클릭한다.
        성공 시 바코드 스캔 화면("바코드를 스캔해주세요")으로 이동.
        """
        nonmember_btn = self.page.get_by_role("button", name="비회원")
        nonmember_btn.wait_for(state="visible", timeout=10000)
        nonmember_btn.click()

        # 결제 화면 진입 확인
        self.page.wait_for_selector(
            "text=바코드를 스캔해주세요",
            timeout=10000,
        )

    # ── Step 2: 바코드 스캔 (테스트 상품 선택) ──────────────────
    @allure.step("바코드 스캔 화면에서 테스트 바코드 '위탁-2 - 3422886' 선택")
    def scan_test_barcode(self, barcode: str = "위탁-2 - 3422886"):
        """
        바코드 스캔 화면에서 테스트 바코드를 선택한다.
        '위탁-2 - 3422886'은 QA 전용 테스트 바코드이다.
        """
        # 테스트 바코드 버튼/리스트 아이템 클릭
        barcode_item = self.page.get_by_text(barcode, exact=True)
        barcode_item.wait_for(state="visible", timeout=10000)
        barcode_item.click()

        # 상품이 결제 목록에 추가되어 '결제하기' 버튼 활성화 대기
        self.page.wait_for_selector(
            "button:has-text('결제하기')",
            timeout=10000,
        )

    # ── Step 3: 결제하기 버튼 클릭 ──────────────────────────────
    @allure.step("'결제하기' 버튼 클릭")
    def click_payment_button(self):
        """
        결제하기 버튼을 클릭한다.
        클릭 후 '쇼핑백을 선택해주세요' 레이어가 나타나야 한다.
        """
        pay_btn = self.page.get_by_role("button", name="결제하기")
        pay_btn.wait_for(state="visible", timeout=10000)
        pay_btn.click()

        # 쇼핑백 선택 레이어 등장 대기
        self.page.wait_for_selector(
            "text=쇼핑백을 선택해주세요",
            timeout=10000,
        )

    # ── Step 4: 쇼핑백 레이어 → 취소 ───────────────────────────
    @allure.step("'쇼핑백을 선택해주세요' 레이어에서 [취소] 선택")
    def dismiss_shopping_bag_layer(self):
        """
        쇼핑백 선택 레이어에서 취소 버튼을 클릭한다.
        취소 후 쿠폰 레이어 또는 다음 결제 단계로 이동한다.
        """
        cancel_btn = self.page.get_by_role("button", name="취소")
        cancel_btn.wait_for(state="visible", timeout=10000)
        cancel_btn.click()

        # 쇼핑백 레이어가 사라질 때까지 대기
        self.page.wait_for_selector(
            "text=쇼핑백을 선택해주세요",
            state="hidden",
            timeout=10000,
        )

    # ── Step 5: 쿠폰 레이어 → 0원 할인 적용 ────────────────────
    @allure.step("'사용할 수 있는 쿠폰이 있어요' 레이어에서 0원 할인 적용 선택")
    def apply_zero_discount_coupon(self):
        """
        쿠폰 레이어에서 0원 할인 쿠폰(또는 적용 불가 선택)을 클릭한다.
        '0원 할인 적용' 또는 '쿠폰 사용 안함' 텍스트 버튼을 클릭.
        """
        # 쿠폰 레이어 등장 대기
        self.page.wait_for_selector(
            "text=사용할 수 있는 쿠폰이 있어요",
            timeout=10000,
        )

        # 0원 할인 적용 버튼 클릭 (텍스트가 앱 버전에 따라 다를 수 있음)
        zero_coupon = self.page.get_by_text("0원 할인 적용", exact=True)
        zero_coupon.wait_for(state="visible", timeout=5000)
        zero_coupon.click()

        # 쿠폰 레이어가 사라질 때까지 대기
        self.page.wait_for_selector(
            "text=사용할 수 있는 쿠폰이 있어요",
            state="hidden",
            timeout=10000,
        )
