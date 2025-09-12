import glob, serial, time, re

KNOWN_IDS = {
    "buttons_module",
    "knob_module",
    "sliders_module",
    "switches_module",
    "wires_module",
    "e-ink_display_module",
}

def identify_ports(timeout=8.0):
    result = {}
    for path in glob.glob("/dev/ttyUSB*"):
        try:
            ser = serial.Serial(path, 9600, timeout=0.2)
        except Exception:
            continue
        start = time.time()
        while time.time() - start < timeout and path not in result:
            line = ser.readline().decode(errors="ignore").strip()
            if line in KNOWN_IDS:
                result[path] = line
        ser.close()
    return result

def port_sort_key(port):
    m = re.search(r'(\d+)$', port)
    return int(m.group(1)) if m else 1e9

def pretty_print(mapping):
    if not mapping:
        print("No modules detected.")
        return
    # Sort by port number
    items = sorted(mapping.items(), key=lambda kv: port_sort_key(kv[0]))
    w_port = max(len(p) for p,_ in items)
    w_mod  = max(len(m) for _,m in items)
    print("Detected Arduino modules:")
    print(f"{'PORT'.ljust(w_port)}  MODULE")
    print(f"{'-'*w_port}  {'-'*w_mod}")
    for port, mod in items:
        print(f"{port.ljust(w_port)}  {mod}")

if __name__ == "__main__":
    mapping = identify_ports()
    pretty_print(mapping)
