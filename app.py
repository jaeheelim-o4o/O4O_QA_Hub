#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
import os
import base64
import requests as http_requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


@app.route('/')
def hub():
    return render_template('hub.html')


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


if __name__ == '__main__':
    app.run(debug=True, port=5001)
