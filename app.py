#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, redirect
import os
import sys
import shutil
import base64
import subprocess
import threading
import uuid
import requests as http_requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


@app.route('/')
def hub():
    return render_template('hub.html')


@app.route('/api/whoami')
def api_whoami():
    import socket
    return jsonify({'user': socket.gethostname()})


@app.route('/api/create-dashboard', methods=['POST'])
def api_create_dashboard():
    data = request.get_json()
    epic_key = (data.get('epic_key') or '').strip().upper()
    if not epic_key:
        return jsonify({'error': '에픽 키를 입력해주세요.'}), 400

    jira_email    = os.environ.get('JIRA_EMAIL', '')
    jira_token    = os.environ.get('JIRA_TOKEN', '')
    jira_base_url = os.environ.get('JIRA_BASE_URL', 'https://musinsa-oneteam.atlassian.net')
    bug_project   = os.environ.get('BUG_PROJECT', 'OFFSYSM')

    if not jira_email or not jira_token:
        return jsonify({'error': '.env 파일에 JIRA_EMAIL과 JIRA_TOKEN을 설정해주세요.'}), 500

    credentials = base64.b64encode(f"{jira_email}:{jira_token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    log_lines = []

    def log(msg):
        log_lines.append(msg)

    # ── 에픽 조회 ──
    log(f"[1/4] 에픽 정보 조회 중: {epic_key}")
    r = http_requests.get(f"{jira_base_url}/rest/api/3/issue/{epic_key}", headers=headers)
    if not r.ok:
        return jsonify({'error': f"에픽 조회 실패 ({r.status_code}): 티켓 번호를 확인해 주세요."})
    epic_title = r.json()["fields"]["summary"]
    log(f"  → {epic_key}: {epic_title}")

    # ── 필터 생성 ──
    base_jql = (
        f"created >= -90d AND project = {bug_project} "
        f"AND type = Bug AND parent = '{epic_key}'"
    )
    all_status = (
        'status IN (SUGGESTED, "Ready To Test", "in QA", '
        '"In Progress", "In Developer Test", "In Code Review", HOLD, Done)'
    )
    filter_specs = [
        (f"[{epic_key}] 버그 전체",        f"{base_jql} AND {all_status} ORDER BY created DESC"),
        (f"[{epic_key}] 버그 오픈",        f"{base_jql} AND status = SUGGESTED ORDER BY created DESC"),
        (f"[{epic_key}] 버그 IN PROGRESS", f"{base_jql} AND status IN ('In Progress', 'In Developer Test', 'In Code Review') ORDER BY created DESC"),
        (f"[{epic_key}] 버그 IN QA",       f"{base_jql} AND status IN ('in QA', 'Ready To Test') ORDER BY created DESC"),
        (f"[{epic_key}] 버그 CLOSED",      f"{base_jql} AND status = Done ORDER BY created DESC"),
        (f"[{epic_key}] 버그 심각도순",     f"{base_jql} AND {all_status} ORDER BY priority ASC, created DESC"),
    ]

    log(f"\n[2/4] 필터 생성 중... (총 {len(filter_specs)}개)")
    filters = {}
    label_keys = ["전체", "오픈", "IN PROGRESS", "IN QA", "CLOSED", "심각도순"]

    def create_filter(name, jql):
        r = http_requests.post(f"{jira_base_url}/rest/api/3/filter", headers=headers, json={
            "name": name, "jql": jql,
            "sharePermissions": [{"type": "authenticated"}],
            "editPermissions": [
                {"type": "user", "user": {"accountId": "712020:06ee49e6-6adf-4213-a0d5-f94a5597be03"}},
                {"type": "project", "project": {"id": "10262"}}
            ]
        })
        if r.ok:
            return r.json()["id"]
        if "같은 이름" in r.text or "already exists" in r.text.lower():
            s = http_requests.get(f"{jira_base_url}/rest/api/3/filter/my?maxResults=100", headers=headers)
            if s.ok:
                for f in s.json():
                    if f["name"] == name:
                        return f["id"]
        return None

    for (name, jql), key in zip(filter_specs, label_keys):
        fid = create_filter(name, jql)
        if not fid:
            return jsonify({'error': f"필터 생성 실패: {name}"})
        filters[key] = fid
        log(f"  ✓ {name}  (ID: {fid})")

    # ── 대시보드 생성 ──
    log(f"\n[3/4] 대시보드 생성 중...")
    r = http_requests.post(f"{jira_base_url}/rest/api/3/dashboard", headers=headers, json={
        "name": epic_title,
        "sharePermissions": [{"type": "authenticated"}],
        "editPermissions": [{"type": "authenticated"}]
    })
    if not r.ok:
        return jsonify({'error': f"대시보드 생성 실패: {r.text[:120]}"})
    dashboard_id = r.json()["id"]
    log(f"  ✓ {epic_title}  (ID: {dashboard_id})")

    # ── 가젯 추가 ──
    URI_FILTER = "rest/gadgets/1.0/g/com.atlassian.jira.gadgets:filter-results-gadget/gadgets/filter-results-gadget.xml"
    URI_2D     = "rest/gadgets/1.0/g/com.atlassian.jira.gadgets:two-dimensional-stats-gadget/gadgets/two-dimensional-stats-gadget.xml"
    URI_CR     = "rest/gadgets/1.0/g/com.atlassian.jira.gadgets:created-vs-resolved-issues-chart-gadget/gadgets/createdvsresolved-gadget.xml"
    URI_CAL    = "rest/gadgets/1.0/g/com.atlassian.jira.ext.calendar:issuescalendar-gadget/templates/plugins/jira/portlets/calendar/gadget/calendar-gadget.xml"

    fid_all   = filters["전체"]
    col_names = "issuetype|issuekey|summary|심각도[Dropdown]|assignee|status"
    prefix    = epic_title[:35]

    log(f"\n[4/4] 가젯 추가 중...")

    gadgets = [
        (URI_CR,     0, 0, "blue", "생성 대비 해결됨 차트", {
            "isConfigured": "true", "isPopup": "false", "refresh": "15",
            "periodName": "daily", "showUnresolvedTrend": "true",
            "projectOrFilterId": "", "type": "filter",
            "versionLabel": "none", "isCumulative": "false",
            "name": prefix, "daysprevious": "30",
            "id": fid_all, "operation": "cumulative"
        }),
        (URI_2D,     0, 1, "blue", "버그 오픈 종류 (기능/디자인)", {
            "isConfigured": "true", "isPopup": "false", "refresh": "15",
            "filterId": f"filter-{filters['오픈']}",
            "xstattype": "customfield_10275", "ystattype": "labels",
            "sortDirection": "asc", "sortBy": "natural",
            "more": "false", "numberToShow": "5"
        }),
        (URI_CAL,    0, 2, "blue", "일별 버그 등록 추이 캘린더", {
            "isConfigured": "true", "refresh": "15",
            "numOfIssueIcons": "10", "dateFieldName": "created",
            "name": prefix, "projectOrFilterId": f"filter-{fid_all}",
            "id": fid_all, "type": "filter", "displayVersions": "false"
        }),
        (URI_2D,     1, 0, "blue", "심각도순 버그 취합", {
            "isConfigured": "true", "isPopup": "false", "refresh": "15",
            "filterId": f"filter-{fid_all}",
            "xstattype": "statuses", "ystattype": "customfield_10275",
            "sortDirection": "asc", "sortBy": "natural",
            "more": "false", "numberToShow": "5"
        }),
        (URI_2D,     1, 1, "blue", "담당자별 버그 취합", {
            "isConfigured": "true", "isPopup": "false", "refresh": "15",
            "filterId": f"filter-{fid_all}",
            "xstattype": "statuses", "ystattype": "assignees",
            "sortDirection": "asc", "sortBy": "natural",
            "more": "false", "numberToShow": "20"
        }),
        (URI_FILTER, 1, 2, "blue", "버그 오픈 리스트", {
            "isConfigured": "true", "isPopup": "false", "refresh": "15",
            "filterId": filters["오픈"], "columnNames": col_names, "num": "20"
        }),
        (URI_FILTER, 1, 3, "blue", "버그 IN PROGRESS", {
            "isConfigured": "true", "isPopup": "false", "refresh": "15",
            "filterId": filters["IN PROGRESS"], "columnNames": col_names, "num": "20"
        }),
        (URI_FILTER, 1, 4, "blue", "버그 IN QA", {
            "isConfigured": "true", "isPopup": "false", "refresh": "15",
            "filterId": filters["IN QA"], "columnNames": col_names, "num": "20"
        }),
        (URI_FILTER, 1, 5, "green", "버그 CLOSED", {
            "isConfigured": "true", "isPopup": "false", "refresh": "15",
            "filterId": filters["CLOSED"], "columnNames": col_names, "num": "20"
        }),
    ]

    def add_gadget(uri, col, row, color, label, config):
        r = http_requests.post(
            f"{jira_base_url}/rest/api/3/dashboard/{dashboard_id}/gadget",
            headers=headers,
            json={"uri": uri, "position": {"column": col, "row": row}, "color": color}
        )
        if not r.ok:
            log(f"  ⚠ {label} 추가 실패: {r.text[:80]}")
            return
        gid = r.json()["id"]
        http_requests.put(
            f"{jira_base_url}/rest/api/3/dashboard/{dashboard_id}/gadget/{gid}",
            headers=headers, json={"title": label, "color": color}
        )
        r2 = http_requests.put(
            f"{jira_base_url}/rest/api/3/dashboard/{dashboard_id}/items/{gid}/properties/config",
            headers=headers, json=config
        )
        if r2.ok:
            log(f"  ✓ {label}")
        else:
            log(f"  ⚠ {label} config 실패: {r2.text[:80]}")

    for args in gadgets:
        add_gadget(*args)

    url = f"{jira_base_url}/jira/dashboards/{dashboard_id}"
    log(f"\n✅ 완료!")
    return jsonify({'log': '\n'.join(log_lines), 'url': url})


# ── UI 자동화 실행 상태 저장 ──────────────────────────────────
_ui_runs = {}  # {run_id: {"status": "running"|"done"|"error", ...}}
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route('/api/ui-test/run', methods=['POST'])
def api_ui_test_run():
    data         = request.get_json()
    service      = data.get('service', 'self_pos')
    api_type     = data.get('api_type', 'mpos')
    fe_type      = data.get('fe_type', 'MPOS')
    tests        = data.get('tests', [])
    triggered_by = data.get('triggered_by', '')
    headless     = data.get('headless', True)

    if service not in ('self_pos', 'mpos', 'pdp'):
        return jsonify({'error': '알 수 없는 서비스입니다.'}), 400

    run_id     = uuid.uuid4().hex[:8]
    report_dir = os.path.join(ROOT_DIR, 'test_results', 'html', run_id)
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, 'report.html')

    allure_results_dir = os.path.join(ROOT_DIR, 'test_results', 'allure-results', run_id)
    allure_report_dir  = os.path.join(ROOT_DIR, 'test_results', 'allure-report',  run_id)
    os.makedirs(allure_results_dir, exist_ok=True)

    test_path = os.path.join('tests', service)
    if tests:
        test_path = ' '.join(
            os.path.join('tests', service, t) for t in tests
        )

    _ui_runs[run_id] = {
        'status':              'running',
        'service':             service,
        'api_type':            api_type,
        'fe_type':             fe_type,
        'headless':            headless,
        'report_path':         report_path,
        'allure_results_dir':  allure_results_dir,
        'allure_report_dir':   allure_report_dir,
        'triggered_by':        triggered_by,
        'result':              None
    }

    def _run():
        env = os.environ.copy()
        env['UI_TEST_API_TYPE'] = api_type
        env['UI_TEST_FE_TYPE']  = fe_type
        env['UI_TEST_HEADLESS'] = 'true' if headless else 'false'

        cmd = [
            sys.executable, '-m', 'pytest',
            os.path.join('tests', service),
            f'--html={report_path}',
            '--self-contained-html',
            f'--alluredir={allure_results_dir}',
            '-v'
        ]

        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            env=env, cwd=ROOT_DIR
        )

        # allure 리포트 생성: CLI 우선, 없으면 allure-combine 폴백
        os.makedirs(allure_report_dir, exist_ok=True)
        allure_bin = shutil.which('allure')
        if allure_bin:
            try:
                subprocess.run(
                    [allure_bin, 'generate', allure_results_dir,
                     '-o', allure_report_dir, '--clean'],
                    capture_output=True, timeout=60, cwd=ROOT_DIR
                )
            except Exception:
                allure_bin = None  # CLI 실패 → combine 폴백

        if not allure_bin:
            try:
                from allure_combine import combine_allure
                combine_allure(allure_results_dir, dest_folder=allure_report_dir,
                               auto_create_folders=True)
            except Exception:
                pass

        _ui_runs[run_id]['status'] = 'done' if proc.returncode in (0, 1) else 'error'
        _ui_runs[run_id]['result'] = {
            'returncode': proc.returncode,
            'stdout':     proc.stdout[-4000:],
            'stderr':     proc.stderr[-1000:]
        }

        try:
            from tests.slack_notify import send_slack_notification
            send_slack_notification(
                service=service, api_type=api_type, fe_type=fe_type,
                report_path=report_path, run_id=run_id,
                hub_base_url='http://localhost:5001',
                stdout=proc.stdout,
                triggered_by=_ui_runs[run_id].get('triggered_by', '')
            )
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({'run_id': run_id})


@app.route('/api/ui-test/status/<run_id>')
def api_ui_test_status(run_id):
    run = _ui_runs.get(run_id)
    if not run:
        return jsonify({'error': 'run_id를 찾을 수 없습니다.'}), 404
    return jsonify({'status': run['status'], 'result': run.get('result')})


@app.route('/api/ui-test/session/refresh', methods=['POST'])
def api_ui_test_session_refresh():
    data    = request.get_json()
    service = data.get('service', 'self_pos')
    if service not in ('self_pos', 'mpos', 'pdp'):
        return jsonify({'error': '알 수 없는 서비스입니다.'}), 400

    subprocess.Popen(
        [sys.executable, 'tests/session_manager.py', service],
        cwd=ROOT_DIR
    )
    return jsonify({'message': f'{service} 세션 갱신 브라우저가 열렸습니다.'})


@app.route('/api/ui-test/report/<run_id>')
def api_ui_test_report(run_id):
    run = _ui_runs.get(run_id)
    if not run:
        return jsonify({'error': 'run_id를 찾을 수 없습니다.'}), 404

    # allure 리포트가 있으면 allure 우선 서빙 (CLI: index.html / combine: complete.html)
    allure_dir = run.get('allure_report_dir', '')
    for allure_file in ('index.html', 'complete.html'):
        if os.path.exists(os.path.join(allure_dir, allure_file)):
            return redirect(f'/api/ui-test/allure/{run_id}/?f={allure_file}')

    # fallback: pytest-html
    path = run.get('report_path', '')
    if not os.path.exists(path):
        return jsonify({'error': '리포트 파일이 아직 없습니다.'}), 404
    return send_file(path, mimetype='text/html')


@app.route('/api/ui-test/allure/<run_id>/')
@app.route('/api/ui-test/allure/<run_id>/<path:filename>')
def api_ui_test_allure(run_id, filename=None):
    run = _ui_runs.get(run_id)
    if not run:
        return jsonify({'error': 'run_id를 찾을 수 없습니다.'}), 404
    allure_dir = run.get('allure_report_dir', '')
    if not filename:
        # f 쿼리 파라미터로 파일명 지정 (index.html or complete.html)
        filename = request.args.get('f', 'index.html')
    if not allure_dir or not os.path.exists(os.path.join(allure_dir, filename)):
        return jsonify({'error': 'Allure 리포트가 없습니다.'}), 404
    return send_from_directory(allure_dir, filename)


@app.route('/api/ui-test/trace-file/<path:filename>')
def api_ui_test_trace_file(filename):
    """
    trace.playwright.dev에서 직접 열 수 있도록 CORS 헤더 포함 trace zip 서빙.
    URL: https://trace.playwright.dev/?trace=http://localhost:5001/api/ui-test/trace-file/<filename>
    """
    traces_dir = os.path.join(ROOT_DIR, 'test_results', 'traces')
    filepath   = os.path.join(traces_dir, filename)
    # 경로 탈출 방지
    if not os.path.abspath(filepath).startswith(os.path.abspath(traces_dir)):
        return jsonify({'error': '잘못된 경로입니다.'}), 400
    if not os.path.exists(filepath):
        return jsonify({'error': 'Trace 파일이 없습니다.'}), 404
    resp = send_file(filepath, mimetype='application/zip')
    resp.headers['Access-Control-Allow-Origin']  = 'https://trace.playwright.dev'
    resp.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    return resp


@app.route('/api/ui-test/trace/<run_id>')
def api_ui_test_trace(run_id):
    run = _ui_runs.get(run_id)
    if not run:
        return jsonify({'error': 'run_id를 찾을 수 없습니다.'}), 404
    service    = run.get('service', 'self_pos')
    traces_dir = os.path.join(ROOT_DIR, 'test_results', 'traces')
    if not os.path.exists(traces_dir):
        return jsonify({'error': 'Trace 파일이 없습니다.'}), 404
    files = sorted(
        [f for f in os.listdir(traces_dir) if f.startswith(f"{service}_") and f.endswith('.zip')],
        reverse=True
    )
    if not files:
        return jsonify({'error': 'Trace 파일이 없습니다.'}), 404
    return send_file(
        os.path.join(traces_dir, files[0]),
        as_attachment=True,
        download_name=f'trace_{run_id}.zip'
    )


if __name__ == '__main__':
    app.run(debug=True, port=5001)
