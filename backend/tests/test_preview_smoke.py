import importlib.util
from pathlib import Path

import pytest

module_spec = importlib.util.spec_from_file_location('check_preview', Path(__file__).resolve().parents[2] / 'scripts/check-preview.py')
smoke = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(smoke)


@pytest.mark.parametrize('url', ['https://attacker.example', 'http://job-shield-git-tung-sntug.vercel.app', 'https://job-shield-x-sntug.vercel.app@attacker.example', 'https://job-shield-x-sntug.vercel.app/?token=secret'])
def test_smoke_refuses_unexpected_destinations(url):
    with pytest.raises(ValueError):
        smoke.validate_url(url)


def fake_api(*, wrong_commit=False, old_schema=False, missing_provenance=False):
    calls = []
    def request(base, path, method='GET', payload=None, headers=None, timeout=30):
        calls.append((path, method, headers))
        response_headers = {'x-commit-sha': 'oldcode' if wrong_commit else 'abcdef0', 'cache-control': 'no-store', 'x-request-id': 'trace'}
        if path == '/ready':
            return 200, {'status': 'ready', 'database': 'connected', 'schema': 'outdated' if old_schema else 'current'}, response_headers
        if path == '/api/v1/verifications':
            source = {} if missing_provenance else {'url': 'https://fptsoftware.com/contact-us', 'verified_at': '2026-10-26', 'source_revision': 1, 'evidence_excerpt_vi': 'Public source'}
            return 200, {'verification_label_vi': 'Khớp nguồn đã xác minh', 'matched_sources': [source], 'field_checks': []}, response_headers
        if path == '/api/v1/analyses':
            return 201, {'id': 'analysis-id', 'guest_session_token': 'guest-token', 'risk_label_vi': 'Không đủ thông tin'}, response_headers
        assert headers == {'X-Guest-Session-Token': 'guest-token'}
        return 200, {'id': 'analysis-id', 'risk_label_vi': 'Không đủ thông tin'}, response_headers
    return request, calls


def test_smoke_checks_verification_analysis_and_guest_read():
    request, calls = fake_api()
    smoke.run_checks('https://job-shield-x-sntug.vercel.app', 'abcdef0' + '1' * 33, request=request)
    assert [method for _, method, _ in calls] == ['GET', 'POST', 'POST', 'GET']


@pytest.mark.parametrize('mutation', ['wrong_commit', 'old_schema', 'missing_provenance'])
def test_smoke_cannot_report_green_for_stale_or_incomplete_preview(mutation):
    request, _ = fake_api(**{mutation: True})
    with pytest.raises(ValueError):
        smoke.run_checks('https://job-shield-x-sntug.vercel.app', 'abcdef0' + '1' * 33, request=request)


def test_deployment_event_only_accepts_current_same_repo_pr(tmp_path, monkeypatch):
    import json
    sha = 'abcdef0' + '1' * 33
    event = {'repository': {'full_name': 'Sntug/JobShield'},
             'deployment': {'sha': sha, 'environment': 'Preview – job-shield', 'creator': {'login': 'vercel[bot]'}},
             'deployment_status': {'state': 'success', 'creator': {'login': 'vercel[bot]'}, 'environment_url': 'https://job-shield-x-sntug.vercel.app'}}
    path = tmp_path / 'event.json'
    path.write_text(json.dumps(event))
    monkeypatch.setenv('GITHUB_REPOSITORY', 'Sntug/JobShield')
    monkeypatch.setenv('GITHUB_TOKEN', 'test-token')
    def pull_requests(base, path, **kwargs):
        assert base == 'https://api.github.com'
        return 200, [{'state': 'open', 'head': {'sha': sha, 'repo': {'full_name': 'Sntug/JobShield'}}}], {}
    monkeypatch.setattr(smoke, 'request_json', pull_requests)
    assert smoke.deployment_event(path) == ('https://job-shield-x-sntug.vercel.app', sha)
    event['deployment']['environment'] = 'Production'
    path.write_text(json.dumps(event))
    with pytest.raises(ValueError):
        smoke.deployment_event(path)
    event['deployment']['environment'] = 'Preview'
    path.write_text(json.dumps(event))
    monkeypatch.setattr(smoke, 'request_json', lambda *args, **kwargs: (200, [{'state': 'open', 'head': {'sha': sha, 'repo': {'full_name': 'attacker/fork'}}}], {}))
    with pytest.raises(ValueError):
        smoke.deployment_event(path)


@pytest.mark.parametrize('base,expected', [
    ('https://job-shield-x-sntug.vercel.app', 'fixture-bypass-token'),
    ('https://api.github.com', None),
    ('https://attacker.example', None),
    ('http://127.0.0.1:3001', None),
])
def test_bypass_secret_is_only_sent_to_approved_https_preview(monkeypatch, base, expected):
    from io import BytesIO
    from types import SimpleNamespace
    captured = []
    def open_request(request, timeout):
        captured.append(dict((key.lower(), value) for key, value in request.header_items()))
        response = BytesIO(b'{}')
        response.status = 200
        response.headers = {}
        return response
    monkeypatch.setenv('VERCEL_AUTOMATION_BYPASS_SECRET', 'fixture-bypass-token')
    monkeypatch.setattr(smoke, 'build_opener', lambda *args: SimpleNamespace(open=open_request))
    smoke.request_json(base, '/ready')
    assert captured[0].get('x-vercel-protection-bypass') == expected


def test_missing_automation_access_fails_without_waiting_300_seconds(monkeypatch):
    import sys
    monkeypatch.setattr(sys, 'argv', ['check-preview.py', '--url', 'https://job-shield-x-sntug.vercel.app', '--sha', 'a' * 40])
    def denied(*args):
        raise smoke.PreviewAuthenticationRequired('Configure VERCEL_AUTOMATION_BYPASS_SECRET for protected Preview access.')
    monkeypatch.setattr(smoke, 'ready', denied)
    monkeypatch.setattr(smoke.time, 'sleep', lambda *args: pytest.fail('Authentication errors must not be retried'))
    with pytest.raises(SystemExit, match='VERCEL_AUTOMATION_BYPASS_SECRET'):
        smoke.main()


def test_invalid_secret_is_not_echoed_in_errors(monkeypatch):
    monkeypatch.setenv('VERCEL_AUTOMATION_BYPASS_SECRET', 'fixture-secret-with-newline' + chr(10))
    with pytest.raises(ValueError) as error:
        smoke.request_json('https://job-shield-x-sntug.vercel.app', '/ready')
    assert 'fixture-secret-with-newline' not in str(error.value)
