import sys
import serial
from serial.tools import list_ports
import time

display_port = None
ports = list_ports.comports(include_links=False)
for p in ports:
    if p.pid is not None:
        print("Port:", p.device, "-", hex(p.pid), end="\t")
        if p.pid == 0x1:
            display_port = p
            print("Found Display!")
            display = serial.Serial(p.device)
            break

start_time = time.time()
display_last_val = 0

last_time_str = "\n\n"

clear_screen_bytes = bytes([0xFE, 0x58])
display.write(clear_screen_bytes)

countdown_seconds = 3 * 3  # 3 minutes in seconds
while time.time() - start_time < countdown_seconds:
    remaining = countdown_seconds - int(time.time() - start_time)
    minutes = remaining // 60
    seconds = remaining % 60
    time_str = f"     {minutes:02d}:{seconds:02d}\n"
    if time_str != last_time_str:
        display.write(clear_screen_bytes)
        display.write(time_str.encode())
    last_time_str = time_str
