"""Read SSH public identity through the physically attached board console."""
import os
import re
import time
from pathlib import Path
import serial

password = os.environ['TEKNO_BOARD_SETUP_PASSWORD']
def receive(port, seconds=1):
    end = time.monotonic() + seconds
    data = b''
    while time.monotonic() < end:
        data += port.read(8192)
    return data.decode(errors='replace')

with serial.Serial('COM6', 115200, timeout=.15) as port:
    port.write(b'\r')
    initial = receive(port)
    if 'login:' in initial:
        port.write(b'petalinux\r')
        prompt = receive(port)
        if 'password:' not in prompt.lower():
            raise RuntimeError('Expected password prompt: ' + repr(prompt))
        port.write(password.encode() + b'\r')
        prompt = receive(port, 2)
        if 'retype' in prompt.lower():
            port.write(password.encode() + b'\r')
            prompt = receive(port, 2)
        if 'Login incorrect' in prompt or 'login:' in prompt:
            raise RuntimeError('Console login failed')
    response = ''
    for command in (b'cat /etc/ssh/ssh_host_ed25519_key.pub\r',
                    b'cat /proc/device-tree/model\r', b'ip -4 addr\r'):
        for byte in command:
            port.write(bytes([byte]))
            time.sleep(.005)
        response += receive(port, 1)
    print(response.replace(password, '[REDACTED]'))
    match = re.search(r'(ssh-ed25519 AAAA[A-Za-z0-9+/=]+)', response)
    if not match or '192.168.7.2' not in response or 'Zynq' not in response:
        raise RuntimeError('Physical board identity incomplete')
    Path('output/parameter-review-20260918/verified-known-hosts').write_text(
        '192.168.7.2 ' + match.group(1) + '\n', encoding='ascii')
