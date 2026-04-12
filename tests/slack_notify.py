"""
테스트 결과 Slack 알림 유틸리티
pytest 종료 후 호출하거나 QA Hub 백엔드에서 직접 호출
"""
import os
import re
from datetime import datetime
from slack_sdk.webhook import WebhookClient
from dotenv import load_dotenv

load_dotenv()

STATUS_EMOJI = {
    "PASSED":  "✅",
    "FAILED":  "❌",
    "ERROR":   "💥",
    "SKIPPED": "⏭️",
    "XFAILED": "⚠️",
    "XPASSED": "⚠️",
}


def parse_pytest_stdout(stdout: str) -> list[dict]:
    """
    pytest verbose stdout에서 개별 테스트케이스 결과 파싱.
    예: tests/self_pos/test_setup.py::test_landing PASSED [ 25%]
    """
    tests = []
    pattern = re.compile(
        r"(tests/\S+::[\w\[\].,@/ -]+?)\s+"
        r"(PASSED|FAILED|ERROR|SKIPPED|XFAILED|XPASSED)"
        r"(?:\s+\[[\s\d]+%\])?"
    )
    seen = set()
    for line in stdout.splitlines():
        m = pattern.search(line)
        if m:
            full_path, status = m.group(1).strip(), m.group(2)
            if full_path in seen:
                continue
            seen.add(full_path)
            # "tests/self_pos/test_setup.py::test_name" → "test_setup::test_name"
            parts = full_path.split("::")
            module = parts[-2].replace(".py", "").split("/")[-1] if len(parts) >= 2 else ""
            test_name = parts[-1]
            label = f"{module}::{test_name}" if module else test_name
            tests.append({"label": label, "status": status})
    return tests


def parse_html_report(report_path: str) -> dict:
    """pytest-html 리포트에서 요약 수치 파싱"""
    result = {"passed": 0, "failed": 0, "error": 0, "total": 0}
    if not os.path.exists(report_path):
        return result

    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    passed = re.search(r"(\d+) passed", content)
    failed = re.search(r"(\d+) failed", content)
    error  = re.search(r"(\d+) error",  content)

    result["passed"] = int(passed.group(1)) if passed else 0
    result["failed"] = int(failed.group(1)) if failed else 0
    result["error"]  = int(error.group(1))  if error  else 0
    result["total"]  = result["passed"] + result["failed"] + result["error"]
    return result


def _build_blocks(
    service_label: str,
    api_type: str,
    fe_type: str | None,
    passed: int,
    failed: int,
    total: int,
    now: str,
    tests: list[dict],
    report_url: str,
    report_file_path: str = "",
    triggered_by: str = "",
) -> list[dict]:
    """Slack Block Kit 블록 생성"""
    overall_ok = failed == 0
    status_emoji = "✅" if overall_ok else "❌"
    result_text = f"✅ {passed}건 통과  /  ❌ {failed}건 실패  /  전체 {total}건"

    env_parts = [f"API: `{api_type}`"]
    if fe_type:
        env_parts.append(f"FE: `{fe_type}`")
    env_text = "  |  ".join(env_parts)

    # ── 헤더 ──────────────────────────────────────────────────
    summary_fields = [
        {"type": "mrkdwn", "text": f"*환경*\n{env_text}"},
        {"type": "mrkdwn", "text": f"*결과*\n{result_text}"},
        {"type": "mrkdwn", "text": f"*완료 시각*\n{now}"},
    ]
    if triggered_by:
        summary_fields.append({"type": "mrkdwn", "text": f"*실행자*\n{triggered_by}"})

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{status_emoji} [O4O QA] {service_label} 회귀 테스트 완료",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": summary_fields,
        },
        {"type": "divider"},
    ]

    # ── 개별 테스트케이스 ──────────────────────────────────────
    if tests:
        lines = []
        for t in tests:
            emoji = STATUS_EMOJI.get(t["status"], "❓")
            lines.append(f"{emoji}  `{t['label']}`")

        # Slack text 필드 최대 3000자 제한 — 긴 경우 잘라냄
        tc_text = "\n".join(lines)
        if len(tc_text) > 2900:
            tc_text = tc_text[:2900] + "\n…(생략)"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*테스트케이스 상세*\n{tc_text}",
            },
        })
        blocks.append({"type": "divider"})

    # ── 리포트 링크 ────────────────────────────────────────────
    if report_url:
        # QA Hub 서버 경유 버튼
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📄 HTML 리포트 보기", "emoji": True},
                    "url": report_url,
                    "style": "primary" if overall_ok else "danger",
                }
            ],
        })
    elif report_file_path:
        # 직접 실행 시 로컬 파일 경로 표시
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📄 *리포트 파일*: `{report_file_path}`",
                }
            ],
        })

    return blocks


def send_slack_notification(
    service: str,
    api_type: str,
    fe_type: str | None = None,
    report_path: str | None = None,
    run_id: str | None = None,
    hub_base_url: str = "http://localhost:5001",
    stdout: str = "",
    triggered_by: str = "",
):
    """Slack으로 테스트 결과 알림 전송 (Block Kit)"""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL이 설정되지 않아 알림을 건너뜁니다.")
        return

    report_path = report_path or "test_results/html/report.html"
    stats = parse_html_report(report_path)

    # stdout이 있으면 거기서 개별 케이스 파싱, 없으면 빈 리스트
    tests = parse_pytest_stdout(stdout) if stdout else []

    # stats에서 숫자가 없으면 tests 리스트로 보정
    if stats["total"] == 0 and tests:
        stats["passed"] = sum(1 for t in tests if t["status"] == "PASSED")
        stats["failed"] = sum(1 for t in tests if t["status"] in ("FAILED", "ERROR"))
        stats["total"]  = len(tests)

    now           = datetime.now().strftime("%Y-%m-%d %H:%M")
    passed        = stats["passed"]
    failed        = stats["failed"] + stats["error"]
    total         = stats["total"]
    service_label = {"self_pos": "Self-POS", "mpos": "mPOS", "pdp": "PDP"}.get(service, service)
    report_url       = f"{hub_base_url}/api/ui-test/report/{run_id}" if run_id else ""
    report_file_path = os.path.abspath(report_path) if not run_id and os.path.exists(report_path) else ""

    blocks = _build_blocks(
        service_label=service_label,
        api_type=api_type,
        fe_type=fe_type,
        passed=passed,
        failed=failed,
        total=total,
        now=now,
        tests=tests,
        report_url=report_url,
        report_file_path=report_file_path,
        triggered_by=triggered_by,
    )

    # fallback text (알림 미리보기용)
    status_emoji = "✅" if failed == 0 else "❌"
    fallback = f"{status_emoji} [{service_label}] 통과 {passed} / 실패 {failed} / 전체 {total}"

    try:
        client = WebhookClient(webhook_url)
        response = client.send(text=fallback, blocks=blocks)
        if response.status_code == 200:
            print("✅ Slack 알림 전송 완료")
        else:
            print(f"⚠ Slack 알림 실패: {response.status_code} {response.body}")
    except Exception as e:
        print(f"⚠ Slack 알림 중 오류: {e}")


if __name__ == "__main__":
    # 테스트용 직접 실행 — 실제 report.html이 있어야 함
    sample_stdout = """\
tests/self_pos/test_setup.py::test_landing_after_env_setup PASSED [ 25%]
tests/self_pos/test_setup.py::test_api_type_switch[mpos1] PASSED [ 50%]
tests/self_pos/test_setup.py::test_api_type_switch[mpos2] PASSED [ 75%]
tests/self_pos/test_setup.py::test_api_type_switch[mpos3] PASSED [100%]
"""
    send_slack_notification(
        service="self_pos",
        api_type="mpos",
        fe_type="MPOS",
        triggered_by="테스트 실행",
        report_path="test_results/html/report.html",
        # run_id 없음 → 리포트 링크 미포함 (직접 실행 테스트용)
        stdout=sample_stdout,
    )
