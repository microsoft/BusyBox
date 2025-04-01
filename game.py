import serial
from serial.tools import list_ports
import time
import threading
import yaml
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BombGame:
    def __init__(self, config_path="game_config.yaml"):
        logger.info("Initializing BombGame")
        self.load_config(config_path)
        logger.info("Config loaded")
        self.setup_success_conditions()
        logger.info("Success conditions setup")
        self.setup_devices()
        logger.info("Devices setup")
        self.threads = []

    def load_config(self, config_path):
        """Load game configuration from YAML file."""
        config_path = Path(__file__).parent / config_path
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Set common variables from config
        self.countdown_seconds = self.config["countdown"]["time_seconds"]

        # Calculate slider success range
        slider1_config = self.config["slider_module"]["devices"][0]["ports"]["slider1"]
        slider1_range = slider1_config["range"]
        slider2_config = self.config["slider_module"]["devices"][0]["ports"]["slider2"]
        slider2_range = slider2_config["range"]

        self.slider1_success = slider1_range
        self.slider2_success = slider2_range

        # Get rotary success range based on direction
        rotary_config = self.config["rotary_module"]["devices"][0]["ports"]["rotary"]
        self.rotary_success = rotary_config["range"]

    def setup_success_conditions(self):
        """Initialize success conditions based on config."""
        self.success_conditions = {
            "slider1_in_range": False,
            "slider2_in_range": False,
            "rotary_in_range": False,
            "switches_correct": False,
            "wires_correct": False,
            "buttons_correct": False,
        }

    def find_port(self, pid):
        """Find a serial port by PID."""

        # if isinstance(pid, str):
        #     pid = int(pid, 16)

        ports = list_ports.comports(include_links=False)
        for p in ports:
            print(p, p.pid, hex(p.pid), pid)
            if p.pid is not None:
                logger.debug(f"Port: {p.device} - {hex(p.pid)}")
                if p.pid == pid:
                    return p
        raise Exception(f"PID {hex(pid)} not found")

    def find_serial_device(self, pid, baud_rate=9600):
        """Find and open a serial device by PID."""
        port = self.find_port(pid)
        return serial.Serial(port.device, baudrate=baud_rate, timeout=0.5)

    def send_command(self, ser_port, command):
        """Send command to serial port and read response."""
        ser_port.flushInput()
        ser_port.write(command.encode())
        response = ser_port.read(25).decode()
        return response

    def gpio_commands(self):
        """GPIO command helpers."""
        return {
            "read": lambda ser_port, pin: int(
                self.send_command(ser_port, f"adc read {pin}\r")[12:-3]
            ),
            "set": lambda ser_port, pin: self.send_command(
                ser_port, f"gpio set {pin}\r"
            ),
            "clear": lambda ser_port, pin: self.send_command(
                ser_port, f"gpio clear {pin}\r"
            ),
        }

    def countdown_timer(self):
        """Countdown timer thread."""
        display = self.devices["display"]
        if not display:
            logger.error("Display not found!")
            return

        clear_screen_bytes = bytes([0xFE, 0x58])
        display.write(clear_screen_bytes)
        start_time = time.time()
        last_time_str = "\n\n"

        while time.time() - start_time < self.countdown_seconds:
            remaining = self.countdown_seconds - int(time.time() - start_time)
            minutes, seconds = divmod(remaining, 60)
            time_str = f"     {minutes:02d}:{seconds:02d}\n"

            if time_str != last_time_str:
                display.write(clear_screen_bytes)
                display.write(time_str.encode())

            last_time_str = time_str
            time.sleep(0.5)
            logger.info(self.success_conditions)

            if all(self.success_conditions.values()):
                display.write(clear_screen_bytes)
                display.write(b"   DISARMED!")
                return

        if not all(self.success_conditions.values()):
            display.write(clear_screen_bytes)
            display.write(b"!!!!!!BOOM!!!!!!")

    def read_rotary_value(self):
        """Read rotary encoder values."""
        rotary_trinkey = self.devices.get("rotary")
        if not rotary_trinkey:
            logger.error("Rotary Trinkey not found!")
            return

        rotary_last_val = 0
        start_time = time.time()

        ticks_per_circle = 18
        numbers_on_dial = 6

        while time.time() - start_time < self.countdown_seconds:
            y = rotary_trinkey.readline().decode("utf-8").strip()
            if y.startswith("Rotary: "):
                rotary_val = int(float(y.split(": ")[1])) % ticks_per_circle
                rotary_val = numbers_on_dial - (rotary_val / numbers_on_dial)
                if rotary_val != rotary_last_val:
                    logger.info(f"Rotary: {rotary_val}")
                    rotary_last_val = rotary_val
                    self.success_conditions["rotary_in_range"] = (
                        self.rotary_success[0] <= rotary_val <= self.rotary_success[1]
                    )

    def find_serial_device_by_prefix(self, pid, expected_prefix):
        """Find and open a serial device by PID and message prefix."""
        ports = list_ports.comports(include_links=False)
        for p in ports:
            logger.info(
                f"Checking port: {p.device} - {hex(p.pid)} for {expected_prefix}"
            )
            if p.pid == pid:
                try:
                    # Try to open the port with a timeout
                    ser = serial.Serial(p.device, timeout=0.5)  # 1 second timeout
                    # Wait for a line of data
                    for _ in range(
                        10
                    ):  # Try a few times in case first read isn't immediate
                        line = ser.readline().decode("utf-8").strip()
                        if line.startswith(expected_prefix):
                            return ser
                        time.sleep(0.1)
                    # If we didn't find the right device, close it and continue
                    ser.close()
                except Exception as e:
                    logger.error(f"Error checking device {p.device}: {e}")
                    continue
        raise Exception(
            f"Device with PID {hex(pid)} and prefix '{expected_prefix}' not found"
        )

    def read_slider_value(self):
        """Read slider values."""
        trinkey = self.devices.get("slider")
        if not trinkey:
            logger.error("Slider Trinkey not found!")
            return

        last_vals = {"slider1": 0, "slider2": 0}
        start_time = time.time()

        while time.time() - start_time < self.countdown_seconds:
            line = trinkey.readline().decode("utf-8").strip()
            if not line.startswith("SLIDER"):
                continue

            # Split the line into the two slider readings
            slider_readings = line.split("\t")

            # Process first slider
            if "SLIDER 1:" in slider_readings[0]:
                val1 = float(slider_readings[0].split("Scaled Value: ")[1])
                # val1 = int(val1 * 100)  # Convert to integer range
                if val1 != last_vals["slider1"]:
                    logger.info(f"Slider1 Value: {val1}")
                    last_vals["slider1"] = val1
                    self.success_conditions["slider1_in_range"] = (
                        self.slider1_success[0] <= val1 <= self.slider1_success[1]
                    )

            # Process second slider
            if len(slider_readings) > 1 and "SLIDER 2:" in slider_readings[1]:
                val2 = float(slider_readings[1].split("Scaled Value: ")[1])
                # val2 = int(val2 * 100)  # Convert to integer range
                if val2 != last_vals["slider2"]:
                    logger.info(f"Slider2 Value: {val2}")
                    last_vals["slider2"] = val2
                    self.success_conditions["slider2_in_range"] = (
                        self.slider2_success[0] <= val2 <= self.slider2_success[1]
                    )

            logger.info(
                f"Slider1: {last_vals['slider1']} ({self.slider1_success}), Slider2: {last_vals['slider2']} ({self.slider2_success})"
            )

    def direction_sequence(self, direction):
        """Generate LED sequence based on direction."""
        sequences = {
            "down": [(1, 0, 2), (1, 1, 0.1), (0, 0, 2), (0, 1, 2)],
            "left": [(1, 1, 0.1), (0, 1, 4), (1, 0, 2), (1, 1, 2)],
            "right": [(0, 0, 2), (0, 1, 0.1), (1, 0, 2), (1, 1, 2)],
            "up": [(0, 1, 0.1), (1, 1, 4), (0, 0, 2), (0, 1, 2)],
        }
        return sequences.get(direction, [])

    def handle_gpio(self):
        """Handle GPIO operations for switches and LEDs."""
        gpio_config = self.config["gpio_module"]["devices"][0]
        gpio_serial = self.devices.get("gpio")
        if not gpio_serial:
            logger.error("GPIO not found")
            return

        gpio_cmds = self.gpio_commands()
        start_time = time.time()
        last_check_time = 0

        # Set initial LED states
        for port_name, port_config in gpio_config["ports"].items():
            if port_config["type"] == "output":
                pin = port_config["pin"]
                if port_config["initial_state"] == 1:
                    logger.info(f"Setting {port_name} {pin} to on")
                    gpio_cmds["set"](gpio_serial, pin)
                else:
                    logger.info(f"Setting {port_name} {pin} to off")
                    gpio_cmds["clear"](gpio_serial, pin)
                time.sleep(1)

        # Track switch success conditions
        switch_conditions = {}
        input_ports = {
            name: cfg
            for name, cfg in gpio_config["ports"].items()
            if cfg["type"] == "input"
        }
        for port_name in input_ports:
            switch_conditions[f"{port_name}_correct"] = False

        while time.time() - start_time < self.countdown_seconds:
            current_time = time.time()

            # Check switches every 100ms
            if current_time - last_check_time >= 0.1:
                try:
                    # Check each switch
                    for port_name, port_config in input_ports.items():
                        pin = port_config["pin"]
                        current_state = gpio_cmds["read"](gpio_serial, pin)
                        current_state = current_state > 0
                        target_state = port_config["target_state"]

                        # Update success condition for this switch
                        switch_conditions[f"{port_name}_correct"] = (
                            current_state == target_state
                        )

                        # Log state changes
                        logger.info(
                            f"{port_name} (pin {pin}) state: {current_state}, target: {target_state}"
                        )

                    # Update overall GPIO success condition
                    self.success_conditions["switches_correct"] = all(
                        switch_conditions.values()
                    )

                    last_check_time = current_time
                except Exception as e:
                    logger.error(f"Error reading switches: {e}")

                time.sleep(0.01)

    def handle_four_wires(self):
        """Handle four wires module operations."""
        wires_config = self.config["four_wires_module"]["devices"][0]
        wires = self.devices.get("wires")
        if not wires:
            logger.error("Four wires module not found!")
            return

        start_time = time.time()
        last_check_time = 0

        # Track wire states
        wire_conditions = {}
        wire_ports = wires_config["ports"]
        for port_name in wire_ports:
            wire_conditions[f"{port_name}_correct"] = False

        while time.time() - start_time < self.countdown_seconds:
            current_time = time.time()

            # Check wires every 100ms
            if current_time - last_check_time >= 0.1:
                try:
                    # Read the wire states from serial
                    line: str = wires.readline().decode("utf-8").strip()
                    if line.startswith("WIRES"):
                        # Convert string to dict, removing single quotes
                        wire_states = eval(line.split(": ", maxsplit=1)[1])

                        # Check each wire and update conditions
                        wire_status = []
                        for wire_name, wire_config in wire_ports.items():
                            current_state = wire_states[wire_name]
                            target_state = wire_config["target_state"]

                            # Update success condition for this wire
                            wire_conditions[f"{wire_name}_correct"] = (
                                current_state == target_state
                            )
                            wire_status.append(
                                f"{wire_name}: {current_state}/{target_state}"
                            )

                        # Log all wire states in a single message
                        logger.info("Wires [current/target]: " + ", ".join(wire_status))

                        # Update overall wires success condition
                        self.success_conditions["wires_correct"] = all(
                            wire_conditions.values()
                        )

                    last_check_time = current_time
                except Exception as e:
                    logger.error(f"Error reading wires: {e}")

                time.sleep(0.01)

    def handle_four_buttons(self):
        """Handle four buttons module operations."""
        buttons_config = self.config["four_buttons_module"]["devices"][0]
        buttons = self.devices.get("buttons")
        if not buttons:
            logger.error("Four buttons module not found!")
            return

        start_time = time.time()
        last_check_time = 0

        # Track only buttons that need to be pressed
        button_conditions = {}
        button_ports = {
            name: cfg
            for name, cfg in buttons_config["ports"].items()
            if cfg["target_state"] == 1
        }
        for port_name in button_ports:
            button_conditions[f"{port_name}_correct"] = False

        while time.time() - start_time < self.countdown_seconds:
            current_time = time.time()

            # Check buttons every 100ms
            if current_time - last_check_time >= 0.1:
                try:
                    # Read the button states from serial
                    line: str = buttons.readline().decode("utf-8").strip()
                    if not line.startswith("button none"):
                        # Convert string to dict, removing single quotes

                        # Only check buttons that need to be pressed
                        button_status = []
                        for button_name in button_ports:
                            if button_name in line:
                                button_conditions[f"{button_name}_correct"] = True
                                button_status.append(f"{button_name}: pressed")

                        # Log only the buttons we care about
                        logger.info(
                            "Required buttons [current]: " + ", ".join(button_status)
                        )

                        # Success if all required buttons are pressed
                        self.success_conditions["buttons_correct"] = all(
                            button_conditions.values()
                        )
                    else:
                        logger.info("No buttons pressed")
                    last_check_time = current_time
                except Exception as e:
                    logger.error(f"Error reading buttons: {e}")

                time.sleep(0.01)

    def setup_devices(self):
        """Find and store all device connections during initialization."""
        self.devices = {}

        logger.info("Finding display device")
        try:
            display_config = self.config["countdown"]["display"]
            display_device = self.find_serial_device(display_config["pid"])
            self.devices["display"] = display_device
            logger.info("Display device connected")
            clear_screen_bytes = bytes([0xFE, 0x58])
            display_device.write(clear_screen_bytes)
            display_device.write(b" Initializing...")
        except Exception as e:
            logger.error(f"Failed to connect to display device: {e}")
            self.devices["display"] = None

        # Find slider device
        logger.info("Finding slider device")
        try:
            slider_config = self.config["slider_module"]["devices"][0]
            slider_device = self.find_serial_device_by_prefix(
                slider_config["pid"], "SLIDER"
            )
            self.devices["slider"] = slider_device
            logger.info("Slider device connected")
        except Exception as e:
            logger.error(f"Failed to connect to slider device: {e}")
            self.devices["slider"] = None

        # Find rotary device
        logger.info("Finding rotary device")
        try:
            rotary_config = self.config["rotary_module"]["devices"][0]
            rotary_device = self.find_serial_device(rotary_config["pid"])
            self.devices["rotary"] = rotary_device
            logger.info("Rotary device connected")
        except Exception as e:
            logger.error(f"Failed to connect to rotary device: {e}")
            self.devices["rotary"] = None

        # Find wires device
        logger.info("Finding wires device")
        try:
            wires_config = self.config["four_wires_module"]["devices"][0]
            wires_device = self.find_serial_device_by_prefix(
                wires_config["pid"], "WIRES"
            )
            self.devices["wires"] = wires_device
            logger.info("Wires device connected")
        except Exception as e:
            logger.error(f"Failed to connect to wires device: {e}")
            self.devices["wires"] = None

        # Find GPIO device
        logger.info("Finding GPIO device")
        try:
            gpio_config = self.config["gpio_module"]["devices"][0]
            gpio_device = self.find_serial_device(gpio_config["pid"], baud_rate=19200)
            self.devices["gpio"] = gpio_device
            logger.info("GPIO device connected")
        except Exception as e:
            logger.error(f"Failed to connect to GPIO device: {e}")
            self.devices["gpio"] = None

        # Find buttons device
        logger.info("Finding buttons device")
        try:
            buttons_config = self.config["four_buttons_module"]["devices"][0]
            buttons_device = self.find_serial_device_by_prefix(
                buttons_config["pid"], "button"
            )
            self.devices["buttons"] = buttons_device
            logger.info("Buttons device connected")
        except Exception as e:
            logger.error(f"Failed to connect to buttons device: {e}")
            self.devices["buttons"] = None

    def start(self):
        """Start all game threads."""
        self.threads = [
            threading.Thread(target=self.countdown_timer, daemon=True),
            threading.Thread(target=self.read_rotary_value, daemon=True),
            threading.Thread(target=self.read_slider_value, daemon=True),
            threading.Thread(target=self.handle_gpio, daemon=True),
            threading.Thread(target=self.handle_four_wires, daemon=True),
            threading.Thread(target=self.handle_four_buttons, daemon=True),
        ]

        for thread in self.threads:
            thread.start()

        try:
            while any(thread.is_alive() for thread in self.threads):
                time.sleep(0.05)
        except KeyboardInterrupt:
            logger.info("Exiting...")


if __name__ == "__main__":
    game = BombGame()
    game.start()
