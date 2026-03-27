# Setting up Raspberry Pi Zero W for flashing BusyBox firmware

### 1. Install OS
Install [Raspberry Pi OS (64-bit)](https://www.raspberrypi.com/software/operating-systems/) on [Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/). 

### 2. Acquire Hardware
required hardware:
 - Enough USB hubs to flash all BusyBox Modules desired (for 6 modules, this requires 6 Nanos and 2 4-port USB Hubs).
 - internet connection for Pi Zero 2 W

### 3. Install and Initialize Arduino CLI

install
```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
sudo mv bin/arduino-cli /usr/local/bin/
rm -rf bin
```

initialize 
```bash
arduino-cli config init
arduino-cli core update-index
arduino-cli core install arduino:avr
# e-ink display drivers
arduino-cli lib update-index
arduino-cli lib install "GxEPD2"
```



### 4. Build and Upload firmware code to Arduinos

Plug in USB Hubs to the Pi Zero 2 W. This requires one USB Hub to be daisy chained to the other.

Plug in the targeted number of Arduinos to the Pi Zero 2 W's USB Hubs.

```bash
cd BusyBox/devices
ls /dev/ttyUSB* -la  # view connected Arduino Nanos
nano device_build_targets.yaml  # edit device ports and module targets as needed
./build_all.sh
./upload_all.sh
```

### 5. Verify firmware

View serial output of arduinos:
```bash
# replace /dev/ttyUSB0 with the device you want to view
screen /dev/ttyUSB0 9600
# Exit: `Ctrl+A` then `K` → `Y`.
```

If using the E-ink display module, send e-ink commands:
```bash
# assuming /dev/ttyUSB5 corresponds to the e-ink module
stty -F /dev/ttyUSB5 9600 cs8 -cstopb -parenb
echo -e "1:Hello\n" > /dev/ttyUSB5  # set top line
echo -e "2:World\n" > /dev/ttyUSB5  # set bottom line
```

test port identification of modules
```bash
cd BusyBox/devices
python test_identify_arduinos.py
```

this should return:
```
Detected Arduino modules:
PORT          MODULE
------------  --------------------
/dev/ttyUSB0  buttons_module
/dev/ttyUSB1  knob_module
/dev/ttyUSB2  sliders_module
/dev/ttyUSB3  switches_module
/dev/ttyUSB4  wires_module
/dev/ttyUSB5  e-ink_display_module
```

### 6. Installing MQTT on the pi
```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
# Check status:
systemctl status mosquitto

sudo apt install python3-paho-mqtt
```

running the mqtt bridge
```bash
cd BusyBox/devices/pi_sw
python mqtt_bridge.py --broker-host localhost  # MQTT broker on pi
python mqtt_bridge.py --broker-host 10.137.70.35  # MQTT broker on other PC

# command the e-ink display:
mosquitto_pub -t busybox/eink/cmd -m "1:BusyBox Demo"
mosquitto_pub -t busybox/eink/cmd -m "2:Ready!"

# listen to published topic chatter
mosquitto_sub -h localhost -t 'busybox/buttons/state' -v  # replace `buttons` with desired state
```
