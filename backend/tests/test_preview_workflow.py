"""Execute the workflow's real routing/bootstrap run blocks without GitHub or secrets."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

WORKFLOW = Path(__file__).resolve().parents[2] / '.github/workflows/preview-smoke.yml'
BOOTSTRAP = '0f6e4676b21b5b367d0e8daeab38beaab14c8a4f'


def workflow_script(marker):
    lines = WORKFLOW.read_text().splitlines()
    start = lines.index('      - ' + marker)
    start = next(index for index in range(start, len(lines)) if lines[index].startswith('        run:'))
    if lines[start] != '        run: |':
        return lines[start].split('run: ', 1)[1]
    script = []
    for line in lines[start + 1:]:
        if line and not line.startswith('          '):
            break
        script.append(line[10:])
    return '\n'.join(script)


def run_block(step, tmp_path, *, event=None, default_checker=False):
    output = tmp_path / 'output'
    event_path = tmp_path / 'event.json'
    event_path.write_text(json.dumps(event or {}))
    if default_checker:
        (tmp_path / 'scripts').mkdir()
        (tmp_path / 'scripts/check-preview.py').touch()
    binary = tmp_path / 'bin'
    binary.mkdir()
    git = binary / 'git'
    git.write_text('#!/bin/sh\nprintf "%s\\n" ' + 'a' * 40 + '\n')
    git.chmod(0o700)
    result = subprocess.run(['bash', '-e', '-c', workflow_script('id: ' + step)], cwd=tmp_path, env={
        **os.environ, 'PATH': str(binary) + os.pathsep + os.environ['PATH'],
        'GITHUB_OUTPUT': str(output), 'GITHUB_EVENT_PATH': str(event_path), 'GITHUB_SHA': 'b' * 40,
    }, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return dict(line.split('=', 1) for line in output.read_text().splitlines())


@pytest.mark.parametrize('creator,state,environment,relevant', [
    ('vercel[bot]', 'success', 'Preview', 'true'),
    ('vercel[bot]', 'success', 'Preview – job-shield', 'true'),
    ('Sntug', 'success', 'Tung - JobShield PR #7', 'false'),
    ('vercel[bot]', 'pending', 'Preview', 'false'),
    ('vercel[bot]', 'success', 'Production', 'false'),
])
def test_deployment_routing_is_explicit_not_a_skipped_job(tmp_path, creator, state, environment, relevant):
    event = {'deployment': {'creator': {'login': creator}, 'environment': environment}, 'deployment_status': {'state': state}}
    assert run_block('route', tmp_path, event=event)['relevant'] == relevant
    # Job-level conditions produce unevaluated names and can mask a real check with a later skip.
    assert '\n    if:' not in WORKFLOW.read_text()


def test_first_rollout_uses_audited_checker_not_untrusted_pr_head(tmp_path):
    assert run_block('checker', tmp_path)['revision'] == BOOTSTRAP


def test_after_installation_checker_tracks_trusted_default_branch(tmp_path):
    assert run_block('checker', tmp_path, default_checker=True)['revision'] == 'a' * 40


@pytest.mark.parametrize('outcome,expected_states', [
    ('success', ['pending', 'success']),
    ('failure', ['pending', 'failure']),
    ('ignored', []),
    ('untrusted', []),
    ('api-error', ['pending']),
    ('status-read-error', []),
])
def test_smoke_publishes_a_separate_commit_status(tmp_path, outcome, expected_states):
    result = run_status_smoke(tmp_path, outcome)
    statuses = tmp_path / 'statuses'
    assert (statuses.read_text().splitlines() if statuses.exists() else []) == expected_states
    assert (result.returncode == 0) == (outcome in {'success', 'ignored'})
    assert 'fixture-token' not in result.stdout + result.stderr


@pytest.mark.parametrize('rerun_id', ['10', '20', '30'])
def test_deployment_status_only_blocks_older_reruns(tmp_path, rerun_id):
    assert run_status_smoke(tmp_path, 'failure', deployment_id='20').returncode != 0
    assert run_status_smoke(tmp_path, 'success', deployment_id=rerun_id).returncode == 0
    expected_states = ['pending', 'failure'] if rerun_id == '10' else ['pending', 'failure', 'pending', 'success']
    assert (tmp_path / 'statuses').read_text().splitlines() == expected_states
    assert (tmp_path / 'checks').read_text().splitlines() == (['20'] if rerun_id == '10' else ['20', rerun_id])


def run_status_smoke(tmp_path, outcome, *, deployment_id='20'):
    # The expensive cloud checker is a boundary double; execute the real workflow wrapper.
    scripts = tmp_path / 'scripts'
    scripts.mkdir(exist_ok=True)
    (scripts / 'check-preview.py').write_text('''
import json, os
from pathlib import Path

def deployment_event(path):
    if os.environ['OUTCOME'] == 'untrusted':
        raise ValueError('Not an approved deployment')
    return 'https://job-shield-x-sntug.vercel.app', 'a' * 40

def request_json(base, path, method='GET', payload=None, headers=None):
    assert base == 'https://api.github.com'
    assert headers == {'Authorization': 'Bearer fixture-token'}
    if method == 'GET':
        assert path == '/repos/Sntug/JobShield/commits/' + 'a' * 40 + '/status?per_page=100'
        latest = Path('latest')
        return (403 if os.environ['OUTCOME'] == 'status-read-error' else 200), {
            'statuses': [json.loads(latest.read_text())] if latest.exists() else [],
        }, {}
    assert path == '/repos/Sntug/JobShield/statuses/' + 'a' * 40
    assert method == 'POST'
    assert payload['context'] == 'JobShield / Preview smoke'
    assert payload['target_url'] == 'https://github.com/Sntug/JobShield/actions/runs/123'
    with open('statuses', 'a') as output:
        output.write(payload['state'] + '\\n')
    if os.environ['OUTCOME'] != 'api-error':
        Path('latest').write_text(json.dumps(payload))
    return (403 if os.environ['OUTCOME'] == 'api-error' else 201), {}, {}

def main():
    with open('checks', 'a') as output:
        output.write(os.environ['PREVIEW_DEPLOYMENT_ID'] + '\\n')
    if os.environ['OUTCOME'] == 'failure':
        raise SystemExit('Preview access denied')

if __name__ == '__main__':
    main()
''')
    return subprocess.run(['bash', '-e', '-c', workflow_script('name: Verify actual frontend to backend to database flow')],
                            cwd=tmp_path, env={**os.environ, 'OUTCOME': outcome,
        'PATH': str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'],
        'PREVIEW_RELEVANT': 'false' if outcome == 'ignored' else 'true',
        'PREVIEW_DEPLOYMENT_ID': deployment_id,
        'GITHUB_REPOSITORY': 'Sntug/JobShield', 'GITHUB_RUN_ID': '123',
        'GITHUB_SERVER_URL': 'https://github.com', 'GITHUB_TOKEN': 'fixture-token',
        'GITHUB_EVENT_PATH': 'event.json',
    }, capture_output=True, text=True)
