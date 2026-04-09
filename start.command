#!/bin/bash

cd "$(dirname "$0")"

echo "=============================="
echo "  PBO QA Hub 시작 중..."
echo "=============================="

# ── .env 확인 ──────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "  ⚠️  .env 파일이 생성됐습니다."
    echo "  아래 파일에 본인의 Jira 정보를 입력해주세요:"
    echo "  $(pwd)/.env"
    echo ""
    open .env 2>/dev/null
    read -p "설정 완료 후 엔터를 누르세요..."
fi

# ── Python 감지 ────────────────────────────────────────────
PYTHON_BIN=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$cmd" &>/dev/null; then
        MAJOR=$("$cmd" -c "import sys; print(sys.version_info[0])" 2>/dev/null)
        MINOR=$("$cmd" -c "import sys; print(sys.version_info[1])" 2>/dev/null)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ] 2>/dev/null; then
            PYTHON_BIN="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "❌ Python 3.9 이상이 필요합니다."
    read -p "엔터를 누르면 종료됩니다..."
    exit 1
fi

# ── 가상환경 ───────────────────────────────────────────────
if [ ! -d "venv" ]; then
    echo "가상환경 생성 중... ($PYTHON_BIN)"
    "$PYTHON_BIN" -m venv venv
fi

VENV_PYTHON="$(pwd)/venv/bin/python3"
PIP="$(pwd)/venv/bin/pip"

# ── 의존성 설치 ────────────────────────────────────────────
INSTALL_OUTPUT=$("$PIP" install -r requirements.txt 2>&1)
NEW_PACKAGES=$(echo "$INSTALL_OUTPUT" | grep -v "already satisfied" | grep -v "^$" | grep -v "notice" | grep -v "Requirement")
if [ -n "$NEW_PACKAGES" ]; then
    echo "패키지 설치 중..."
fi

# ── 서버 실행 ──────────────────────────────────────────────
echo ""
echo "  서버 시작: http://localhost:5001"
echo "  종료: 이 창에서 Ctrl+C"
echo ""

sleep 1.5 && open http://localhost:5001 &

"$VENV_PYTHON" app.py
