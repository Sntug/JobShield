"""Keep Tesseract's CPU budget local to the OCR child process."""

import os
import subprocess
import sys

from app.services.ocr import run_system_tesseract


def test_ocr_limits_child_threads_without_changing_parent_environment(tmp_path, monkeypatch):
    executable = tmp_path / 'tesseract'
    executable.write_text(
        f'#!{sys.executable}\n'
        'import os, sys\n'
        'assert sys.stdin.buffer.read() == b"image-bytes"\n'
        'print("threads=" + os.environ.get("OMP_THREAD_LIMIT", "unset") '
        '+ ";inherited=" + os.environ.get("R3_OCR_TEST_SETTING", "missing"))\n'
    )
    executable.chmod(0o700)
    monkeypatch.setattr('app.services.ocr.shutil.which', lambda _: str(executable))
    monkeypatch.setenv('OMP_THREAD_LIMIT', '8')
    monkeypatch.setenv('R3_OCR_TEST_SETTING', 'kept')
    parent = dict(os.environ)

    assert run_system_tesseract(b'image-bytes') == 'threads=1;inherited=kept'
    assert dict(os.environ) == parent


def test_ocr_timeout_stays_bounded_and_does_not_log_image_contents(monkeypatch, caplog):
    monkeypatch.setattr('app.services.ocr.shutil.which', lambda _: '/usr/bin/tesseract')

    def timeout(command, **kwargs):
        assert kwargs['timeout'] == 10
        raise subprocess.TimeoutExpired(command, 10, output=b'PRIVATE_IMAGE_TEXT', stderr=b'PRIVATE_IMAGE_TEXT')

    monkeypatch.setattr('app.services.ocr.subprocess.run', timeout)
    assert run_system_tesseract(b'PRIVATE_IMAGE_TEXT') is None
    assert 'TimeoutExpired' in caplog.text
    assert 'PRIVATE_IMAGE_TEXT' not in caplog.text
