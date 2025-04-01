MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
GPIO_LED_TOPIC = "gpio_led_command"
LCD_COMMAND_TOPIC = "lcd_command"

DEVICES = {
    "buttons": "/dev/tty_buttons",
    "gpio": "/dev/tty_gpio",
    "knob": "/dev/tty_knob",
    "sliders": "/dev/tty_sliders",
    "wires": "/dev/tty_wires",
    "lcd": None,
}

import paho.mqtt.client as mqtt
import serial
import time
import json
import threading

class GPIODeviceInterface:
    HIGH_REF_PIN = "6"
    LED_RED = "2"
    LED_YELLOW = "3"
    LED_GREEN = "4"
    SWITCH_LEFT = "1"
    SWITCH_RIGHT = "0"

    def __init__(self, device_path):
        self.ser = serial.Serial(
            port=device_path,
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
        )
        self.lock = threading.Lock()

        self._send_command(f"gpio set {self.HIGH_REF_PIN}")

        # Make sure all LEDs are off initially
        self._send_command(f"gpio clear {self.LED_RED}")
        self._send_command(f"gpio clear {self.LED_YELLOW}")
        self._send_command(f"gpio clear {self.LED_GREEN}")

        # Set up MQTT client that listens for LED commands
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        self.mqtt_client.subscribe(GPIO_LED_TOPIC)
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.loop_start()

        self.io_states = {
            "led_red": False,
            "led_yellow": False,
            "led_green": False,
            "switch_left": None,
            "switch_right": None,
        }

    def on_mqtt_message(self, client, userdata, message):
        """Callback for MQTT messages
        message payload is expected to be a JSON string with LED states
        Example: {"red": true, "yellow": false, "green": true}
        """
        try:
            led_states = json.loads(message.payload.decode())
            self.set_leds(
                red_on=led_states.get("red", False),
                yellow_on=led_states.get("yellow", False),
                green_on=led_states.get("green", False)
            )
        except json.JSONDecodeError as e:
            print(f"Failed to decode MQTT message: {e}")

    def _send_command(self, cmd):
        """Send command to GPIO module and read response"""
        with self.lock:
            self.ser.write((cmd + '\r').encode())
            time.sleep(0.0625)  # Give device time to respond
            response = self.ser.read(self.ser.in_waiting).decode().strip()
        return response

    def read_switches(self):
        switch_l = self._send_command(f"gpio read {self.SWITCH_LEFT}")
        switch_r = self._send_command(f"gpio read {self.SWITCH_RIGHT}")

        switch_l = bool(int(switch_l.strip().split('\n')[1]))
        switch_r = bool(int(switch_r.strip().split('\n')[1]))

        self.io_states["switch_left"] = switch_l
        self.io_states["switch_right"] = switch_r
        return switch_l, switch_r

    def set_leds(self, red_on, yellow_on, green_on):
        """Set the state of the LEDs"""
        if red_on:
            self._send_command(f"gpio set {self.LED_RED}")
        else:
            self._send_command(f"gpio clear {self.LED_RED}")

        if yellow_on:
            self._send_command(f"gpio set {self.LED_YELLOW}")
        else:
            self._send_command(f"gpio clear {self.LED_YELLOW}")

        if green_on:
            self._send_command(f"gpio set {self.LED_GREEN}")
        else:
            self._send_command(f"gpio clear {self.LED_GREEN}")
        
        self.io_states["led_red"] = red_on
        self.io_states["led_yellow"] = yellow_on
        self.io_states["led_green"] = green_on

    def close(self):
        # Turn off all LEDs before exiting
        self._send_command(f"gpio clear {self.LED_RED}")
        self._send_command(f"gpio clear {self.LED_YELLOW}")
        self._send_command(f"gpio clear {self.LED_GREEN}")
        self.ser.close()

    def __del__(self):
        self.close()
        print("GPIO serial connection closed")

class LCDInterface:
    TURN_ON_BACKLIGHT = b"\xFE\x42\x00"
    TURN_OFF_BACKLIGHT = b"\xFE\x46"
    CLEAR_DISPLAY = b"\xFE\x58"

    def __init__(self, device_path):
        self.ser = serial.Serial(device_path, timeout=1)
        self.lock = threading.Lock()

        # Set up MQTT client that listens for LED commands
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        self.mqtt_client.subscribe(LCD_COMMAND_TOPIC)
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.loop_start()

        self.current_text = ""

    def get_current_text(self):
        return self.current_text

    def on_mqtt_message(self, client, userdata, message):
        """Callback for MQTT messages
        message payload is expected to be a JSON string with LCD commands including optional backlight command
        Example1: {"top_line": "top text", "bottom_line": "bottom text", "backlight": true}
        Example2: {"top_line": "hello", "bottom_line": "world"}
        
        """
        with self.lock:
            # Initialize variables outside the try block
            backlight_on = None
            text = ""
            
            try:
                lcd_command = json.loads(message.payload.decode())
                top_line = lcd_command.get("top_line", "")
                bottom_line = lcd_command.get("bottom_line", "")
                if "backlight" in lcd_command:
                    backlight_on = lcd_command["backlight"]
                
                if len(top_line) > 20:
                    top_line = top_line[:20]
                elif len(top_line) < 20:
                    top_line = top_line.ljust(20)
                text = top_line + bottom_line[:16]
                self.current_text = text
                
            except json.JSONDecodeError as e:
                print(f"Failed to decode MQTT message: {e}")
                # Only process the command if JSON decoding was successful
            
            self.ser.write(self.CLEAR_DISPLAY)
            if backlight_on is not None:
                if backlight_on is True:
                    self.ser.write(self.TURN_ON_BACKLIGHT)
                    time.sleep(0.1)
                elif backlight_on is False:
                    self.ser.write(self.TURN_OFF_BACKLIGHT)
                    time.sleep(0.1)
            print(f"LCD: {text}")
            self.ser.write(text.encode())
            time.sleep(0.1)
                
    def close(self):
        self.ser.write(self.CLEAR_DISPLAY)
        time.sleep(0.1)
        self.ser.write(self.TURN_OFF_BACKLIGHT)
        time.sleep(0.1)
        self.ser.close()

    def __del__(self):
        self.close()
        print("LCD serial connection closed")


if __name__ == "__main__":
    # test GPIODeviceInterface
    gpio_device = GPIODeviceInterface(DEVICES["gpio"])
    start = time.time()
    total_blink_time = 10

    lcd_device = LCDInterface("/dev/ttyACM0")
    try:
        green_led = True
        while time.time() - start < total_blink_time:
            switch_l, switch_r = gpio_device.read_switches()
            
            # Example of setting LEDs based on switches
            gpio_device.set_leds(switch_l, switch_r, green_led)
            green_led = not green_led
            time.sleep(0.25)  # Interval between updates
        
        while True:
            '''bash
            # control LEDs
            mosquitto_pub -h 127.0.0.1 -p 1883 -t gpio_led_command -m '{"red": true, "yellow": false, "green": true}'
            # control LCD
            mosquitto_pub -h 127.0.0.1 -p 1883 -t lcd_command -m '{"top_line": "Hello", "bottom_line": "World", "backlight": true}'
            '''
            # Keep the program running to listen for MQTT messages
            time.sleep(0.25)

    except KeyboardInterrupt:
        gpio_device.close()
        lcd_device.close()
        print("\nExiting program")
