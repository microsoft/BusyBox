import glob
import time
import threading
import queue
import re
import serial
from pathlib import Path

# Known module identity strings -> logical short device name
IDENTITY_MAP = {
    "buttons_module": "buttons",
    "knob_module": "knob",
    "sliders_module": "sliders",
    "switches_module": "switches",
    "wires_module": "wires",
    "e-ink_display_module": "eink",  # special handling (no data; sink only)
}

DATA_DEVICE_NAMES = {"buttons", "knob", "sliders", "switches", "wires"}
EINK_IDENTITY = "e-ink_display_module"
BAUD = 9600
DISCOVERY_TIMEOUT = 8.0
LOG_PATH = Path(__file__).parent / "test_aggregation.log"
PUBLISH_INTERVAL = 15.0  # seconds

# Regex patterns to parse each device line format (loose / robust)
# We rely on known prefixes printed by each sketch.
BUTTONS_PREFIX = "Button States:"  # Button States: D2=1 D3=0 ...
SWITCHES_PREFIX = "Switch States:"  # Switch States: D2=1 D3=0 ...
WIRES_PREFIX = "Wire States:"      # Wire States: D2=1 D3=0 D4=1 D5=1
SLIDERS_PREFIX = "Slider States:"  # Slider States: A0=123 A1=456
KNOB_PREFIX = "Knob State:"        # Knob State: 42

PORT_LINE_TIMEOUT = 0.2


def identify_ports(timeout=DISCOVERY_TIMEOUT):
    """Identify modules by listening for alive beacons on /dev/ttyUSB*.
    Returns: { logical_name | 'eink' : serial_path }
    """
    reverse = {}  # identity -> path
    deadline = time.time() + timeout
    open_ports = []
    for path in glob.glob("/dev/ttyUSB*"):
        try:
            ser = serial.Serial(path, BAUD, timeout=0.25)
            open_ports.append(ser)
        except Exception:
            continue
    try:
        while time.time() < deadline and len(reverse) < len(IDENTITY_MAP):
            for ser in list(open_ports):
                if ser.port in reverse.values():
                    continue
                line = ser.readline().decode(errors="ignore").strip()
                if line in IDENTITY_MAP:
                    reverse[line] = ser.port
            # small sleep to avoid busy spin
            time.sleep(0.05)
    finally:
        for ser in open_ports:
            ser.close()
    # Map to logical names (avoid overwriting duplicates; last wins if any)
    logical = {}
    for identity, port in reverse.items():
        logical_name = IDENTITY_MAP[identity]
        logical[logical_name] = port
    return logical


def parse_values(device, line):
    """Return list[int] parsed from a status/output line for a given device logical name.
    Returns None if line not recognized.
    """
    try:
        if device == "buttons" and line.startswith(BUTTONS_PREFIX):
            # Example: Button States: D2=1 D3=0 D4=1 D5=1
            parts = line.split(":", 1)[1].strip().split()
            vals = []
            for p in parts:
                if '=' in p:
                    vals.append(int(p.split('=')[1]))
            return vals if vals else None
        if device == "switches" and line.startswith(SWITCHES_PREFIX):
            parts = line.split(":", 1)[1].strip().split()
            vals = []
            for p in parts:
                if '=' in p:
                    vals.append(int(p.split('=')[1]))
            return vals if vals else None
        if device == "wires" and line.startswith(WIRES_PREFIX):
            parts = line.split(":", 1)[1].strip().split()
            vals = []
            for p in parts:
                if '=' in p:
                    vals.append(int(p.split('=')[1]))
            return vals if vals else None
        if device == "sliders" and line.startswith(SLIDERS_PREFIX):
            # Slider States: A0=123 A1=456
            parts = line.split(":", 1)[1].strip().split()
            vals = []
            for p in parts:
                if '=' in p:
                    vals.append(int(p.split('=')[1]))
            return vals if vals else None
        if device == "knob" and line.startswith(KNOB_PREFIX):
            # Knob State: 42
            num = line.split(':',1)[1].strip()
            if num:
                return [int(num)]
    except Exception:
        return None
    return None


class SerialReader(threading.Thread):
    def __init__(self, device_name, port, out_queue, stop_event):
        super().__init__(daemon=True)
        self.device_name = device_name
        self.port = port
        self.out_queue = out_queue
        self.stop_event = stop_event
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, BAUD, timeout=PORT_LINE_TIMEOUT)
        except Exception as e:
            return
        buf = b""
        while not self.stop_event.is_set():
            try:
                line = self.ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                vals = parse_values(self.device_name, line)
                if vals is not None:
                    ts = time.time()
                    self.out_queue.put((ts, self.device_name, vals))
            except Exception:
                continue
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass


def open_eink_port(mapping):
    for logical, port in mapping.items():
        if logical == "eink":
            try:
                return serial.Serial(port, BAUD, timeout=0.3)
            except Exception:
                return None
    return None


def main():
    print("Identifying modules...")
    mapping = identify_ports()
    if not mapping:
        print("No devices found.")
        return
    # Display mapping
    for name, port in mapping.items():
        print(f"{name}: {port}")

    log_file = open(LOG_PATH, "a", buffering=1)
    log_file.write(f"# --- Session start {time.time():.3f} ---\n")

    stop_event = threading.Event()
    q = queue.Queue()

    latest = {}  # device -> (timestamp, values)

    readers = []
    for dev in DATA_DEVICE_NAMES:
        if dev in mapping:
            t = SerialReader(dev, mapping[dev], q, stop_event)
            t.start()
            readers.append(t)

    eink_ser = open_eink_port(mapping)
    last_publish = time.time()

    try:
        while True:
            try:
                ts, dev, vals = q.get(timeout=0.2)
                latest[dev] = (ts, vals)
                log_file.write(f"{ts:.3f} - {dev}: {vals}\n")
            except queue.Empty:
                pass

            now = time.time()
            if eink_ser and (now - last_publish) >= PUBLISH_INTERVAL:
                # Choose most recently updated device (among data devices)
                if latest:
                    recent_dev, (dts, dvals) = max(latest.items(), key=lambda kv: kv[1][0])
                    # Publish to e-ink: line1 device, line2 comma list
                    line1 = f"1:{recent_dev}\n"
                    line2 = f"2:{','.join(str(v) for v in dvals)}\n"
                    try:
                        eink_ser.write(line1.encode())
                        eink_ser.write(line2.encode())
                    except Exception:
                        pass
                last_publish = now
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        stop_event.set()
        for t in readers:
            t.join(timeout=1.0)
        if eink_ser:
            try: eink_ser.close()
            except Exception: pass
        log_file.write(f"# --- Session end {time.time():.3f} ---\n")
        log_file.close()


if __name__ == "__main__":
    main()
