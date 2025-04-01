import serial
from serial.tools import list_ports
import time
import threading

countdown_seconds = 10 * 3  # 9 seconds


ROTARY_SUCCESS = (0, 5)
SLIDER_SUCCESS = (10, 20)

# Add these near the top with other globals
success_conditions = {
    "slider_in_range": False,
    "rotary_in_range": False,
    "button_pressed": False,
}


def find_port(pid):
    ports = list_ports.comports(include_links=False)
    for p in ports:
        if p.pid is not None:
            print("Port:", p.device, "-", hex(p.pid), end="\n")
            if p.pid == pid:
                return p
    else:
        raise Exception("pid {pid} not found")


def find_serial_device(pid):
    """Find a serial device by PID."""
    port = find_port(pid)
    return serial.Serial(port.device)


def send_command(ser_port, command):
    """Send command to the serial port and read the response."""
    ser_port.flushInput()
    ser_port.write(command.encode())
    response = ser_port.read(25).decode()
    return response


def read_gpio(ser_port, gpio_number):
    """Read GPIO pin state."""
    command = f"gpio read {gpio_number}\r"
    response = send_command(ser_port, command)
    response = int(response[12:-3])
    return response


def countdown_timer():
    """Countdown timer that updates a serial display."""
    display = find_serial_device(0x1)
    if not display:
        print("Display not found!")
        return

    clear_screen_bytes = bytes([0xFE, 0x58])
    display.write(clear_screen_bytes)

    start_time = time.time()
    last_time_str = "\n\n"

    while time.time() - start_time < countdown_seconds:
        remaining = countdown_seconds - int(time.time() - start_time)
        minutes = remaining // 60
        seconds = remaining % 60
        time_str = f"     {minutes:02d}:{seconds:02d}\n"

        if time_str != last_time_str:
            display.write(clear_screen_bytes)
            display.write(time_str.encode())

        last_time_str = time_str
        time.sleep(0.5)  # Reduce CPU usage

        # Check if all conditions are met
        if all(success_conditions.values()):
            display.write(clear_screen_bytes)
            display.write(b"   DISARMED!")
            return

    # Only show BOOM if not disarmed
    if not all(success_conditions.values()):
        display.write(clear_screen_bytes)
        display.write(b"!!!!!!BOOM!!!!!!")


def read_rotary_value():
    """Read values from a rotary Trinkey."""
    rotary_trinkey = find_serial_device(0x80FC)
    if not rotary_trinkey:
        print("Rotary Trinkey not found!")
        return

    rotary_last_val = 0
    start_time = time.time()

    while time.time() - start_time < countdown_seconds:
        y = rotary_trinkey.readline().decode("utf-8").strip()
        if y.startswith("Rotary: "):
            rotary_val = int(float(y.split(": ")[1]))
            if rotary_val != rotary_last_val:
                print("Rotary:", rotary_val)
                rotary_last_val = rotary_val
                success_conditions["rotary_in_range"] = (
                    ROTARY_SUCCESS[0] <= rotary_val <= ROTARY_SUCCESS[1]
                )


def read_slider_value():
    """Read values from a slider Trinkey."""
    trinkey = find_serial_device(0x8102)
    if not trinkey:
        print("Slider Trinkey not found!")
        return

    last_val = 0
    start_time = time.time()

    while time.time() - start_time < countdown_seconds:
        x = trinkey.readline().decode("utf-8").strip()
        if x.startswith("Slider: "):
            val = int(float(x.split(": ")[1]))
            if val != last_val:
                print("Slider Value:", val)
                last_val = val
                success_conditions["slider_in_range"] = (
                    SLIDER_SUCCESS[0] <= val <= SLIDER_SUCCESS[1]
                )


def read_button_value():
    gpio = find_port(0x800)
    if not gpio:
        print("GPIO not found")
        return

    baud_rate = 9600
    timeout = 1

    start_time = time.time()

    with serial.Serial(gpio.device, baud_rate, timeout=timeout) as ser_port:
        while time.time() - start_time < countdown_seconds:
            val = read_gpio(ser_port, 7)
            if val == 1:
                print("button clicked!")
                success_conditions["button_pressed"] = True
                return
            else:
                print("not button clicked")


# Start all tasks as separate threads
threads = [
    threading.Thread(target=countdown_timer, daemon=True),
    threading.Thread(target=read_rotary_value, daemon=True),
    threading.Thread(target=read_slider_value, daemon=True),
    threading.Thread(target=read_button_value, daemon=True),
]

for thread in threads:
    thread.start()

# Keep the main thread alive to allow background threads to run
try:
    while any(thread.is_alive() for thread in threads):
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting...")
