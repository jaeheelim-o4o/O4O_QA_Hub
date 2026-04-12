#!/bin/bash
# UI 자동화 테스트 초기 설치 스크립트

set -e

echo "=============================="
echo " QA Hub — UI 자동화 환경 설치"
echo "=============================="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# venv 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "venv가 없습니다. python3 -m venv venv 먼저 실행하세요."
    exit 1
fi

echo ""
echo "[1/3] 패키지 설치 중..."
pip install playwright pytest pytest-playwright pytest-html slack-sdk --quiet

echo ""
echo "[2/3] Playwright 브라우저 설치 중..."
playwright install chromium

echo ""
echo "[3/3] 디렉토리 확인..."
mkdir -p tests/sessions test_results/html test_results/traces test_results/screenshots

echo ""
echo "=============================="
echo " 설치 완료!"
echo "=============================="
echo ""
echo "다음 단계:"
echo "  1. .env 파일에 OKTA_EMAIL, OKTA_PASSWORD 입력"
echo "  2. 세션 갱신: python tests/session_manager.py self_pos"
echo "  3. 테스트 실행: pytest tests/self_pos/test_setup.py -v"
echo ""
