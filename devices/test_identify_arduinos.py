import glob, serial, time, re, argparse, sys

KNOWN_IDS = {
    "buttons_module",
    "knob_module",
    "sliders_module",
    "switches_module",
    "wires_module",
    "e-ink_display_module",
}

def identify_ports_static(timeout=8.0):
    """Original one-shot glob version."""
    result = {}
    for path in glob.glob("/dev/ttyUSB*"):
        try:
            ser = serial.Serial(path, 9600, timeout=0.25)
        except Exception:
            continue
        start = time.time()
        while time.time() - start < timeout and path not in result:
            line = ser.readline().decode(errors="ignore").strip()
            if line in KNOWN_IDS:
                result[path] = line
        ser.close()
    return result

def identify_ports_dynamic(timeout=8.0, rescan_interval=0.4, dtr_reset=True, dtr_reset_at=0.5):
    """Continuously rescan /dev/ttyUSB* during timeout, open new ports, optionally DTR reset midway.

    dtr_reset_at: fraction of timeout after which unidentified ports will get a DTR toggle once.
    """
    opened = {}          # path -> serial object
    identified = {}      # path -> identity
    dtr_toggled = set()  # paths already toggled
    start = time.time()
    next_scan = start
    try:
        while True:
            now = time.time()
            elapsed = now - start
            if elapsed >= timeout:
                break
            if now >= next_scan:
                for path in glob.glob("/dev/ttyUSB*"):
                    if path not in opened:
                        try:
                            opened[path] = serial.Serial(path, 9600, timeout=0.15)
                        except Exception:
                            continue
                next_scan = now + rescan_interval
            # Read from all unopened identities
            for path, ser in list(opened.items()):
                if path in identified:
                    continue
                try:
                    line = ser.readline().decode(errors="ignore").strip()
                except Exception:
                    continue
                if not line:
                    continue
                if line in KNOWN_IDS:
                    identified[path] = line
                # Consider two-line beacon second line: ignore if not identity
            # Optional DTR reset once after threshold
            if dtr_reset and elapsed/timeout >= dtr_reset_at:
                for path, ser in opened.items():
                    if path in identified or path in dtr_toggled:
                        continue
                    try:
                        ser.dtr = False
                        time.sleep(0.05)
                        ser.dtr = True
                        dtr_toggled.add(path)
                    except Exception:
                        pass
            time.sleep(0.05)
    finally:
        for ser in opened.values():
            try: ser.close()
            except Exception: pass
    return identified

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

def main(argv=None):
    p = argparse.ArgumentParser(description="Identify connected Arduino modules by alive beacons.")
    p.add_argument("--timeout", type=float, default=8.0, help="Total discovery time (s).")
    p.add_argument("--static", action="store_true", help="Use legacy single-scan method.")
    p.add_argument("--no-dtr", action="store_true", help="Disable DTR reset on dynamic mode.")
    p.add_argument("--rescan", type=float, default=0.4, help="Rescan interval for dynamic mode (s).")
    p.add_argument("--no-pretty", action="store_true", help="Print raw dict only.")
    args = p.parse_args(argv)

    if args.static:
        mapping = identify_ports_static(timeout=args.timeout)
    else:
        mapping = identify_ports_dynamic(timeout=args.timeout, rescan_interval=args.rescan, dtr_reset=not args.no_dtr)

    if args.no_pretty:
        print(mapping)
    else:
        pretty_print(mapping)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
