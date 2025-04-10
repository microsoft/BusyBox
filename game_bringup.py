import threading
import time
import serial
import os
import signal
from identify_devices import find_unmapped_device
from game_utils import (
    DEVICES,
    WEB_SERVER_PORT,
    GPIODeviceInterface,
    LCDInterface,
    SerialMessageDecoderAndPublisher,
)
from web_server import start_server, emit_device_data
from game_state_manager import GameStateManager

# Flag to control threads
running = True

def signal_handler(sig, frame):
    global running
    print("\nStopping monitoring threads...")
    running = False

def monitor_device(device_name, device_path, publisher):
    """Monitor a device continuously and emit data via websocket"""
    print(f"Starting monitoring thread for {device_name} at {device_path}")
    if not os.path.exists(device_path):
        emit_device_data(device_name, f"ERROR: Device path {device_path} does not exist")
        return
    try:
        ser = serial.Serial(device_path, 9600, timeout=0.1)
        while running:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                if data:
                    try:
                        decoded = data.decode('utf-8', errors='replace')
                        publisher.parse_serial_message_and_publish(decoded)
                        timestamp = time.time()
                        # Send data to web clients
                        emit_device_data(device_name, {
                            'timestamp': timestamp,
                            'data': decoded.strip(),
                            'raw': False
                        })
                    except Exception as e:
                        emit_device_data(device_name, {
                            'timestamp': time.time(),
                            'data': str(data),
                            'error': str(e),
                            'raw': True
                        })
            time.sleep(0.1)  # Short sleep to prevent CPU hogging
        ser.close()
    except Exception as e:
        emit_device_data(device_name, {
            'timestamp': time.time(),
            'error': str(e),
            'raw': False
        })

def interact_with_gpio(device_name, device_path, publisher):
    """Monitor GPIO swithces and emit data via websocket"""
    print(f"Starting monitoring thread for {device_name} at {device_path}")
    if not os.path.exists(device_path):
        emit_device_data(device_name, f"ERROR: Device path {device_path} does not exist")
        return
    try:
        gpio_device = GPIODeviceInterface(device_path)
        
        while running:
            switch_l, switch_r = gpio_device.read_switches()
            switch_state = f"Switch L: {switch_l}, Switch R: {switch_r}"
            led_states = (
                f"LED Red: {gpio_device.io_states['led_red']}, "
                f"LED Yellow: {gpio_device.io_states['led_yellow']}, "
                f"LED Green: {gpio_device.io_states['led_green']}"
            )
            try:
                publisher.parse_serial_message_and_publish(switch_state)
                publisher.parse_serial_message_and_publish(led_states)
                timestamp = time.time()
                # Send data to web clients
                emit_device_data(device_name, {
                    'timestamp': timestamp,
                    'data': switch_state,
                    'raw': False
                })
                emit_device_data(device_name, {
                    'timestamp': timestamp,
                    'data': led_states,
                    'raw': False
                })
            except Exception as e:
                emit_device_data(device_name, {
                    'timestamp': time.time(),
                    'data': switch_state,
                    'error': str(e),
                    'raw': True
                })
            time.sleep(0.25)
        
        del gpio_device
        
    except Exception as e:
        emit_device_data(device_name, {
            'timestamp': time.time(),
            'error': str(e),
            'raw': False
        })

def spin_lcd(device_name, device_path, publisher):
    """Interact with the LCD device and emit data via websocket"""
    print(f"Starting monitoring thread for {device_name} at {device_path}")
    if not os.path.exists(device_path):
        emit_device_data(device_name, f"ERROR: Device path {device_path} does not exist")
        return
    try:
        lcd_device = LCDInterface(device_path)
        while running:
            current_text = lcd_device.get_current_text()
            try:
                publisher.parse_serial_message_and_publish(current_text)
                timestamp = time.time()
                # Send data to web clients
                emit_device_data(device_name, {
                    'timestamp': timestamp,
                    'data': current_text,
                    'raw': False
                })
            except Exception as e:
                emit_device_data(device_name, {
                    'timestamp': time.time(),
                    'data': current_text,
                    'error': str(e),
                    'raw': True
                })
            time.sleep(1.0)

    except Exception as e:
        emit_device_data(device_name, {
            'timestamp': time.time(),
            'error': str(e),
            'raw': False
        })

if __name__ == "__main__":
    # Register signal handler for CTRL+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Find unmapped LCD device
    unmapped = find_unmapped_device()
    if unmapped:
        DEVICES["lcd"] = f"/dev/{unmapped[0]}"
        print(f"Found LCD at {DEVICES['lcd']}")
    else:
        print("No LCD device found.")
        exit(1)
    
    # Start the web server in a separate thread
    web_thread = threading.Thread(target=start_server, daemon=True)
    web_thread.start()
    print(f"Web server started at http://localhost:{WEB_SERVER_PORT}")
    
    # Create threads for each device
    threads = []
    for device_name, device_path in DEVICES.items():
        publisher = SerialMessageDecoderAndPublisher()
        if device_name == "lcd":
            thread = threading.Thread(
                target=spin_lcd, 
                args=(device_name, device_path, publisher),
                name=f"LCD-{device_name}",
                daemon=True
            )
        elif device_name == "gpio":
            thread = threading.Thread(
                target=interact_with_gpio, 
                args=(device_name, device_path, publisher),
                name=f"GPIO-{device_name}",
                daemon=True
            )
        elif device_path:
            thread = threading.Thread(
                target=monitor_device, 
                args=(device_name, device_path, publisher),
                name=f"Monitor-{device_name}",
                daemon=True
            )
        threads.append(thread)
    
    # Start all threads
    print("Starting monitoring threads. Press CTRL+C to stop...")
    for thread in threads:
        thread.start()
    time.sleep(0.1)  # Give threads and serial time to start

    # Start Game State manager
    gsm = GameStateManager()
    gsm.run()
    
    try:
        # Keep main thread alive until CTRL+C
        while running:
            time.sleep(0.25)
    except KeyboardInterrupt:
        # This is handled by the signal handler
        pass
    
    print("Shutting down...")
    time.sleep(0.5)
