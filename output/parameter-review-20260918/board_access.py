"""Pinned SSH access using a Windows-encrypted credential supplied in memory."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'build/parameter-deploy-python'))
import paramiko

plan = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
password = os.environ['TEKNO_BOARD_SETUP_PASSWORD']
client = paramiko.SSHClient()
client.load_host_keys(str(Path('output/parameter-review-20260918/verified-known-hosts')))
client.set_missing_host_key_policy(paramiko.RejectPolicy())
client.connect('192.168.7.2', username='petalinux', password=password,
               timeout=8, allow_agent=False, look_for_keys=False)
try:
    for step in plan:
        if 'download' in step:
            with client.open_sftp() as transfer:
                transfer.get(step['download'], step['destination'])
            print('Downloaded:', step['destination'], flush=True)
            continue
        if 'upload' in step:
            with client.open_sftp() as transfer:
                transfer.put(step['upload'], step['destination'])
            print('Uploaded:', step['destination'], flush=True)
            continue
        command = step['command']
        if step.get('sudo'):
            import shlex
            command = "sudo -S -p '' sh -c " + shlex.quote(command)
        stdin, stdout, stderr = client.exec_command(command, timeout=45)
        if step.get('sudo'):
            stdin.write(password + '\n'); stdin.flush()
        stdin.channel.shutdown_write()
        output = stdout.read().decode(errors='replace')
        errors = stderr.read().decode(errors='replace')
        code = stdout.channel.recv_exit_status()
        print(output.replace(password, '[REDACTED]'), end='', flush=True)
        print(errors.replace(password, '[REDACTED]'), end='', file=sys.stderr, flush=True)
        if code:
            raise SystemExit(code)
finally:
    client.close()
