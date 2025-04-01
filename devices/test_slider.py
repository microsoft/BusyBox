import sys
import serial
from serial.tools import list_ports
import time

slider_trinkey_port = None
ports = list_ports.comports(include_links=False)
for p in ports:
    if p.pid is not None:
        print("Port:", p.device, "-", hex(p.pid), end="\t")
        if p.pid == 0x8102:
            slider_trinkey_port = p
            print("Found Slider Trinkey!")
            trinkey = serial.Serial(p.device)
            break
else:
    print("Did not find Slider Trinkey port :(")
    sys.exit()

start_time = time.time()
last_val = 0
while time.time() - start_time < 15:
    x = trinkey.readline().decode("utf-8")
    if not x.startswith("Slider: "):
        continue

    val = int(float(x.split(": ")[1]))
    if val != last_val:
        print("Slider Value:", val)
        last_val = val
