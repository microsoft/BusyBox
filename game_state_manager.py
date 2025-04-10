import socket
import subprocess
import re
import json
import paho.mqtt.publish as publish

from game_utils import (
    MQTT_BROKER, 
    MQTT_PORT, 
    WEB_SERVER_PORT, 
    LCD_COMMAND_TOPIC,
    get_ethernet_ip,
)

class GameStateManager:
    def __init__(self):
        self.state = "initial"
        self.ip = None

    def set_state(self, new_state):
        self.state = new_state

    def get_state(self):
        return self.state

    def reset_state(self):
        self.state = "initial"

    def run(self):
        if self.state == "initial":
            self.ip = get_ethernet_ip()
            try:
                mqtt_payload = {
                    "top_line": f"server:{WEB_SERVER_PORT}", 
                    "bottom_line": self.ip if self.ip else "No IP found", 
                    "backlight": True
                }
                publish.single(LCD_COMMAND_TOPIC, json.dumps(mqtt_payload), hostname=MQTT_BROKER, port=MQTT_PORT)
                print(f"Sent IP address to LCD: {self.ip}")
            except Exception as e:
                print(f"Failed to send MQTT message: {e}")
            self.state = "wait_for_difficulty"
        
        elif self.state == "wait_for_difficulty":
            self.wait_for_difficulty()

    def wait_for_difficulty(self):
        # Placeholder for waiting for difficulty selection
        pass
        
if __name__ == "__main__":
    gsm = GameStateManager()
    gsm.run()