"""Complete the board's observed first-login password prompt without logging secrets."""
import os
import serial
import time

password = os.environ['TEKNO_BOARD_SETUP_PASSWORD']
with serial.Serial('COM6', 115200, timeout=.3) as connection:
    pending = connection.read(4096).decode(errors='replace')
    if 'login:' in pending or 'U-Boot' in pending:
        raise SystemExit('Board login state changed; no password sent.')
    connection.write(password.encode() + b'\r')
    output = connection.read(4096).decode(errors='replace')
    if 'Retype' not in output and 'retype' not in output:
        print(output.replace(password, '[REDACTED]'))
        raise SystemExit('Password confirmation prompt not observed.')
    connection.write(password.encode() + b'\r')
    time.sleep(.5)
    output += connection.read(8192).decode(errors='replace')
    print(output.replace(password, '[REDACTED]'))
