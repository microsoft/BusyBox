import socket
import subprocess
import re
import json
import paho.mqtt.publish as publish

class GameStateManager:
    def __init__(self):
        self.state = "initial"

    def set_state(self, new_state):
        self.state = new_state

    def get_state(self):
        return self.state

    def reset_state(self):
        self.state = "initial"

    def run(self):
        if self.state == "initial":
            self.ip = self.get_ethernet_ip()
            try:
                mqtt_payload = {
                    "top_line": "server:5000", 
                    "bottom_line": self.ip if self.ip else "No IP found", 
                    "backlight": True
                }
                publish.single("lcd_command", json.dumps(mqtt_payload), hostname="127.0.0.1", port=1883)
                print(f"Sent IP address to LCD: {self.ip}")
            except Exception as e:
                print(f"Failed to send MQTT message: {e}")
            self.state = "wait_for_start"
        
        elif self.state == "wait_for_start":
            pass
    
    def get_ethernet_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
            output = result.stdout
            eth_interfaces = re.findall(r'eth[0-9]+', output)
            for interface in eth_interfaces:
                if ip in output.split(interface)[1].split("inet ")[1]:
                    return ip
            return None
        except Exception as e:
            return None
        
if __name__ == "__main__":
    gsm = GameStateManager()
    gsm.run()