from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_ioctl_runtime_validation_and_readback():
    prefix = ['wsl.exe'] if os.name == 'nt' else []
    target = 'build/p0/detection-config-api-test'
    (ROOT/'build/p0').mkdir(parents=True, exist_ok=True)
    subprocess.run([*prefix, 'gcc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
        '-pedantic', '-Iplatforms/embedded/p0/include',
        'platforms/embedded/p0/src/p0_dma_runtime.c', 'tests/p0/p0_detection_config_api_run.c',
        '-Wl,--wrap=ioctl', '-o', target], cwd=ROOT, check=True, capture_output=True, text=True)
    run = subprocess.run([*prefix, target], cwd=ROOT, check=True, capture_output=True, text=True)
    assert 'DETECTION_CONFIG_API_PASS' in run.stdout
