# License
# -------
# This code is published and shared by Numato Systems Pvt Ltd under GNU LGPL
# license with the hope that it may be useful. Read complete license at
# http://www.gnu.org/licenses/lgpl.html or write to Free Software Foundation,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

# Simplicity and understandability is the primary philosophy followed while
# writing this code. Sometimes at the expence of standard coding practices and
# best practices. It is your responsibility to independantly assess and implement
# coding practices that will satisfy safety and security necessary for your final
# application.

# This demo code demonstrates how to set, clear, and read a GPIO and read an analog channel.

import serial
from serial.tools import list_ports
import time


def send_command(ser_port, command):
    """Send command to the serial port and read the response."""
    ser_port.flushInput()
    ser_port.write(command.encode())
    response = ser_port.read(25).decode()
    return response


def find_port():
    ports = list_ports.comports(include_links=False)
    for p in ports:
        if p.pid is not None:
            print("Port:", p.device, "-", hex(p.pid), end="\n")
            if p.pid == 0x800:
                print("Found Numato gpio!" + p.device)
                return p
    else:
        print("Did not find Slider Trinkey port :(")
        raise Exception("Slider Trinkey not found")


def set_gpio(ser_port, gpio_number):
    """Set GPIO pin to high."""
    command = f"gpio set {gpio_number}\r"
    response = send_command(ser_port, command)
    return response


def clear_gpio(ser_port, gpio_number):
    """Clear GPIO pin to low."""
    command = f"gpio clear {gpio_number}\r"
    response = send_command(ser_port, command)
    return response


def read_gpio(ser_port, gpio_number):
    """Read GPIO pin state."""
    command = f"gpio read {gpio_number}\r"
    response = send_command(ser_port, command)
    response = int(response[12:-3])
    return response


def read_adc(ser_port, adc_channel):
    """Read ADC channel value with proper timing."""
    # Clear any pending data in the buffer
    ser_port.reset_input_buffer()
    ser_port.reset_output_buffer()

    # Send ADC read command
    adc_command = f"adc read {adc_channel}\r"
    adc_response = send_command(ser_port, adc_command)

    # Add a small delay to ensure command completion
    time.sleep(0.01)

    try:
        adc_value = int(adc_response[12:-3])
        return adc_value
    except (ValueError, IndexError):
        print(f"Invalid ADC response: {adc_response}")
        return None


def main():
    port = find_port()
    port_name = port.device  # Replace with your actual COM port
    baud_rate = 19200
    timeout = 1

    start_time = time.time()

    try:
        with serial.Serial(port_name, baud_rate, timeout=timeout) as ser_port:
            # Example 1: Read from ADC channel 0
            set_gpio(ser_port, 2)
            set_gpio(ser_port, 3)
            set_gpio(ser_port, 4)
            while time.time() - start_time < 63:
                adc_value = read_adc(ser_port, 0)
                print(f"ADC Read 0 is: {adc_value != 0}")
                adc_value = read_adc(ser_port, 1)
                print(f"ADC Read 1 is: {adc_value != 0}")
                # gpio_value = read_gpio(ser_port, 7)
                # print(f"GPIO 7 is: {gpio_value}")

            # adc_value = read_adc(ser_port, 1)
            # print(f"ADC Read 1 is: {adc_value}")

            # gpio_value = read_gpio(ser_port, 0)
            # print(f"GPIO 0 is: {gpio_value}")

            # gpio_value = read_gpio(ser_port, 1)
            # print(f"GPIO 1 is: {gpio_value}")

            # gpio_value = read_gpio(ser_port, 7)
            # print(f"GPIO 7 is: {gpio_value}")

            # print("Waiting 2 seconds")
            # time.sleep(2)

            # gpio_value = read_gpio(ser_port, 7)
            # print(f"GPIO 7 is: {gpio_value}")

            # set_gpio(ser_port, 0)
            # set_gpio(ser_port, 1)

            # print("Waiting 2 seconds")
            # time.sleep(2)

            # adc_value = read_adc(ser_port, 0)
            # print(f"ADC Read 0 is: {adc_value}")

            # adc_value = read_adc(ser_port, 1)
            # print(f"ADC Read 1 is: {adc_value}")

            # print("finished reading, wait 2")
            # time.sleep(2)

            # adc_value = read_adc(ser_port, 0)
            # print(f"ADC Read 0 is: {adc_value}")

            # adc_value = read_adc(ser_port, 1)
            # print(f"ADC Read 1 is: {adc_value}")

    except serial.SerialException as e:
        print(f"Error opening or communicating with serial port: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
