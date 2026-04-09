#!/bin/bash

cd "$(dirname "$0")"
BASE_DIR="$(pwd)"

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

# ══════════════════════════════════════════════════════════
# [1] TC 생성기 설정
# ══════════════════════════════════════════════════════════
TC_DIR="$BASE_DIR/tc_generator"
TC_REPO="https://github.com/namseok-ko/TestCase_Generator.git"

echo ""
echo "[TC 생성기] 최신 버전 확인 중..."

if [ ! -d "$TC_DIR/.git" ]; then
    echo "  처음 실행 — TC 생성기 다운로드 중..."
    git clone "$TC_REPO" "$TC_DIR" -q
    echo "  다운로드 완료!"
else
    git -C "$TC_DIR" fetch origin main -q 2>/dev/null
    LOCAL=$(git -C "$TC_DIR" rev-parse HEAD 2>/dev/null)
    REMOTE=$(git -C "$TC_DIR" rev-parse origin/main 2>/dev/null)
    if [ "$LOCAL" = "$REMOTE" ]; then
        echo "  이미 최신 버전입니다."
    else
        echo "  새 버전 업데이트 중..."
        git -C "$TC_DIR" reset --hard origin/main -q
        echo "  업데이트 완료!"
    fi
fi

# TC 생성기 가상환경 및 의존성
if [ ! -d "$TC_DIR/venv" ]; then
    echo "  가상환경 생성 중..."
    "$PYTHON_BIN" -m venv "$TC_DIR/venv"
fi

TC_PIP="$TC_DIR/venv/bin/pip"
TC_PYTHON="$TC_DIR/venv/bin/python3"

INSTALL_OUTPUT=$("$TC_PIP" install -r "$TC_DIR/requirements.txt" 2>&1)
NEW_PACKAGES=$(echo "$INSTALL_OUTPUT" | grep -v "already satisfied" | grep -v "^$" | grep -v "notice" | grep -v "Requirement")
[ -n "$NEW_PACKAGES" ] && echo "  패키지 설치 중..."

# TC 생성기 .env 복사 (없으면)
if [ ! -f "$TC_DIR/.env" ] && [ -f "$TC_DIR/.env.example" ]; then
    cp "$TC_DIR/.env.example" "$TC_DIR/.env"
fi

# TC 생성기 서버 실행 (백그라운드, 포트 5000)
echo "  서버 시작 중... (포트 5000)"
cd "$TC_DIR"
"$TC_PYTHON" app.py &
TC_PID=$!
cd "$BASE_DIR"

# ══════════════════════════════════════════════════════════
# [2] QA Hub 설정
# ══════════════════════════════════════════════════════════
echo ""
echo "[QA Hub] 시작 중..."

if [ ! -d "$BASE_DIR/venv" ]; then
    echo "  가상환경 생성 중..."
    "$PYTHON_BIN" -m venv "$BASE_DIR/venv"
fi

HUB_PIP="$BASE_DIR/venv/bin/pip"
HUB_PYTHON="$BASE_DIR/venv/bin/python3"

INSTALL_OUTPUT=$("$HUB_PIP" install -r "$BASE_DIR/requirements.txt" 2>&1)
NEW_PACKAGES=$(echo "$INSTALL_OUTPUT" | grep -v "already satisfied" | grep -v "^$" | grep -v "notice" | grep -v "Requirement")
[ -n "$NEW_PACKAGES" ] && echo "  패키지 설치 중..."

echo "  서버 시작 중... (포트 5001)"

# ══════════════════════════════════════════════════════════
echo ""
echo "=============================="
echo "  TC 생성기: http://localhost:5000"
echo "  QA Hub   : http://localhost:5001"
echo "  종료     : 이 창에서 Ctrl+C"
echo "=============================="
echo ""

# 브라우저는 QA Hub로 열기
sleep 2 && open http://localhost:5001 &

# QA Hub 서버 실행 (포그라운드)
"$HUB_PYTHON" "$BASE_DIR/app.py"

# QA Hub 종료 시 TC 생성기도 함께 종료
kill $TC_PID 2>/dev/null
