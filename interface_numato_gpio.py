import serial
import time

# Configure the serial connection
ser = serial.Serial(
    port='/dev/tty_gpio',
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

def send_command(cmd):
    """Send command to GPIO module and read response"""
    ser.write((cmd + '\r').encode())
    time.sleep(0.1)  # Give device time to respond
    response = ser.read(ser.in_waiting).decode().strip()
    return response

try:
    send_command("gpio set 6")  # this pin acts as high reference for 0 and 1
    
    # Make sure all LEDs are off initially
    send_command("gpio clear 2")
    send_command("gpio clear 3")
    send_command("gpio clear 4")
    
    print("Reading switches and cycling LEDs (press Ctrl+C to exit)...")
    current_led = 2  # Start with LED on pin 2
    
    while True:
        # Read input pins
        pin0_value = send_command("gpio read 0")
        pin1_value = send_command("gpio read 1")

        print(pin0_value.strip().split('\n')[1])
        
        # Turn off all LEDs
        send_command("gpio clear 2")
        send_command("gpio clear 3")
        send_command("gpio clear 4")
        
        # Turn on current LED
        send_command(f"gpio set {current_led}")
        
        # Move to next LED in sequence
        current_led = current_led + 1
        if current_led > 4:
            current_led = 2
        
        time.sleep(0.5)  # Interval between updates
        
except KeyboardInterrupt:
    print("\nExiting program")
finally:
    # Turn off all LEDs before exiting
    send_command("gpio clear 2")
    send_command("gpio clear 3")
    send_command("gpio clear 4")
    ser.close()
    print("All LEDs turned off and serial connection closed")
