"""Execute the workflow's real routing/bootstrap run blocks without GitHub or secrets."""

import json
import os
from pathlib import Path
import subprocess

import pytest

WORKFLOW = Path(__file__).resolve().parents[2] / '.github/workflows/preview-smoke.yml'
BOOTSTRAP = '0f6e4676b21b5b367d0e8daeab38beaab14c8a4f'


def run_block(step, tmp_path, *, event=None, default_checker=False):
    lines = WORKFLOW.read_text().splitlines()
    start = lines.index(f'      - id: {step}')
    start = lines.index('        run: |', start) + 1
    script = []
    for line in lines[start:]:
        if line and not line.startswith('          '):
            break
        script.append(line[10:])
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
    result = subprocess.run(['bash', '-e', '-c', '\n'.join(script)], cwd=tmp_path, env={
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
