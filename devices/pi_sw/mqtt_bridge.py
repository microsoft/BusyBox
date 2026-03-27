#!/usr/bin/env python3
"""
BusyBox MQTT Bridge

Functions:
  * Discovers all connected BusyBox Arduino modules by listening for alive beacons.
  * Starts a serial reader thread for each data-producing module (buttons, knob, sliders, switches, wires).
  * Publishes every parsed data update immediately to MQTT topics.
  * Subscribes to a command topic for the e-ink display and forwards commands to the e-ink module's serial port.

MQTT Topics (default prefix 'busybox'):
  busybox/buttons/state   -> JSON: {"ts": <unix_seconds>, "values": [..]}
  busybox/knob/state
  busybox/sliders/state
  busybox/switches/state
  busybox/wires/state
  busybox/eink/cmd        -> SUBSCRIBE to send commands to e-ink display (payload is raw line, newline optional)
  busybox/status/bridge   -> Bridge lifecycle events / errors (plain text)

Example e-ink publishes (from another machine):
  mosquitto_pub -h <pi-host> -t busybox/eink/cmd -m "1:BusyBox Demo"
  mosquitto_pub -h <pi-host> -t busybox/eink/cmd -m "2:Ready!"
  mosquitto_pub -h <pi-host> -t busybox/eink/cmd -m "CLEAR"
  mosquitto_pub -h <pi-host> -t busybox/eink/cmd -m "REFRESH"

CLI Options:
  --broker-host HOST   (default: localhost)
  --broker-port PORT   (default: 1883)
  --discovery-timeout S (default: 8.0)
  --base-topic PREFIX  (default: busybox)
  --log-file PATH      (optional) append text log
  --verbose            (extra stdout logging)

Requires: pyserial, paho-mqtt

Stop with Ctrl+C.
"""
import argparse
import glob
import json
import queue
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

import serial  # type: ignore
import paho.mqtt.client as mqtt  # type: ignore

# ---------------- Configuration Maps ----------------
IDENTITY_MAP = {
    "buttons_module": "buttons",
    "knob_module": "knob",
    "sliders_module": "sliders",
    "switches_module": "switches",
    "wires_module": "wires",
    "e-ink_display_module": "eink",  # sink only
}
DATA_DEVICE_NAMES = {"buttons", "knob", "sliders", "switches", "wires"}
BAUD = 9600
PORT_LINE_TIMEOUT = 0.25

# Prefix markers in second beacon lines
BUTTONS_PREFIX = "Button States:"  # D2=1 ...
SWITCHES_PREFIX = "Switch States:"
WIRES_PREFIX = "Wire States:"
SLIDERS_PREFIX = "Slider States:"  # A0=123 A1=456
KNOB_PREFIX = "Knob State:"        # Knob State: 42

# ----------------------------------------------------

def parse_args():
    ap = argparse.ArgumentParser(description="BusyBox serial -> MQTT bridge")
    ap.add_argument('--broker-host', default='localhost')
    ap.add_argument('--broker-port', type=int, default=1883)
    ap.add_argument('--discovery-timeout', type=float, default=8.0)
    ap.add_argument('--base-topic', default='busybox')
    ap.add_argument('--log-file', default=None)
    ap.add_argument('--verbose', action='store_true')
    return ap.parse_args()


def log(msg: str, *, state=None, file_handle=None, verbose=False):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    if verbose:
        print(line)
    if file_handle:
        try:
            file_handle.write(line + "\n")
        except Exception:
            pass


# ---------------- Port Discovery --------------------

def identify_ports(timeout: float, verbose=False) -> Dict[str, str]:
    """Listen on /dev/ttyUSB* for identity beacons.
    Returns mapping: logical_name -> port
    """
    reverse = {}  # identity -> path
    deadline = time.time() + timeout
    open_ports = []
    for path in glob.glob('/dev/ttyUSB*'):
        try:
            ser = serial.Serial(path, BAUD, timeout=0.3)
            open_ports.append(ser)
        except Exception:
            continue
    try:
        while time.time() < deadline and len(reverse) < len(IDENTITY_MAP):
            for ser in list(open_ports):
                if ser.port in reverse.values():
                    continue
                try:
                    line = ser.readline().decode(errors='ignore').strip()
                except Exception:
                    continue
                if line in IDENTITY_MAP and line not in reverse:
                    reverse[line] = ser.port
                    if verbose:
                        print(f"Discovered {line} on {ser.port}")
            time.sleep(0.05)
    finally:
        for ser in open_ports:
            try: ser.close()
            except Exception: pass
    logical = {}
    for identity, port in reverse.items():
        logical_name = IDENTITY_MAP[identity]
        logical[logical_name] = port
    return logical

# ---------------- Data Parsing ----------------------

def parse_values(device: str, line: str):
    try:
        if device == 'buttons' and line.startswith(BUTTONS_PREFIX):
            return [int(p.split('=')[1]) for p in line.split(':',1)[1].strip().split() if '=' in p]
        if device == 'switches' and line.startswith(SWITCHES_PREFIX):
            return [int(p.split('=')[1]) for p in line.split(':',1)[1].strip().split() if '=' in p]
        if device == 'wires' and line.startswith(WIRES_PREFIX):
            return [int(p.split('=')[1]) for p in line.split(':',1)[1].strip().split() if '=' in p]
        if device == 'sliders' and line.startswith(SLIDERS_PREFIX):
            return [int(p.split('=')[1]) for p in line.split(':',1)[1].strip().split() if '=' in p]
        if device == 'knob' and line.startswith(KNOB_PREFIX):
            num = line.split(':',1)[1].strip()
            if num:
                return [int(num)]
    except Exception:
        return None
    return None

# ---------------- Serial Reader Thread --------------

class SerialReader(threading.Thread):
    def __init__(self, device_name: str, port: str, out_queue: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.device_name = device_name
        self.port = port
        self.out_queue = out_queue
        self.stop_event = stop_event
        self.ser: Optional[serial.Serial] = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, BAUD, timeout=PORT_LINE_TIMEOUT)
        except Exception:
            return
        while not self.stop_event.is_set():
            try:
                line = self.ser.readline().decode(errors='ignore').strip()
                if not line:
                    continue
                vals = parse_values(self.device_name, line)
                if vals is not None:
                    self.out_queue.put((time.time(), self.device_name, vals))
            except Exception:
                continue
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass

# ---------------- E-Ink Command Sink ----------------

class EinkSink:
    def __init__(self, port: Optional[str], verbose=False):
        self.port = port
        self.verbose = verbose
        self.ser: Optional[serial.Serial] = None
        if port:
            try:
                self.ser = serial.Serial(port, BAUD, timeout=0.3)
            except Exception:
                self.ser = None

    def send(self, cmd: str):
        if not self.ser:
            return False
        # Ensure newline
        if not cmd.endswith('\n'):
            cmd_to_send = cmd + '\n'
        else:
            cmd_to_send = cmd
        try:
            self.ser.write(cmd_to_send.encode())
            if self.verbose:
                print(f"Sent to e-ink: {cmd.strip()}")
            return True
        except Exception:
            return False

    def close(self):
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass

# ---------------- MQTT Bridge -----------------------

def main():
    args = parse_args()
    log_fp = open(args.log_file, 'a', buffering=1) if args.log_file else None

    # Print selected CLI options at program start
    print("Selected CLI options:")
    print(f"  --broker-host {args.broker_host}")
    print(f"  --broker-port {args.broker_port}")
    print(f"  --discovery-timeout {args.discovery_timeout}")
    print(f"  --base-topic {args.base_topic}")
    print(f"  --log-file {args.log_file}")
    print(f"  --verbose {args.verbose}")

    log("Discovering modules...", file_handle=log_fp, verbose=True)
    mapping = identify_ports(args.discovery_timeout, verbose=args.verbose)
    if not mapping:
        log("No modules discovered; exiting.", file_handle=log_fp, verbose=True)
        return 1
    log(f"Discovered mapping: {mapping}", file_handle=log_fp, verbose=True)

    eink_port = mapping.get('eink')
    eink_sink = EinkSink(eink_port, verbose=args.verbose)

    # Queue for serial updates
    q: queue.Queue = queue.Queue()
    stop_event = threading.Event()

    readers = []
    for dev in DATA_DEVICE_NAMES:
        if dev in mapping:
            t = SerialReader(dev, mapping[dev], q, stop_event)
            t.start()
            readers.append(t)

    # MQTT Client setup
    client_id = f"busybox-bridge-{int(time.time())}"
    client = mqtt.Client(client_id=client_id, clean_session=True)

    def on_connect(cli, userdata, flags, rc, properties=None):  # type: ignore
        if rc == 0:
            log("MQTT connected", file_handle=log_fp, verbose=True)
            # Subscribe for e-ink commands
            eink_topic = f"{args.base_topic}/eink/cmd"
            cli.subscribe(eink_topic, qos=0)
            log(f"Subscribed: {eink_topic}", file_handle=log_fp, verbose=args.verbose)
        else:
            log(f"MQTT connect failed rc={rc}", file_handle=log_fp, verbose=True)

    def on_message(cli, userdata, msg):  # type: ignore
        topic = msg.topic
        payload = msg.payload.decode(errors='ignore').strip()
        if topic.endswith('/eink/cmd'):
            if eink_sink.port is None:
                log("E-ink command received but no e-ink port available", file_handle=log_fp, verbose=True)
            else:
                ok = eink_sink.send(payload)
                if not ok:
                    log(f"Failed writing to e-ink: {payload}", file_handle=log_fp, verbose=True)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(args.broker_host, args.broker_port, keepalive=30)
    except Exception as e:
        log(f"Cannot connect to MQTT broker: {e}", file_handle=log_fp, verbose=True)
        eink_sink.close()
        return 2

    client.loop_start()

    base = args.base_topic.rstrip('/')
    status_topic = f"{base}/status/bridge"

    def publish_status(text: str):
        try:
            client.publish(status_topic, text, qos=0, retain=False)
        except Exception:
            pass

    publish_status("online")

    # Graceful shutdown
    running = True
    def handle_sig(sig, frame):  # noqa: ARG001
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    try:
        while running:
            try:
                _, dev, vals = q.get(timeout=0.3)
            except queue.Empty:
                continue
            topic = f"{base}/{dev}/state"
            payload = json.dumps({"values": vals})
            try:
                client.publish(topic, payload, qos=0, retain=False)
                if args.verbose:
                    print(f"PUB {topic} {payload}")
            except Exception:
                pass
    finally:
        publish_status("offline")
        stop_event.set()
        for t in readers:
            t.join(timeout=1.0)
        eink_sink.close()
        client.loop_stop()
        try:
            client.disconnect()
        except Exception:
            pass
        if log_fp:
            log_fp.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
