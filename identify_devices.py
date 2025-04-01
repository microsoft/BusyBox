import os
import glob
import time

TURN_ON_BACKLIGHT = b"\xFE\x42\x00"
TURN_OFF_BACKLIGHT = b"\xFE\x46"
CLEAR_DISPLAY = b"\xFE\x58"
GO_TO_HOME = b"\xFE\x48"


def find_unmapped_device():
    # Get all ttyACM devices
    acm_devices = set(os.path.basename(dev) for dev in glob.glob('/dev/ttyACM*'))
    
    # Find all symlinks pointing to ttyACM devices
    mapped_devices = set()
    for symlink in glob.glob('/dev/tty_*'):
        if os.path.islink(symlink):
            target = os.path.basename(os.readlink(symlink))
            if target.startswith('ttyACM'):
                mapped_devices.add(target)
    
    # Find the unmapped devices
    unmapped_devices = acm_devices - mapped_devices
    
    if unmapped_devices:
        for device in unmapped_devices:
            print(f"Found unmapped device: /dev/{device}")
        return list(unmapped_devices)
    else:
        print("All ttyACM devices are mapped to symlinks")
        return []

if __name__ == "__main__":
    unmapped = find_unmapped_device()
    if unmapped:
        print(f"Unmapped device(s): {', '.join(unmapped)}")
        first_unmapped = f"/dev/{unmapped[0]}"
        print(f"Suggested symlink: ln -s {unmapped[0]} /dev/tty_lcd")
    else:
        print("No unmapped devices found")