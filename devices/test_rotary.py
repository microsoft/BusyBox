import sys
import serial
from serial.tools import list_ports
import time

rotary_trinkey_port = None
ports = list_ports.comports(include_links=False)
for p in ports:
    if p.pid is not None:
        print("Port:", p.device, "-", hex(p.pid), end="\t")
        if p.pid == 0x80FC:
            rotary_trinkey_port = p
            print("Found Rotary Trinkey!")
            rotary_trinkey = serial.Serial(p.device)
            break

start_time = time.time()
rotary_last_val = 0
while time.time() - start_time < 15:
    y = rotary_trinkey.readline().decode("utf-8")
    if not y.startswith("Rotary: "):
        continue

    rotary_val = int(float(y.split(": ")[1]))
    if rotary_val != rotary_last_val:
        print("Rotary:", rotary_val)
        rotary_last_val = rotary_val
