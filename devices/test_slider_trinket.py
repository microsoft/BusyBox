import sys
import serial
from serial.tools import list_ports
import time

slider_trinkey_port = None
ports = list_ports.comports(include_links=False)
for p in ports:
    if p.pid is not None:
        print("Port:", p.device, "-", hex(p.pid), end="\t")
        if p.pid == 0x801F:
            slider_trinkey_port = p
            print("Found Slider Trinket!", p)
            # need to figure a better way for this.
            # it looked like two ports were available, but only one was working.
            trinkey = serial.Serial("/dev/ttyACM2")
            break
else:
    print("Did not find Slider Trinket port :(")
    sys.exit()

start_time = time.time()
last_val = 0
while time.time() - start_time < 15:
    x = trinkey.readline().decode("utf-8")
    print(x)
    time.sleep(0.1)
    # if not x.startswith("Slider: "):
    #     continue

    # val = int(float(x.split(": ")[1]))
    # if val != last_val:
    #     print("Slider Value:", val)
    #     last_val = val
