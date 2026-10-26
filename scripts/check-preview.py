"""Credential-free functional smoke through the frontend's same-origin API proxy."""

import argparse
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_url(value, *, allow_local=False):
    parts = urlsplit(value)
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ('', '/'):
        raise ValueError('Unexpected Preview URL.')
    if allow_local and parts.scheme == 'http' and parts.hostname in {'127.0.0.1', 'localhost'} and parts.port:
        return value.rstrip('/')
    if parts.scheme != 'https' or parts.port or not re.fullmatch(r'job-shield-[a-z0-9-]+-sntug\.vercel\.app', parts.hostname or ''):
        raise ValueError('Unexpected Preview host.')
    return value.rstrip('/')


def request_json(base, path, method='GET', payload=None, headers=None, timeout=30):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(base + path, data=data, method=method, headers={
        'Accept': 'application/json', 'Content-Type': 'application/json',
        'User-Agent': 'JobShield-Preview-Smoke', **(headers or {}),
    })
    try:
        response = build_opener(NoRedirect).open(req, timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        body = response.read(1024 * 1024 + 1)
        if len(body) > 1024 * 1024:
            raise ValueError('Oversized Preview response.')
        try:
            parsed = json.loads(body)
        except (ValueError, UnicodeError):
            raise ValueError('Expected JSON from Preview; check proxy or deployment protection.') from None
        return response.status, parsed, dict((key.lower(), value) for key, value in response.headers.items())


def assert_response(result, sha, *, statuses=(200,)):
    status, data, headers = result
    if status not in statuses or not isinstance(data, dict):
        raise ValueError('Preview API request failed.')
    if headers.get('x-commit-sha') != sha[:7]:
        raise ValueError('Preview backend commit does not match deployment.')
    if 'no-store' not in headers.get('cache-control', '') or not headers.get('x-request-id'):
        raise ValueError('Preview proxy lost privacy or trace headers.')
    return data


def ready(base, sha, request=request_json):
    data = assert_response(request(base, '/ready'), sha)
    if (data.get('status'), data.get('database'), data.get('schema')) != ('ready', 'connected', 'current'):
        raise ValueError('Preview database schema is not ready.')


def run_checks(base, sha, *, request=request_json):
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Expected a full deployment commit SHA.')
    ready(base, sha, request)
    verification = assert_response(request(base, '/api/v1/verifications', 'POST', {
        'company_name': 'FPT Software', 'contact_email': 'Recruitment@fpt.com',
    }), sha)
    if verification.get('verification_label_vi') != 'Khớp nguồn đã xác minh' or not verification.get('matched_sources'):
        raise ValueError('Reviewed verification source was not bootstrapped.')
    for source in verification['matched_sources']:
        if not all(source.get(key) for key in ('url', 'verified_at', 'source_revision', 'evidence_excerpt_vi')):
            raise ValueError('Verification provenance is missing.')
    analysis = assert_response(request(base, '/api/v1/analyses', 'POST', {
        'text': 'Công ty kiểm thử Preview tuyển lập trình viên tại Hà Nội. Lương 10 triệu/tháng. Liên hệ smoke@example.com.',
    }), sha, statuses=(200, 201))
    token, analysis_id = analysis.get('guest_session_token'), analysis.get('id')
    if not isinstance(token, str) or not token or not isinstance(analysis_id, str) or not re.fullmatch(r'[A-Za-z0-9-]+', analysis_id):
        raise ValueError('Analysis did not create a guest session.')
    restored = assert_response(request(base, '/api/v1/analyses/' + analysis_id, headers={'X-Guest-Session-Token': token}), sha)
    if restored.get('id') != analysis_id or not restored.get('risk_label_vi'):
        raise ValueError('Guest analysis could not be restored.')


def deployment_event(path):
    event = json.loads(Path(path).read_text())
    deployment, status = event['deployment'], event['deployment_status']
    repository = os.environ['GITHUB_REPOSITORY']
    environment = deployment.get('environment', '').lower()
    if (event['repository']['full_name'] != repository or status['state'] != 'success'
            or deployment['creator']['login'] != 'vercel[bot]'
            or status['creator']['login'] != 'vercel[bot]'
            or not (environment == 'preview' or environment.startswith('preview '))):
        raise ValueError('Not an approved Vercel Preview deployment event.')
    sha = deployment['sha']
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Invalid deployment commit.')
    _, prs, _ = request_json('https://api.github.com', f'/repos/{repository}/commits/{sha}/pulls', headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN']})
    if not isinstance(prs, list) or not any(pr.get('state') == 'open' and pr['head']['repo'] and pr['head']['repo']['full_name'] == repository and pr['head']['sha'] == sha for pr in prs):
        raise ValueError('Deployment is not the current head of an open same-repository PR.')
    return validate_url(status.get('environment_url') or status.get('target_url') or ''), sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url')
    parser.add_argument('--sha')
    parser.add_argument('--deployment-event')
    parser.add_argument('--allow-local', action='store_true')
    args = parser.parse_args()
    try:
        if args.deployment_event:
            base, sha = deployment_event(args.deployment_event)
        else:
            base, sha = validate_url(args.url or '', allow_local=args.allow_local), args.sha or ''
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise ValueError('Expected a full deployment commit SHA.')
        deadline = time.monotonic() + 300
        while True:
            try:
                ready(base, sha)
                break
            except (ValueError, URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise ValueError('Preview not ready after 300 seconds; check backend deploy, PR metadata and schema.') from None
                time.sleep(10)
        run_checks(base, sha)
    except Exception as error:
        # Never dump response bodies, guest tokens, or environment values to Actions logs.
        message = str(error) if isinstance(error, ValueError) else type(error).__name__
        raise SystemExit('Preview smoke failed: ' + message) from None
    print('Preview smoke passed: matching commit, current schema, reviewed source and guest analysis restore.')


if __name__ == '__main__':
    main()
